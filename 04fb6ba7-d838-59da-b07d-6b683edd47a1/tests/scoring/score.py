"""Six-lane scorer for receivables finance surveillance. Standard library only.

Lanes are purely additive: no consistency veto, no global gate, no stability multiplier, so
every lane stays independently improvable. Each lane's floor is the maximum metric attained by
the frozen competent-method portfolio recorded in scorer_manifest.json, so matching a competent
method earns exactly zero in that lane and only exceeding it pays.

Nothing here runs at import time: Harbor Reward Kit imports every Python file under /tests.
"""
import json
import math
import os

LANES = ('dilution_reserve', 'collection_profile', 'dispute_flag', 'recovery_tier', 'availability_rank', 'loss_reserve')
CHEAT_CHECKS = ('duplicate_answer_rows', 'submission_symlink', 'oversized_answer_file', 'non_finite_values')

# Denominator safeguards fixed before any graded target was inspected: $500 dilution materiality
# and $50 loss-reserve materiality. They stop a near-zero truth turning a trivial miss into a full error.
DILUTION_BOUND = 500.0
LOSS_BOUND = 50.0
# A rank agrees when it lies within this many places of the desk's dense rank in the cohort.
RANK_TOLERANCE = 10
MAX_ANSWER_BYTES = 20_000_000
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scorer_manifest.json')


def read_jsonl(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _reject_constant(value):
    raise ValueError('non-standard JSON constant ' + str(value))


def read_submission(submission_dir, tripped=None):
    """Return {record_id: row}. Duplicate ids are dropped entirely, never resolved to the last one."""
    tripped = set() if tripped is None else tripped
    path = os.path.join(str(submission_dir), 'predictions.jsonl')
    if os.path.islink(path):
        tripped.add('submission_symlink')
        raise ValueError('symlinked predictions.jsonl')
    if not os.path.isfile(path):
        raise ValueError('missing predictions.jsonl')
    if os.path.getsize(path) > MAX_ANSWER_BYTES:
        tripped.add('oversized_answer_file')
        raise ValueError('oversized predictions.jsonl')
    seen, duplicated = {}, set()
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line, parse_constant=_reject_constant)
            except (ValueError, RecursionError):
                if 'NaN' in line or 'Infinity' in line:
                    tripped.add('non_finite_values')
                continue
            if not isinstance(row, dict):
                continue
            key = row.get('record_id')
            if not isinstance(key, str):
                continue
            if key in seen:
                duplicated.add(key)
                continue
            seen[key] = row
    if duplicated:
        tripped.add('duplicate_answer_rows')
    for key in duplicated:
        seen.pop(key, None)
    return seen


def relative_agreement(pairs, bound):
    """(1 - mean(err)) / (1 + sqrt(mean(err^2))), err = min(1, |a-b| / max(|b|, bound)).

    Penalizes error variance as well as mean error. Missing or invalid items count as err = 1.
    """
    if not pairs:
        return 0.0
    errs = []
    for predicted, actual in pairs:
        if not _finite(predicted) or predicted < 0 or abs(predicted - round(predicted, 2)) > 1e-8:
            errs.append(1.0)
            continue
        errs.append(min(1.0, abs(predicted - actual) / max(abs(actual), bound)))
    mean_err = math.fsum(errs) / len(errs)
    mean_sq = math.fsum(e * e for e in errs) / len(errs)
    return (1.0 - mean_err) / (1.0 + math.sqrt(mean_sq))


def _distribution_vector(value, periods):
    if not isinstance(value, list) or len(value) != periods:
        return None
    out = []
    for item in value:
        if not _finite(item) or item < 0:
            return None
        out.append(float(item))
    try:
        total = math.fsum(out)
    except OverflowError:
        return None
    if total > 1.0 + 1e-9:
        return None
    out.append(max(0.0, 1.0 - total))
    return out


def distribution_overlap(pairs, periods):
    """1 - total variation distance over the eight bands plus an explicit uncollected category."""
    if not pairs:
        return 0.0
    scores = []
    for predicted, actual in pairs:
        truth_vec = _distribution_vector(actual, periods)
        if truth_vec is None:
            continue
        pred_vec = _distribution_vector(predicted, periods)
        if pred_vec is None:
            scores.append(0.0)
            continue
        tv = 0.5 * math.fsum(abs(p - q) for p, q in zip(pred_vec, truth_vec))
        scores.append(max(0.0, 1.0 - tv))
    return math.fsum(scores) / len(scores) if scores else 0.0


def f1_detection(pairs):
    # An invalid flag is an adverse decision on that truth row, never an abstention.
    pairs = [(1 - a if p is None else p, a) for p, a in pairs]
    tp = fp = fn = 0
    for predicted, actual in pairs:
        pred = 1 if predicted == 1 else 0
        true = 1 if actual == 1 else 0
        if pred and true:
            tp += 1
        elif pred and not true:
            fp += 1
        elif not pred and true:
            fn += 1
    if tp == 0:
        return 0.0
    precision, recall = tp / (tp + fp), tp / (tp + fn)
    return 2.0 * precision * recall / (precision + recall)


def macro_f1(pairs, labels):
    values = []
    for label in labels:
        tp = sum(p == label and a == label for p, a in pairs)
        fp = sum((p == label or p is None) and a != label for p, a in pairs)
        fn = sum(p != label and a == label for p, a in pairs)
        denominator = 2 * tp + fp + fn
        values.append(2 * tp / denominator if denominator else 0.0)
    return math.fsum(values) / len(values) if values else 0.0


