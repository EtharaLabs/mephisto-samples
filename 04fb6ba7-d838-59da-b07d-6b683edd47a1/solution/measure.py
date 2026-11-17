"""Author-side diagnostics, NOT a scorer, floor or solve implementation. Writes JSON under
solution/measurements/. Standard library only.

  independence     syntax-tree walk of estimators.py: no fit_/predict_ function of one lane calls
                   another lane's function, and a deletion ablation that removes each lane's fitted
                   object and checks every other lane's predictions are unchanged
  asof_ablation    recompute the truth with the ledger discipline disabled (corrected values
                   throughout, every booked row) and report per-lane agreement with the real truth
  nonregression    regenerate the truth twice and require byte identity
  single_field     the best single published snapshot field as a rank predictor for the
                   availability lane, to show no single column carries the cohort ordering
"""
import ast
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'solution'))
sys.path.insert(0, str(ROOT / 'tests' / 'scoring'))
import estimators  # noqa: E402
import score  # noqa: E402

W = ROOT / 'environment' / 'workspace'
M = ROOT / 'solution' / 'measurements'
LANES = estimators.LANES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independence():
    tree = ast.parse((ROOT / 'solution/estimators.py').read_text())
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    lane_of = {}
    for name in functions:
        for lane in LANES:
            if name.endswith(lane):
                lane_of[name] = lane
    helpers = {'recovery_score': 'recovery_tier', 'availability_net': 'availability_rank', 'availability_basis': 'availability_rank',
               '_dilution_design': 'dilution_reserve', '_local_linear': 'dilution_reserve', '_weighted_km': 'collection_profile',
               '_restricted_mean': 'collection_profile', '_survival_at': 'collection_profile', '_dispute_features': 'dispute_flag',
               '_dispute_design': 'dispute_flag', '_recovery_point': 'recovery_tier', '_nadaraya_watson': 'recovery_tier'}
    lane_of.update(helpers)
    cross = []
    for name, node in functions.items():
        owner = lane_of.get(name)
        if owner is None:
            continue
        for call in ast.walk(node):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                callee = call.func.id
                other = lane_of.get(callee)
                if other is not None and other != owner:
                    cross.append((name, callee))
    shared = sorted(n for n in functions if n not in lane_of and n != 'main')
    return {'cross_lane_calls': cross, 'shared_transport_helpers': shared, 'lane_functions': sorted(lane_of)}


def deletion_ablation(fitted, queries):
    base = {lane: [getattr(estimators, 'predict_' + lane)(fitted[lane], r['obligor_id'], r['period'], W) for r in queries] for lane in LANES}
    changed = {}
    for removed in LANES:
        kept = {k: v for k, v in fitted.items() if k != removed}
        for lane in LANES:
            if lane == removed:
                continue
            fresh = {k: (dict(v) if isinstance(v, dict) else v) for k, v in kept.items()}
            for v in fresh.values():
                if isinstance(v, dict):
                    v.pop('rank_cache', None)
                    v.pop('tier_cache', None)
            out = [getattr(estimators, 'predict_' + lane)(fresh[lane], r['obligor_id'], r['period'], W) for r in queries]
            changed[(removed, lane)] = sum(a != b for a, b in zip(out, base[lane]))
    return {f'{removed}->{lane}': n for (removed, lane), n in changed.items()}, base


def asof_ablation(base, queries):
    original = estimators.asof

    def naive(rows, q):
        return [r for r in rows if r.get('kind') == 'closed' and r['booked_period'] < q]

    estimators.asof = naive
    try:
        fitted = {lane: getattr(estimators, 'fit_' + lane)(W) for lane in LANES}
        alt = {lane: [getattr(estimators, 'predict_' + lane)(fitted[lane], r['obligor_id'], r['period'], W) for r in queries] for lane in LANES}
    finally:
        estimators.asof = original
    truth = {r['record_id']: dict(r, **{lane: base[lane][i] for lane in LANES}) for i, r in enumerate(queries)}
    predictions = {r['record_id']: {lane: alt[lane][i] for lane in LANES} for i, r in enumerate(queries)}
    metrics, _, _, _ = score.lane_metrics(predictions, truth)
    agree = {lane: sum(a == b for a, b in zip(alt[lane], base[lane])) / len(queries) for lane in LANES}
    return {'raw_metric_of_naive_truth_against_real_truth': metrics, 'exact_agreement_share': agree,
            'interpretation': 'the lane metric a solver reaches by reproducing the private method exactly but reading corrected values throughout'}


