"""Six-lane settlement scorer. Standard library only; nothing runs on import.

Competent floors apply independently. No global gate or cross-lane veto exists.
The expected population always comes from judge-private truth, never submission.
"""
import json
import math
import os
from pathlib import Path

LANES = ('adjustment_magnitude', 'allocation_key_profile', 'challenge_flag', 'method_tier', 'review_rank', 'uncertain_tax_reserve')
CHEAT_CHECKS = ('duplicate_answer_rows', 'submission_symlink', 'oversized_answer_file', 'non_finite_values')
ADJUSTMENT_BOUND = 500.0
RESERVE_BOUND = 50.0
RANK_TOLERANCE = 10
MAX_ANSWER_BYTES = 20_000_000
MANIFEST_PATH = Path(__file__).with_name('scorer_manifest.json')


def read_jsonl(path):
    with open(path, encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _integer(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def read_submission(submission_dir, tripped=None):
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
    seen, duplicates = {}, set()
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (ValueError, RecursionError):
                continue
            if not isinstance(row, dict) or not isinstance(row.get('record_id'), str):
                continue
            for lane in LANES:
                value = row.get(lane)
                items = value if isinstance(value, list) else [value]
                if any(isinstance(v, float) and not math.isfinite(v) for v in items):
                    tripped.add('non_finite_values')
                    row[lane] = None
            key = row['record_id']
            if key in seen:
                duplicates.add(key)
            seen[key] = row
    if duplicates:
        tripped.add('duplicate_answer_rows')
    return {k: v for k, v in seen.items() if k not in duplicates}


def relative_agreement(pairs, bound):
    """(1-mean(error))/(1+RMS(error)); missing items have clipped error one."""
    errors = [min(1.0, abs(p-a)/max(abs(a), bound)) if _finite(p) and p >= 0 and abs(p - round(p, 2)) <= 1e-8 else 1.0 for p, a in pairs]
    if not errors:
        return 0.0
    return (1-math.fsum(errors)/len(errors))/(1+math.sqrt(math.fsum(e*e for e in errors)/len(errors)))


def _distribution_vector(value, periods=8):
    if not isinstance(value, list) or len(value) != periods or any(not _finite(v) or v < 0 or v > 1.0 + 1e-9 for v in value):
        return None
    total = math.fsum(value)
    if total > 1.0 + 1e-9:
        return None
    return value + [max(0.0, 1-total)]


def distribution_overlap(pairs, periods=8):
    scores = []
    for p, a in pairs:
        p, a = _distribution_vector(p, periods), _distribution_vector(a, periods)
        if a is None:
            raise ValueError('invalid private distribution')
        scores.append(max(0.0, 1-0.5*math.fsum(abs(x-y) for x, y in zip(p, a))) if p is not None else 0.0)
    return math.fsum(scores)/len(scores) if scores else 0.0


def f1_detection(pairs):
    pairs = [(1-a if p is None else p, a) for p, a in pairs]
    tp = sum(p == 1 and a == 1 for p, a in pairs)
    fp = sum(p == 1 and a == 0 for p, a in pairs)
    fn = sum(p != 1 and a == 1 for p, a in pairs)
    return 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0


def macro_f1(pairs, labels):
    values = []
    for label in labels:
        tp = sum(p == label and a == label for p, a in pairs)
        fp = sum((p == label or p is None) and a != label for p, a in pairs)
        fn = sum(p != label and a == label for p, a in pairs)
        values.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0)
    return math.fsum(values)/len(values) if values else 0.0


def rank_agreement(pairs, tolerance=RANK_TOLERANCE):
    return sum(_integer(p, 1, len(pairs)) and abs(p-a) <= tolerance for p, a in pairs)/len(pairs) if pairs else 0.0


def lane_metrics(predictions, truth):
    keys = sorted(truth)
    expected = len(keys)
    if not expected:
        raise ValueError('empty graded truth')
    def pairs(lane):
        return [(predictions.get(k, {}).get(lane), truth[k][lane]) for k in keys]
    flags = [(p if _integer(p,0,1) else None, a) for p,a in pairs('challenge_flag')]
    tiers = [(p if _integer(p,0,3) else None, a) for p,a in pairs('method_tier')]
    cohorts = {}
    for k in keys:
        cohorts.setdefault(k.rsplit(':p',1)[1], []).append((predictions.get(k,{}).get('review_rank'), truth[k]['review_rank']))
    metrics = {
        LANES[0]: relative_agreement(pairs(LANES[0]), ADJUSTMENT_BOUND),
        LANES[1]: distribution_overlap(pairs(LANES[1])),
        LANES[2]: f1_detection(flags),
        LANES[3]: macro_f1(tiers, sorted({r[LANES[3]] for r in truth.values()})),
        LANES[4]: math.fsum(rank_agreement(v) for v in cohorts.values())/len(cohorts),
        LANES[5]: relative_agreement(pairs(LANES[5]), RESERVE_BOUND)}
    present = sum(k in predictions for k in keys)
    return metrics, present/expected, expected, present


def lane_points(metrics, manifest):
    result = {}
    for lane in LANES:
        spec = manifest['lanes'][lane]
        floor, weight = spec['floor'], spec['weight']
        if not _finite(floor) or not 0 <= floor < 1 or not _finite(weight) or weight <= 0:
            raise ValueError('invalid lane floor or weight')
        result[lane] = weight*max(0.0, min(1.0, (metrics[lane]-floor)/(1-floor)))
    return result


def evaluate_report(submission_dir, input_path, manifest_path=MANIFEST_PATH):
    manifest = json.loads(Path(manifest_path).read_text())
    truth = {r['record_id']:r for r in read_jsonl(input_path)}
    tripped, note = set(), None
    try:
        predictions = read_submission(submission_dir, tripped)
    except (OSError, UnicodeError, ValueError) as exc:
        predictions, note = {}, str(exc)
    metrics, coverage, expected, present = lane_metrics(predictions, truth)
    points = lane_points(metrics, manifest)
    total = math.fsum(manifest['lanes'][l]['weight'] for l in LANES)
    return {'score': round(math.fsum(points.values())/total,4), 'coverage':coverage,
            'expected_records':expected, 'valid_records':present, 'note':note,
            'lanes':{l:dict(metric=metrics[l],floor=manifest['lanes'][l]['floor'],
                            fraction=points[l]/manifest['lanes'][l]['weight'],points=points[l],
                            max=manifest['lanes'][l]['weight'],metric_kind=manifest['lanes'][l]['metric_kind']) for l in LANES},
            'cheat_checks':{c:c in tripped for c in CHEAT_CHECKS}}


def evaluate(submission_dir, input_path, manifest_path=MANIFEST_PATH):
    return evaluate_report(submission_dir, input_path, manifest_path)['score']


def ctrf(report):
    tests = [dict(name=c,status='failed' if report['cheat_checks'][c] else 'passed',duration=0) for c in CHEAT_CHECKS]
    failed = sum(t['status']=='failed' for t in tests)
    return {'results':{'tool':{'name':'transfer-pricing-settlement'},'tests':tests,
                       'summary':dict(tests=len(tests),passed=len(tests)-failed,failed=failed,pending=0,skipped=0,other=0,start=0,stop=0)}}
