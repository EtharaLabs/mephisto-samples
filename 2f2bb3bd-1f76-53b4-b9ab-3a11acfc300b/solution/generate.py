"""Private deterministic construction for documentary credit examination.

Run with ``python3 -B solution/generate.py``. Keyed public draws generate observations;
the six independent fitted estimators produce history and graded truth. No private draw
enters a target. A rerun overwrites exactly the same generated paths and bytes.
"""
import hashlib
import json
import math
import random
from pathlib import Path

import estimators

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / 'environment/workspace'
PUBLIC_KEY = 'documentary-credit-examination-public-v1-2026'
BENEFICIARY_COUNT = 360
REFERENCE_COUNT = 80
PERIODS = tuple(range(1, 21))
HISTORY_PERIODS = (8, 10, 12)
QUERY_PERIODS = (16, 20)
CLASSES = ('late presentation', 'inconsistent data', 'missing document', 'expired credit',
           'short shipment', 'insurance defect', 'transport defect', 'other')


def keyed_rng(label):
    return random.Random(int.from_bytes(hashlib.sha256(f'{PUBLIC_KEY}|{label}'.encode()).digest(), 'big'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


# --- observations and completed-case outcomes ----------------------------------------------

def sample(index, rng, base=None) -> dict:
    ranges = (((4, 35), (0, 0.5), (0, 0.4), (0, 35), (-8, 40)),
              ((0, 1), (0, 1), (0, 1), (0, 0.5), (0, 1)),
              ((0, 9), (0, 14), (0, 0.6), (0, 5), (0, 1)),
              ((0, 220), (0, 20), (0, 7), (0, 50), (0, 1)),
              ((0, 72), (0, 24), (0, 1), (0, 16), (0, 1)),
              ((11, 16), (0, 1), (1, 20), (0, 1), (0, 18)))
    values = [rng.uniform(a, b) for a, b in ranges[index]]
    if base is not None:
        values = [0.55 * a + 0.45 * b for a, b in zip(base, values)]
    # Tenor coverage must include sight and long usance presentations, not only middle bands.
    if index == 3:
        values[0] = rng.choice([0, 15, 30, 60, 90, 120, 180, 210])
    if index == 5:
        values[0] = math.exp(values[0])
    return dict(zip(estimators.FIELDS[index], [round(v, 6) for v in values]))


def outcome(index, row, rng, period, group):
    x = [row[k] for k in estimators.FIELDS[index]]
    regime = float(period >= 14)
    if index == 0:
        level = (0.2 + 0.018 * x[0] + 1.6 * x[1] + 1.3 * x[2] + 0.025 * x[3]
                 - 0.012 * x[4] + 0.18 * group + 0.32 * regime + 0.4 * math.sin(x[1] * 9))
        return round(max(0, math.exp(level + rng.gauss(0, 0.3)) - 1), 4)
    if index == 1:
        logits = [2.7 * x[0], 2.5 * x[1], 2.5 * x[2], 1.4 * x[0] - 0.6,
                  1.5 * (1 - x[2]), 5 * x[3], 2.2 * x[4], 0.6 + 0.3 * group,
                  1.0 + 1.7 * x[1] * x[4] + 0.5 * regime]
        logits[(group + 2) % 8] += 0.7
        probabilities = [math.exp(v) for v in logits]
        counts = [0] * 9
        for category in rng.choices(range(9), probabilities, k=rng.randrange(12, 45)):
            counts[category] += 1
        return counts
    if index == 2:
        logodds = (-2.2 + 0.38 * x[0] + 0.08 * x[1] + 3.0 * x[2] - 0.22 * x[3]
                   - 1.4 * x[4] + 0.22 * group + 0.45 * regime + 0.17 * x[0] * x[2])
        return int(rng.random() < sigmoid(logodds))
    if index == 3:
        return round(max(0, x[0] * (0.78 + 0.07 * group) + x[1] + x[3] * x[4]
                         + 4 * math.sin(x[2]) + 7 * regime + rng.gauss(0, 13)), 4)
    if index == 4:
        return round(12 + 0.13 * x[0] - 0.48 * x[1] + 7 * x[2] + 0.6 * x[3]
                     + 6 * math.sin(2 * math.pi * x[4] + group * 0.6)
                     + 0.08 * x[0] * x[2] + 3 * math.sin(x[3] / 4 + x[2] * 3)
                     + 2 * regime + rng.gauss(0, 3), 6)
    p = sigmoid(-1.8 + 1.8 * x[1] + 0.07 * x[2] + 1.3 * x[3] - 0.04 * x[4] + 0.18 * group + 0.4 * regime)
    if rng.random() > p:
        return 0.0
    rate = math.exp(-7.0 + 0.75 * x[3] + 0.3 * group + 0.4 * x[1] + rng.gauss(0, 0.5))
    return round(x[0] * rate, 2)


def book(row, rng, index, period):
    row['event_period'] = period
    row['booked_period'] = min(20, period + rng.choice([0, 0, 0, 1, 1, 2]))
    if rng.random() < 0.26:
        row['restated_period'] = row['booked_period'] + rng.randrange(1, 7)
        field = estimators.OUTCOMES[index]
        value = row[field]
        if index == 1:
            value = value[2:] + value[:2]
        elif index == 2:
            value = 1 - value
        else:
            value = round(value * math.exp(rng.gauss(0, 0.6)), 4)
        row['as_booked'] = {field: value}
    return row


# --- generation ---------------------------------------------------------------------------

def main():
    ids = [f'BE{i:04d}' for i in range(BENEFICIARY_COUNT)]
    register = {}
    for i, beneficiary in enumerate(ids):
        rng = keyed_rng('register|' + beneficiary)
        register[beneficiary] = dict(beneficiary_id=beneficiary, sector=rng.randrange(6),
                                    issuing_bank=f'BANK{rng.randrange(24):02d}', currency='USD',
                                    credit_limit_usd=round(math.exp(rng.uniform(13, 17)), 2),
                                    cohort='reference' if i < REFERENCE_COUNT else 'query',
                                    **{group: rng.randrange(4) for group in estimators.GROUPS})
        write_json(WORKSPACE / 'credit_register' / f'{beneficiary}.json', register[beneficiary])
    queries = [dict(record_id=f'{a}:p{q}', beneficiary_id=a, period=q) for q in QUERY_PERIODS for a in ids[REFERENCE_COUNT:]]
    estimators.write_rows(WORKSPACE / 'queries.jsonl', queries)
    for index, view in enumerate(estimators.VIEWS):
        filed = {q: [] for q in PERIODS}
        for q in PERIODS:
            for i in range(110):
                rng = keyed_rng(f'{view}|closed|{q}|{i}')
                group = rng.randrange(4)
                row = sample(index, rng)
                row.update(kind='closed', case_id=f'{index}-{q:02d}-{i:03d}', **{estimators.GROUPS[index]: group})
                row[estimators.OUTCOMES[index]] = outcome(index, row, rng, q, group)
                book(row, rng, index, q)
                filed[row['booked_period']].append(row)
            for a in ids:
                base = sample(index, keyed_rng(f'{view}|base|{a}'))
                values = list(base.values())
                if index == 5:
                    values[0] = math.log(values[0])
                row = sample(index, keyed_rng(f'{view}|snapshot|{a}|{q}'), values)
                row.update(kind='snapshot', beneficiary_id=a, period=q)
                filed[q].append(row)
        for q, rows in filed.items():
            estimators.write_rows(WORKSPACE / view / f'{q}.jsonl', rows)
    write_json(WORKSPACE / 'dataset_metadata.json', {
        'public_generation_key': PUBLIC_KEY, 'currency': 'USD', 'period_unit': 'month', 'periods': PERIODS,
        'history_periods': HISTORY_PERIODS, 'query_periods': QUERY_PERIODS, 'discrepancy_classes': CLASSES,
        'residual_category': 'discrepancies awaiting definitive class coding',
        'tenor_upper_days': [45, 95, 160], 'reference_beneficiaries': ids[:REFERENCE_COUNT],
        'ledger': 'Closed cases have event_period, booked_period, and optionally restated_period and as_booked.'})
    requested = [dict(record_id=f'{a}:p{q}', beneficiary_id=a, period=q) for q in HISTORY_PERIODS for a in ids[:REFERENCE_COUNT]]
    answers = estimators.records(WORKSPACE, requested + queries)
    history = [dict(a, beneficiary_id=r['beneficiary_id'], period=r['period']) for a, r in zip(answers, requested)]
    truth = answers[len(requested):]
    estimators.write_rows(WORKSPACE / 'history/examination.jsonl', history)
    estimators.write_rows(ROOT / 'tests/hidden/truth.jsonl', truth)
    report = {'beneficiaries': len(ids), 'history_rows': len(history), 'graded_rows': len(truth),
              'closed_cases_per_lane': 110 * len(PERIODS),
              'refusal_positive_count': sum(r['refusal_flag'] for r in truth),
              'tenor_counts': [sum(r['tenor_tier'] == c for r in truth) for c in range(4)],
              'numeric_ranges': {lane: [min(r[lane] for r in truth), max(r[lane] for r in truth)]
                                 for lane in ('discrepancy_count', 'charge_reserve')},
              'mean_pending_class_mass': sum(1 - sum(r['discrepancy_class_profile']) for r in truth) / len(truth)}
    write_json(ROOT / 'solution/measurements/generator_report.json', report)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