def single_field_sorts(queries, base):
    fields = {}
    for view in ('dilution', 'collections', 'delinquencies', 'borrowing_base'):
        for path in sorted((W / view).glob('*.jsonl')):
            for line in open(path):
                r = json.loads(line)
                if r.get('kind') == 'snapshot':
                    for k, v in r.items():
                        if isinstance(v, (int, float)) and not isinstance(v, bool) and k != 'period':
                            fields.setdefault(f'{view}.{k}', {})[(r['obligor_id'], r['period'])] = v
    truth = {r['record_id']: dict(r, **{lane: base[lane][i] for lane in LANES}) for i, r in enumerate(queries)}
    results = {}
    for name, table in fields.items():
        for direction in ('ascending', 'descending'):
            pred = {k: {lane: v[lane] for lane in LANES} for k, v in truth.items()}
            for period in sorted({r['period'] for r in queries}):
                ids = [r for r in queries if r['period'] == period]
                values = {r['record_id']: table[r['obligor_id'], period] for r in ids}
                order = sorted(set(values.values()), reverse=(direction == 'descending'))
                rank = {v: i + 1 for i, v in enumerate(order)}
                for r in ids:
                    pred[r['record_id']]['availability_rank'] = rank[values[r['record_id']]]
            metrics, _, _, _ = score.lane_metrics(pred, truth)
            results[f'{name}::{direction}'] = metrics['availability_rank']
    best = max(results, key=results.get)
    return {'best_rule': best, 'best_metric': results[best], 'field_count': len(fields), 'top5': sorted(results.items(), key=lambda kv: -kv[1])[:5]}


def nonregression():
    truth_path = ROOT / 'tests/hidden/truth.jsonl'
    before = sha(truth_path)
    import generate
    importlib.reload(generate)
    generate.main()
    after = sha(truth_path)
    return {'truth_sha256_before': before, 'truth_sha256_after': after, 'identical': before == after}


def main():
    queries = estimators.read_rows(W / 'queries.jsonl')
    fitted = {lane: getattr(estimators, 'fit_' + lane)(W) for lane in LANES}
    out = {'independence': independence()}
    ablation, base = deletion_ablation(fitted, queries)
    out['deletion_ablation_changed_rows'] = ablation
    assert not out['independence']['cross_lane_calls'], out['independence']
    assert all(n == 0 for n in ablation.values()), ablation
    out['asof_ablation'] = asof_ablation(base, queries)
    out['single_field_sorts'] = single_field_sorts(queries, base)
    out['nonregression'] = nonregression()
    assert out['nonregression']['identical']
    M.mkdir(parents=True, exist_ok=True)
    (M / 'independence.json').write_text(json.dumps({'independence': out['independence'], 'deletion_ablation_changed_rows': out['deletion_ablation_changed_rows']}, indent=2) + '\n')
    (M / 'asof_ablation.json').write_text(json.dumps(out['asof_ablation'], indent=2) + '\n')
    (M / 'single_field_sorts.json').write_text(json.dumps(out['single_field_sorts'], indent=2) + '\n')
    (M / 'nonregression.json').write_text(json.dumps(out['nonregression'], indent=2) + '\n')
    print(json.dumps({'cross_lane_calls': out['independence']['cross_lane_calls'],
                      'deletion_changes': sum(out['deletion_ablation_changed_rows'].values()),
                      'asof_naive_metrics': {k: round(v, 4) for k, v in out['asof_ablation']['raw_metric_of_naive_truth_against_real_truth'].items()},
                      'asof_exact_agreement': {k: round(v, 3) for k, v in out['asof_ablation']['exact_agreement_share'].items()},
                      'single_field_best': out['single_field_sorts']['best_rule'], 'single_field_metric': round(out['single_field_sorts']['best_metric'], 4),
                      'nonregression_identical': out['nonregression']['identical']}, indent=1))


if __name__ == '__main__':
    main()