def _ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for index in order[i:j]:
            ranks[index] = (i + j - 1) / 2.0
        i = j
    return ranks


def rank_agreement(pairs, tolerance=RANK_TOLERANCE):
    """Share of ranked records whose rank lies within `tolerance` places of the desk's rank.

    Unlike a rank correlation this does not saturate: a smooth approximation that places most
    records a few dozen ranks away earns little, and only reproducing the ordering closely pays.
    """
    if not pairs:
        return 0.0
    hits = 0
    for predicted, actual in pairs:
        if type(predicted) is int and 1 <= predicted <= len(pairs) and abs(predicted - actual) <= tolerance:
            hits += 1
    return hits / len(pairs)


def lane_metrics(predictions, truth):
    keys = sorted(truth)
    expected = len(keys)
    present = [k for k in keys if k in predictions]

    def pairs(lane):
        return [(predictions.get(k, {}).get(lane), truth[k][lane]) for k in keys]

    flags = [(p if type(p) is int and p in (0, 1) else None, a) for p, a in pairs('dispute_flag')]
    tiers = [(p if type(p) is int and p in (0, 1, 2, 3) else None, a) for p, a in pairs('recovery_tier')]
    cohorts = {}
    for k in keys:
        period = truth[k].get('period', k.rsplit(':p', 1)[-1])
        # a missing or invalid rank is one miss inside its cohort, never a shrunk denominator
        cohorts.setdefault(period, []).append((predictions.get(k, {}).get('availability_rank'), truth[k]['availability_rank']))
    rank_metric = math.fsum(rank_agreement(pairs_) for pairs_ in cohorts.values()) / len(cohorts) if cohorts else 0.0
    metrics = {
        'dilution_reserve': relative_agreement(pairs('dilution_reserve'), DILUTION_BOUND),
        'collection_profile': distribution_overlap(pairs('collection_profile'), 8),
        'dispute_flag': f1_detection(flags),
        'recovery_tier': macro_f1(tiers, sorted({r['recovery_tier'] for r in truth.values()})),
        'availability_rank': rank_metric,
        'loss_reserve': relative_agreement(pairs('loss_reserve'), LOSS_BOUND),
    }
    return metrics, (len(present) / expected if expected else 0.0), expected, len(present)


def lane_points(metrics, manifest):
    points = {}
    for name in LANES:
        lane = manifest['lanes'][name]
        floor, weight = lane['floor'], lane['weight']
        if not math.isfinite(floor) or floor >= 1.0 or floor < 0.0:
            raise ValueError('invalid lane floor')
        fraction = max(0.0, min(1.0, (metrics[name] - floor) / (1.0 - floor)))
        points[name] = weight * fraction
    return points


def _zero_report(manifest, expected, reason, tripped):
    return {'score': 0.0, 'lanes': {name: {'metric': 0.0, 'floor': manifest['lanes'][name]['floor'], 'fraction': 0.0,
                                           'points': 0.0, 'max': manifest['lanes'][name]['weight'],
                                           'metric_kind': manifest['lanes'][name]['metric_kind']} for name in LANES},
            'coverage': 0.0, 'valid_records': 0, 'expected_records': expected, 'note': reason,
            'cheat_checks': {c: c in tripped for c in CHEAT_CHECKS}}


def evaluate_report(submission_dir, input_path, manifest_path=MANIFEST_PATH):
    with open(manifest_path, 'r', encoding='utf-8') as handle:
        manifest = json.load(handle)
    tripped = set()
    truth = {row['record_id']: row for row in read_jsonl(str(input_path))}
    if not truth:
        raise ValueError('empty graded truth')
    try:
        predictions = read_submission(submission_dir, tripped)
    except ValueError as exc:
        return _zero_report(manifest, len(truth), str(exc), tripped)
    if not predictions:
        return _zero_report(manifest, len(truth), 'empty submission', tripped)
    try:
        metrics, coverage, expected, valid = lane_metrics(predictions, truth)
    except (TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, ZeroDivisionError) as exc:
        return _zero_report(manifest, len(truth), 'unscorable submission: ' + type(exc).__name__, tripped)
    points = lane_points(metrics, manifest)
    denominator = math.fsum(manifest['lanes'][n]['weight'] for n in LANES)
    score = round(math.fsum(points[n] for n in LANES) / denominator, 4)
    lanes = {name: {'metric': metrics[name], 'floor': manifest['lanes'][name]['floor'],
                    'fraction': points[name] / manifest['lanes'][name]['weight'] if manifest['lanes'][name]['weight'] else 0.0,
                    'points': points[name], 'max': manifest['lanes'][name]['weight'],
                    'metric_kind': manifest['lanes'][name]['metric_kind']} for name in LANES}
    return {'score': score, 'lanes': lanes, 'coverage': coverage, 'valid_records': valid, 'expected_records': expected,
            'cheat_checks': {c: c in tripped for c in CHEAT_CHECKS}}


def ctrf(report):
    tests = [{'name': c, 'status': 'failed' if report['cheat_checks'].get(c) else 'passed', 'duration': 0} for c in CHEAT_CHECKS]
    failed = sum(t['status'] == 'failed' for t in tests)
    return {'results': {'tool': {'name': 'receivables-surveillance-scorer'},
                        'summary': {'tests': len(tests), 'passed': len(tests) - failed, 'failed': failed,
                                    'pending': 0, 'skipped': 0, 'other': 0, 'start': 0, 'stop': 0},
                        'tests': tests}}


def evaluate(submission_dir, input_path, manifest_path=MANIFEST_PATH):
    return evaluate_report(submission_dir, input_path, manifest_path)['score']
