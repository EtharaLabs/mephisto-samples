"""Frozen public cheap tier and degenerate controls; never reads private truth.

Each cheap method fills all six lanes. A method substitutes its own naive value into one or two
lanes and takes the global historical-median anchor for the others. No fitted multivariate
estimator appears here; that tier lives in portfolio.py.
"""
import json
import statistics
from pathlib import Path

LANES = ('aging_reserve', 'turn_profile', 'sot_flag', 'variance_tier', 'headroom_rank', 'loss_reserve')
CHEAP = ('aged_haircut_table', 'franchise_median', 'prior_period_carry', 'line_utilisation_table', 'velocity_schedule')


def read_jsonl(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def snapshots(workspace, view):
    table = {}
    for path in (workspace / view).glob('*.jsonl'):
        for row in read_jsonl(path):
            if row.get('kind') == 'snapshot':
                table[row['dealer_id'], row['period']] = row
    return table


def generate(workspace):
    history = read_jsonl(workspace / 'history/surveillance.jsonl')
    queries = read_jsonl(workspace / 'queries.jsonl')
    register = {p.stem: json.loads(p.read_text()) for p in (workspace / 'register').glob('*.json')}
    aging = snapshots(workspace, 'aging')
    lines = snapshots(workspace, 'lines')
    repossessions = snapshots(workspace, 'repossessions')
    turns = snapshots(workspace, 'turns')

    def anchor(rows, mean=False):
        rows = rows or history
        reducer = statistics.mean if mean else statistics.median
        result = {}
        for lane in LANES:
            if lane == 'turn_profile':
                v = [reducer(r[lane][j] for r in rows) for j in range(8)]
                result[lane] = [x / max(1.0, sum(v)) for x in v]
            elif lane in ('sot_flag', 'variance_tier'):
                counts = {c: sum(r[lane] == c for r in rows) for c in (range(2) if lane == 'sot_flag' else range(4))}
                result[lane] = max(counts, key=lambda c: (counts[c], -c))
            else:
                result[lane] = reducer(r[lane] for r in rows)
        return result

    global_median = anchor(history)
    method_rows = {m: [] for m in CHEAP}
    control_names = ['empty', 'constant_zero', 'constant_one', 'constant_franchise_mean', 'constant_median',
                     'all_flag', 'no_flag', 'uniform_distribution', 'identity_ranking', 'reverse_identity_ranking']
    control_names += ['tier_' + str(c) for c in range(4)]
    control_names += ['point_mass_' + str(c) for c in range(9)]
    controls = {m: [] for m in control_names}
    period_index = {}
    table_headroom = {}
    for query in queries:
        aid, period = query['dealer_id'], query['period']
        ln = lines[aid, period]
        table_headroom[query['record_id']] = ln['credit_line'] * 0.85 - ln['outstanding'] - ln['pending_payoffs']
    table_ranks = {}
    for period in sorted({q['period'] for q in queries}):
        ids = [q['record_id'] for q in queries if q['period'] == period]
        order = {v: i + 1 for i, v in enumerate(sorted({table_headroom[r] for r in ids}, reverse=True))}
        for r in ids:
            table_ranks[r] = order[table_headroom[r]]
    for query in queries:
        rid, aid, period = query['record_id'], query['dealer_id'], query['period']
        franchise = [r for r in history if register[r['dealer_id']]['franchise'] == register[aid]['franchise'] and r['period'] < period]
        franchise_anchor = anchor(franchise)
        own = [r for r in history if r['dealer_id'] == aid and r['period'] < period]
        carry = own or franchise
        latest = max(r['period'] for r in carry)
        carry = anchor([r for r in carry if r['period'] == latest])
        velocity = turns[aid, period]['lot_velocity']
        start = 0 if velocity > 0.66 else (1 if velocity > 0.33 else 2)
        schedule = [0.0] * 8
        for offset, mass in ((0, 0.45), (1, 0.25), (2, 0.15), (3, 0.08)):
            if start + offset < 8:
                schedule[start + offset] += mass
        ag = aging[aid, period]
        rp = repossessions[aid, period]
        choices = {
            'aged_haircut_table': dict(global_median, aging_reserve=0.15 * ag['floored_balance'] * ag['aged_share'],
                                       loss_reserve=0.02 * rp['exposure']),
            'franchise_median': franchise_anchor,
            'prior_period_carry': carry,
            'line_utilisation_table': dict(global_median, headroom_rank=table_ranks[rid]),
            'velocity_schedule': dict(franchise_anchor, turn_profile=schedule),
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
                row.update({lane: ([value] * 8 if lane == 'turn_profile' else value) for lane in LANES})
            elif name == 'constant_franchise_mean':
                row.update(anchor(franchise, mean=True))
            elif name in ('all_flag', 'no_flag'):
                row.update(sot_flag=int(name == 'all_flag'), variance_tier=3 if name == 'all_flag' else 0)
            elif name.startswith('tier_'):
                row['variance_tier'] = int(name.rsplit('_', 1)[-1])
            elif name == 'uniform_distribution':
                row['turn_profile'] = [1 / 8] * 8
            elif name.startswith('point_mass_'):
                b = int(name.rsplit('_', 1)[-1])
                row['turn_profile'] = [int(b == j) for j in range(8)]
            elif name in ('identity_ranking', 'reverse_identity_ranking'):
                row['headroom_rank'] = period_index[period] * (-1 if name.startswith('reverse') else 1)
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
