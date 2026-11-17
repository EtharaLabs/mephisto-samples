"""Six-lane scorer for documentary credit examination. Standard library only.

Lanes are purely additive: no consistency veto, no global gate, no stability multiplier.
Each lane's measured competent-method floor is frozen in scorer_manifest.json. Nothing
here runs at import time; the verifier never imports or executes submitted Python code.
"""
import json
import math
from pathlib import Path

LANES = ('discrepancy_count', 'discrepancy_class_profile', 'refusal_flag', 'tenor_tier',
         'examiner_priority_rank', 'charge_reserve')
CHEAT_CHECKS = ('duplicate_answer_rows', 'submission_symlink', 'oversized_answer_file', 'non_finite_values')
COUNT_BOUND = 0.5
CHARGE_BOUND = 50.0
RANK_TOLERANCE = 10
MAX_ANSWER_BYTES = 20_000_000
MANIFEST_PATH = Path(__file__).with_name('scorer_manifest.json')


def read_jsonl(path):
    with open(path, encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def read_submission(submission_dir, tripped=None):
    """Drop duplicate ids in full; malformed values cannot poison unrelated lanes."""
    tripped = set() if tripped is None else tripped
    path = Path(submission_dir) / 'predictions.jsonl'
    if path.is_symlink():
        tripped.add('submission_symlink')
        raise ValueError('symlinked predictions.jsonl')
    if not path.is_file():
        raise ValueError('missing predictions.jsonl')
    if path.stat().st_size > MAX_ANSWER_BYTES:
        tripped.add('oversized_answer_file')
        raise ValueError('oversized predictions.jsonl')

    def invalid_constant(value):
        tripped.add('non_finite_values')
        return None

    seen, duplicates = {}, set()
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            try:
                row = json.loads(line, parse_constant=invalid_constant)
            except (ValueError, RecursionError):
                continue
            if not isinstance(row, dict) or not isinstance(row.get('record_id'), str):
                continue
            key = row['record_id']
            if key in seen:
                duplicates.add(key)
            seen[key] = row
            for value in row.values():
                items = value if isinstance(value, list) else [value]
                if any(type(v) is float and not math.isfinite(v) for v in items):
                    tripped.add('non_finite_values')
    if duplicates:
        tripped.add('duplicate_answer_rows')
    return {k: v for k, v in seen.items() if k not in duplicates}


def relative_agreement(pairs, bound):
    """(1 - mean(e)) / (1 + sqrt(mean(e^2))); e is clipped relative absolute error."""
    errors = []
    for predicted, actual in pairs:
        if not _finite(predicted) or predicted < 0 or abs(predicted - round(predicted, 2)) > 1e-8:
            errors.append(1.0)
        else:
            errors.append(min(1.0, abs(predicted - actual) / max(abs(actual), bound)))
    return ((1 - math.fsum(errors) / len(errors)) /
            (1 + math.sqrt(math.fsum(e * e for e in errors) / len(errors)))) if errors else 0.0


def _distribution_vector(value, periods=8):
    if not isinstance(value, list) or len(value) != periods or any(not _finite(v) or v < 0 or v > 1 for v in value):
        return None
    total = math.fsum(value)
    if total > 1 + 1e-9:
        return None
    return value + [max(0, 1 - total)]


def distribution_overlap(pairs, periods=8):
    """One minus total variation, including the pending-classification residual category."""
    scores = []
    for predicted, actual in pairs:
        p, a = _distribution_vector(predicted, periods), _distribution_vector(actual, periods)
        if a is None:
            raise ValueError('invalid truth profile')
        scores.append(max(0, 1 - 0.5 * math.fsum(abs(x - y) for x, y in zip(p, a))) if p is not None else 0)
    return math.fsum(scores) / len(scores) if scores else 0.0


def f1_detection(pairs):
    # An invalid flag is an adverse decision on that truth row, never an abstention.
    pairs = [(1 - a if p is None else p, a) for p, a in pairs]
    tp = sum(p == 1 and a == 1 for p, a in pairs)
    fp = sum(p == 1 and a == 0 for p, a in pairs)
    fn = sum(p != 1 and a == 1 for p, a in pairs)
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def macro_f1(pairs, labels):
    """Unweighted per-class F1, never support-weighted F1 or micro accuracy."""
    values = []
    for label in labels:
        tp = sum(p == label and a == label for p, a in pairs)
        # Invalid predictions incur every adverse one-vs-rest error. Selective omission
        # must never improve macro F1 by removing a rare-class confusion.
        fp = sum((p == label or p is None) and a != label for p, a in pairs)
        fn = sum(p != label and a == label for p, a in pairs)
        values.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return math.fsum(values) / len(values) if values else 0.0


def rank_agreement(pairs, tolerance=RANK_TOLERANCE):
    return sum(type(p) is int and 1 <= p <= len(pairs) and abs(p - a) <= tolerance
               for p, a in pairs) / len(pairs) if pairs else 0.0


def lane_metrics(predictions, truth):
    keys = sorted(truth)
    expected = len(keys)

    def pairs(lane):
        return [(predictions.get(k, {}).get(lane), truth[k][lane]) for k in keys]

    flags = [(p if type(p) is int and p in (0, 1) else None, a) for p, a in pairs('refusal_flag')]
    tiers = [(p if type(p) is int and p in range(4) else None, a) for p, a in pairs('tenor_tier')]
    cohorts = {}
    for k in keys:
        cohorts.setdefault(k.rsplit(':p', 1)[-1], []).append(
            (predictions.get(k, {}).get('examiner_priority_rank'), truth[k]['examiner_priority_rank']))
    metrics = {
        'discrepancy_count': relative_agreement(pairs('discrepancy_count'), COUNT_BOUND),
        'discrepancy_class_profile': distribution_overlap(pairs('discrepancy_class_profile')),
        'refusal_flag': f1_detection(flags),
        'tenor_tier': macro_f1(tiers, sorted({r['tenor_tier'] for r in truth.values()})),
        'examiner_priority_rank': math.fsum(rank_agreement(v) for v in cohorts.values()) / len(cohorts),
        'charge_reserve': relative_agreement(pairs('charge_reserve'), CHARGE_BOUND)}
    present = sum(k in predictions for k in keys)
    return metrics, present / expected, expected, present


def lane_points(metrics, manifest):
    points = {}
    for name in LANES:
        floor = manifest['lanes'][name]['floor']
        if not _finite(floor) or not 0 <= floor < 1:
            raise ValueError('invalid lane floor')
        points[name] = manifest['lanes'][name]['weight'] * max(0, min(1, (metrics[name] - floor) / (1 - floor)))
    return points


def evaluate_report(submission_dir, input_path, manifest_path=MANIFEST_PATH):
    manifest = json.loads(Path(manifest_path).read_text())
    truth = {r['record_id']: r for r in read_jsonl(input_path)}
    if not truth:
        raise ValueError('empty graded truth')
    tripped, note = set(), ''
    try:
        predictions = read_submission(submission_dir, tripped)
    except (ValueError, OSError) as exc:
        predictions, note = {}, str(exc)
    metrics, coverage, expected, present = lane_metrics(predictions, truth)
    points = lane_points(metrics, manifest)
    lanes = {n: dict(metric=metrics[n], floor=manifest['lanes'][n]['floor'], points=points[n],
                     fraction=points[n] / manifest['lanes'][n]['weight'], max=manifest['lanes'][n]['weight'],
                     metric_kind=manifest['lanes'][n]['metric_kind']) for n in LANES}
    return {'score': round(math.fsum(points.values()) / math.fsum(v['weight'] for v in manifest['lanes'].values()), 4),
            'lanes': lanes, 'coverage': coverage, 'expected_records': expected, 'valid_records': present,
            'note': note, 'cheat_checks': {c: c in tripped for c in CHEAT_CHECKS}}


def ctrf(report):
    tests = [dict(name=c, status='failed' if report['cheat_checks'][c] else 'passed', duration=0) for c in CHEAT_CHECKS]
    failed = sum(t['status'] == 'failed' for t in tests)
    return {'results': {'tool': {'name': 'documentary-credit-scorer'}, 'tests': tests,
                        'summary': dict(tests=len(tests), passed=len(tests) - failed, failed=failed,
                                        pending=0, skipped=0, other=0, start=0, stop=0)}}


def evaluate(submission_dir, input_path, manifest_path=MANIFEST_PATH):
    return evaluate_report(submission_dir, input_path, manifest_path)['score']
