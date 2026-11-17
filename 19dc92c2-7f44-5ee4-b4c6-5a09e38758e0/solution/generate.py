"""Private data construction for the fund administration NAV oversight task.

Run with ``python3 -B solution/generate.py``; never copy into the agent image.
All random draws become published inputs. Graded records are fitted expectations,
not realised random outcomes. Keyed streams and canonical serialization are stable.
"""
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

import estimators

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / 'environment' / 'workspace'
PUBLIC_KEY = 'fund-administration-nav-public-v1-2026'
FUND_COUNT = 360
REFERENCE_COUNT = 80
PERIODS = range(1, 21)
HISTORY_PERIODS = (8, 10, 12)
QUERY_PERIODS = (16, 20)
COMPONENTS = ['management fee', 'performance fee', 'admin fee', 'custody fee',
              'audit fee', 'transfer agency', 'regulatory', 'other']
RANGES = (
    ((0, .08), (0, 35), (0, .5), (0, 2), (0, 25), (1, 16)),
    ((20, 200), (0, .25), (0, .3), (16, 21), (0, 90), (1, 16)),
    ((0, 12), (0, 1), (0, .4), (0, 120), (0, 1), (0, 4)),
    ((0, 8), (0, 150), (0, 1), (1, 6), (0, 1), (0, 72)),
    ((0, .2), (0, .3), (0, .15), (0, 8), (0, 1), (0, 3)),
    ((0, .3), (0, 1), (0, 15), (.5, 1.5), (16, 21), (0, .7)))


