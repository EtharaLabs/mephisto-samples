"""Frozen public cheap tier and degenerate controls; never reads private truth.

Each cheap method fills all six lanes. A method substitutes its own naive value into one or two
lanes and takes the global historical-median anchor for the others. No fitted multivariate
estimator appears here; that tier lives in portfolio.py.
"""
import json
import statistics
from pathlib import Path

LANES = ('dilution_reserve', 'collection_profile', 'dispute_flag', 'recovery_tier', 'availability_rank', 'loss_reserve')
CHEAP = ('balance_haircut', 'sector_median', 'prior_period_carry', 'advance_rate_table', 'terms_schedule')
BUCKETS = [15, 30, 45, 60, 90, 120, 180, 270]


def read_jsonl(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def snapshots(workspace, view, keyed_by_obligor):
    table = {}
    for path in (workspace / view).glob('*.jsonl'):
        for row in read_jsonl(path):
            if row.get('kind') == 'snapshot':
                table[row['obligor_id'], row['period']] = row
    return table


def generate(workspace):
    history = read_jsonl(workspace / 'history/surveillance.jsonl')
    queries = read_jsonl(workspace / 'queries.jsonl')
    register = {p.stem: json.loads(p.read_text()) for p in (workspace / 'register').glob('*.json')}
    dilution = snapshots(workspace, 'dilution', False)
    borrowing = snapshots(workspace, 'borrowing_base', False)
    writeoffs = snapshots(workspace, 'writeoffs', True)
    collections = snapshots(workspace, 'collections', False)

    def anchor(rows, mean=False):
        rows = rows or history
        reducer = statistics.mean if mean else statistics.median
        result = {}
        for lane in LANES:
            if lane == 'collection_profile':
                v = [reducer(r[lane][j] for r in rows) for j in range(8)]
                result[lane] = [x / max(1.0, sum(v)) for x in v]
            elif lane in ('dispute_flag', 'recovery_tier'):
                counts = {c: sum(r[lane] == c for r in rows) for c in (range(2) if lane == 'dispute_flag' else range(4))}
                result[lane] = max(counts, key=lambda c: (counts[c], -c))
            else:
                result[lane] = reducer(r[lane] for r in rows)
        return result

    global_median = anchor(history)
    method_rows = {m: [] for m in CHEAP}
    control_names = ['empty', 'constant_zero', 'constant_one', 'constant_sector_mean', 'constant_median',
                     'all_flag', 'no_flag', 'uniform_distribution', 'identity_ranking', 'reverse_identity_ranking']
    control_names += ['tier_' + str(c) for c in range(4)]
    control_names += ['point_mass_' + str(c) for c in range(9)]
    controls = {m: [] for m in control_names}
    period_index = {}
    table_nets = {}
    for query in queries:
        aid, period = query['obligor_id'], query['period']
        bb = borrowing[aid, period]
        table_nets[query['record_id']] = bb['gross_receivables'] * (0.70, 0.75, 0.80, 0.85)[bb['advance_band']] - bb['reserve_holdback'] - bb['drawn_balance']
    table_ranks = {}
    for period in sorted({q['period'] for q in queries}):
        ids = [q['record_id'] for q in queries if q['period'] == period]
        order = {v: i + 1 for i, v in enumerate(sorted({table_nets[r] for r in ids}, reverse=True))}
        for r in ids:
            table_ranks[r] = order[table_nets[r]]
    for query in queries:
        rid, aid, period = query['record_id'], query['obligor_id'], query['period']
        sector = [r for r in history if register[r['obligor_id']]['sector'] == register[aid]['sector'] and r['period'] < period]
        sector_anchor = anchor(sector)
        own = [r for r in history if r['obligor_id'] == aid and r['period'] < period]
        carry = own or sector
        latest = max(r['period'] for r in carry)
        carry = anchor([r for r in carry if r['period'] == latest])
        terms = collections[aid, period]['terms_days']
        bucket = next(i for i, u in enumerate(BUCKETS) if terms <= u)
        schedule = [0.0] * 8
        for offset, mass in ((0, 0.45), (1, 0.25), (2, 0.15), (3, 0.08)):
            if bucket + offset < 8:
                schedule[bucket + offset] += mass
        choices = {
            'balance_haircut': dict(global_median, dilution_reserve=0.03 * dilution[aid, period]['open_balance'],
                                    loss_reserve=0.01 * writeoffs[aid, period]['exposure'] * (1 - writeoffs[aid, period]['insured_share'])),
            'sector_median': sector_anchor,
            'prior_period_carry': carry,
            'advance_rate_table': dict(global_median, availability_rank=table_ranks[rid]),
            'terms_schedule': dict(sector_anchor, collection_profile=schedule),
        }
        for name, row in choices.items():
            method_rows[name].append(dict(row, record_id=rid))
        period_index[period] = period_index.get(period, 0) + 1
        for name in controls:
            if name == 'empty':
                continue
            row = dict(global_median, record_id=rid)
            if name in ('constant_zero', 'constant_one'):
                value = int(name == 'constant_one')
                row.update({lane: ([value] * 8 if lane == 'collection_profile' else value) for lane in LANES})
            elif name == 'constant_sector_mean':
                row.update(anchor(sector, mean=True))
            elif name in ('all_flag', 'no_flag'):
                row.update(dispute_flag=int(name == 'all_flag'), recovery_tier=0 if name == 'all_flag' else 3)
            elif name.startswith('tier_'):
                row['recovery_tier'] = int(name.rsplit('_', 1)[-1])
            elif name == 'uniform_distribution':
                row['collection_profile'] = [1 / 8] * 8
            elif name.startswith('point_mass_'):
                b = int(name.rsplit('_', 1)[-1])
                row['collection_profile'] = [int(b == j) for j in range(8)]
            elif name in ('identity_ranking', 'reverse_identity_ranking'):
                row['availability_rank'] = period_index[period] * (-1 if name.startswith('reverse') else 1)
            controls[name].append(row)
    return method_rows, controls


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as handle:
        for row in rows:
            handle.write(json.dumps(row, allow_nan=False) + '\n')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    methods, controls = generate(root / 'environment/workspace')
    for name, rows in {**methods, **controls}.items():
        write_rows(root / 'solution/measurements/results' / name / 'predictions.jsonl', rows)
    print(json.dumps({'cheap': list(methods), 'controls': list(controls)}))
