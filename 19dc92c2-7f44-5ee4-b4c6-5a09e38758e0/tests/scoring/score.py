"""Frozen, independent six-lane scorer. The submission is data, never executable.

Missing or invalid lane values never shrink the query population. Floors are
judge-private constants; raw metrics and payable fractions are safe feedback.
"""
import json
import math
import os
import stat
from collections import Counter
from pathlib import Path

LANES = ('nav_break_magnitude', 'fee_accrual_profile', 'restatement_flag',
         'pricing_source_tier', 'oversight_rank', 'expense_reserve')
MAX_BYTES = 20_000_000


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def numeric(v):
    try:
        return type(v) in (int, float) and math.isfinite(v)
    except OverflowError:
        return False


def valid(v, lane, cohort_size):
    if lane in (LANES[0], LANES[5]):
        if not numeric(v) or v < 0:
            return False
        scaled = v * 100
        if not numeric(scaled):
            return v == round(v, 2)
        return abs(scaled - round(scaled)) <= 1e-7
    if lane == LANES[1]:
        return isinstance(v, list) and len(v) == 8 and all(numeric(x) and x >= 0 for x in v) and sum(v) <= 1 + 1e-9
    if lane == LANES[2]:
        return type(v) is int and v in (0, 1)
    if lane == LANES[3]:
        return type(v) is int and v in range(4)
    return type(v) is int and 1 <= v <= cohort_size


def load_submission(path):
    """Refuse symlinks, non-regular files and oversized files before reading."""
    issues = []
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                return {}, ['nonregular_or_oversized']
            text = stream.read(MAX_BYTES + 1)
        if len(text.encode('utf-8')) > MAX_BYTES:
            return {}, ['oversized']
        rows = [json.loads(line, parse_constant=lambda _: None) for line in text.splitlines() if line.strip()]
        if any(not isinstance(r, dict) or not isinstance(r.get('record_id'), str) for r in rows):
            return {}, ['malformed_record']
    except (OSError, ValueError, UnicodeError, RecursionError):
        return {}, ['unreadable_or_malformed']
    counts = Counter(r['record_id'] for r in rows)
    if any(n > 1 for n in counts.values()):
        issues.append('duplicate_answer_rows')
    return {r['record_id']: r for r in rows if counts[r['record_id']] == 1}, issues


def f1(pairs, label):
    tp = sum(p == label and y == label for p, y in pairs)
    fp = sum(p == label and y != label for p, y in pairs)
    fn = sum(p != label and y == label for p, y in pairs)
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def raw_metrics(predictions, truth):
    cohorts = Counter(r['record_id'].split(':p')[1] for r in truth)
    metrics, coverage = {}, {}
    for lane in LANES:
        pairs, periods = [], []
        for row in truth:
            period = row['record_id'].split(':p')[1]
            value = predictions.get(row['record_id'], {}).get(lane)
            pairs.append((value if valid(value, lane, cohorts[period]) else None, row[lane]))
            periods.append(period)
        coverage[lane] = sum(p is not None for p, _ in pairs) / len(pairs)
        if lane in (LANES[0], LANES[5]):
            bound = 1.0 if lane == LANES[0] else 100.0
            errors = [1.0 if p is None else min(1, abs(p - y) / max(y, bound)) for p, y in pairs]
            metrics[lane] = (1 - sum(errors) / len(errors)) / (1 + math.sqrt(sum(e*e for e in errors) / len(errors)))
        elif lane == LANES[1]:
            def overlap(p, y):
                if p is None:
                    return 0.0
                return max(0, 1 - .5 * (sum(abs(a-b) for a, b in zip(p, y)) + abs(sum(p) - sum(y))))
            metrics[lane] = sum(overlap(p, y) for p, y in pairs) / len(pairs)
        elif lane == LANES[2]:
            metrics[lane] = f1(pairs, 1) * coverage[lane]
        elif lane == LANES[3]:
            labels = sorted(set(y for _, y in pairs))
            metrics[lane] = sum(f1(pairs, label) for label in labels) / len(labels) * coverage[lane]
        else:
            metrics[lane] = sum(sum(p is not None and abs(p-y) <= 10 for (p, y), q in zip(pairs, periods) if q == period)
                                / size for period, size in cohorts.items()) / len(cohorts)
    return metrics, coverage


def score_rows(predictions, truth, manifest):
    if isinstance(predictions, list):
        counts = Counter(r['record_id'] for r in predictions)
        predictions = {r['record_id']: r for r in predictions if counts[r['record_id']] == 1}
    metrics, coverage = raw_metrics(predictions, truth)
    lanes = {}
    for lane in LANES:
        floor = manifest['lanes'][lane]['floor']
        weight = manifest['lanes'][lane]['weight']
        if not numeric(floor) or not 0 <= floor < 1 or weight != 1.0:
            raise ValueError('invalid lane manifest')
        fraction = max(0, min(1, (metrics[lane] - floor) / (1 - floor)))
        lanes[lane] = {'metric': metrics[lane], 'fraction': fraction, 'coverage': coverage[lane], 'points': fraction * weight}
    return {'score': round(sum(v['points'] for v in lanes.values()) / 6, 4), 'lanes': lanes}


def evaluate(submission_dir, tests_dir=None):
    tests_dir = Path(tests_dir or Path(__file__).resolve().parents[1])
    truth = read_rows(tests_dir / 'hidden' / 'truth.jsonl')
    manifest = json.loads((tests_dir / 'scoring' / 'scorer_manifest.json').read_text())
    predictions, issues = load_submission(Path(submission_dir) / 'predictions.jsonl')
    report = score_rows(predictions, truth, manifest)
    report['issues'] = issues
    return report