def keyed_rng(label):
    return random.Random(int.from_bytes(hashlib.sha256(f'{PUBLIC_KEY}|{label}'.encode()).digest(), 'big'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n' for r in rows))


def features(rng, i, base=None) -> dict[str, Any]:
    values = [rng.uniform(lo, hi) for lo, hi in RANGES[i]]
    group = rng.randrange(4)
    if base is not None:
        values = [.45 * base[k] + .55 * v for k, v in zip(estimators.KEYS[i], values)]
        group = base['group']
    x = dict(zip(estimators.KEYS[i], values), group=group)
    if i == 5:
        x['annual_budget'] = round(math.exp(x['nav_log']) * rng.uniform(.001, .004), 2)
    return x


def outcome(rng, x, i, q):
    z = [(x[k] - lo) / (hi - lo) for k, (lo, hi) in zip(estimators.KEYS[i], RANGES[i])]
    a, b, c, d, e, f = z
    g = x['group']
    regime = q >= 14
    if i == 0:
        return round(math.exp(1.4 + 1.3*a + .7*b + .8*c + .5*math.sin(5*d) + .3*e + .15*g
                              + .25*regime + rng.gauss(0, .35)), 4)
    if i == 1:
        logits = [1.8*a, 3*b*c - .5, .5 + .25*g, .7*d, .6*e, .9*f, .1*g, .3 + b, .5 + e + .4*regime]
        amounts = [round(math.exp(v + rng.gauss(0, .5)) * 1000, 2) for v in logits]
        return amounts
    if i == 2:
        p = 1 / (1 + math.exp(-(-2 + 1.7*a + 1.4*b + c - 1.8*e + 1.2*a*b + .25*g + .2*regime)))
        return int(rng.random() < p)
    if i == 3:
        v = .6 - 2*a - 1.1*b + 1.8*c + .9*d - .8*e - .7*f + .25*g - .15*regime + rng.gauss(0, .4)
        return round(1 / (1 + math.exp(-v)), 6)
    if i == 4:
        return round(math.exp(1 + a + 1.8*b + c + .6*d + .6*math.sin(2*math.pi*e + .5*g)
                              + .7*a*b + .3*f + .2*regime + rng.gauss(0, .22)), 4)
    p = 1 / (1 + math.exp(-(-2 + 1.2*a + 1.4*b - c + .9*d + .2*g + .3*regime)))
    return round(x['annual_budget'] * math.exp(-2 + b + .25*g + rng.gauss(0, .45)), 2) if rng.random() < p else 0.0


def book(rng, row, q, field):
    """Store delayed booking and original outcomes alongside eventual corrections."""
    row['event_period'] = q
    row['booked_period'] = min(20, q + rng.choices([0, 1, 2], [6, 3, 1])[0])
    if rng.random() < .24:
        restated = row['booked_period'] + rng.randrange(1, 6)
        if restated <= 20:
            value = row[field]
            if field == 'reissued':
                original = 1 - value
            elif field == 'component_amounts':
                original = [round(v * math.exp(rng.gauss(0, .6)), 2) for v in value]
            elif field == 'reliability':
                original = round(min(1, max(0, value + rng.gauss(0, .2))), 6)
            elif field == 'overrun_amount' and value == 0:
                original = round(row['annual_budget'] * rng.uniform(.03, .3), 2)
            else:
                original = round(value * math.exp(rng.gauss(0, .5)), 4)
            row.update(restated_period=restated, as_booked={field: original})
    return row


def generate_inputs():
    ids = [f'FD{i:04d}' for i in range(FUND_COUNT)]
    for n, fund in enumerate(ids):
        rng = keyed_rng(f'register|{fund}')
        write_json(WORKSPACE / 'register' / f'{fund}.json', {
            'fund_id': fund, 'base_currency': 'USD', 'domicile': rng.choice(['IE', 'LU', 'US', 'KY']),
            'strategy': rng.choice(['equity', 'credit', 'multi-asset', 'alternatives']),
            'production_cycle': rng.choice(['daily', 'monthly']),
            'share_classes': [{'class_id': f'{fund}-{c}', 'currency': rng.choice(['USD', 'EUR', 'GBP'])} for c in ('A', 'I')],
            'cohort': 'reference' if n < REFERENCE_COUNT else 'query'})
    for i, view in enumerate(estimators.VIEWS):
        filed = {q: [] for q in PERIODS}
        for q in PERIODS:
            for n in range(100):
                rng = keyed_rng(f'{view}|closed|{q}|{n}')
                x = features(rng, i)
                row: dict[str, Any] = dict(x, case_id=f'{view}-{q}-{n}', kind='closed')
                row[estimators.TARGETS[i]] = outcome(rng, x, i, q)
                book(rng, row, q, estimators.TARGETS[i])
                filed[row['booked_period']].append(row)
        for fund in ids:
            base = features(keyed_rng(f'{view}|base|{fund}'), i)
            for q in PERIODS:
                x = features(keyed_rng(f'{view}|snapshot|{fund}|{q}'), i, base)
                filed[q].append(dict(x, fund_id=fund, period=q, kind='snapshot'))
        for q, rows in filed.items():
            write_rows(WORKSPACE / view / f'{q}.jsonl', rows)
    queries = [dict(record_id=f'{f}:p{q}', fund_id=f, period=q) for q in QUERY_PERIODS for f in ids[REFERENCE_COUNT:]]
    history_queries = [dict(record_id=f'{f}:p{q}', fund_id=f, period=q) for q in HISTORY_PERIODS for f in ids[:REFERENCE_COUNT]]
    write_rows(WORKSPACE / 'queries.jsonl', queries)
    write_json(WORKSPACE / 'dataset_metadata.json', {
        'public_generation_key': PUBLIC_KEY, 'periods': list(PERIODS), 'period_unit': 'monthly oversight cut',
        'history_periods': HISTORY_PERIODS, 'query_periods': QUERY_PERIODS, 'currency': 'USD',
        'fee_components': COMPONENTS, 'unallocated_component': 'unallocated accrual pending invoice allocation',
        'pricing_tiers': ['unreliable', 'limited', 'supported', 'independently corroborated'],
        'views': dict(zip(estimators.VIEWS, estimators.KEYS)),
        'group': 'view-specific operating segment code, 0 through 3; codes are not shared across views'})
    return history_queries, queries


def main():
    history_queries, queries = generate_inputs()
    rows = estimators.predict_all(WORKSPACE, history_queries + queries)
    history = [dict(r, fund_id=q['fund_id'], period=q['period']) for r, q in zip(rows, history_queries)]
    write_rows(WORKSPACE / 'history' / 'oversight.jsonl', history)
    write_rows(ROOT / 'tests' / 'hidden' / 'truth.jsonl', rows[len(history_queries):])
    report = {'funds': FUND_COUNT, 'history_rows': len(history), 'graded_rows': len(queries),
              'periods': len(PERIODS), 'seed': PUBLIC_KEY}
    write_json(ROOT / 'solution' / 'measurements' / 'generator_report.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
