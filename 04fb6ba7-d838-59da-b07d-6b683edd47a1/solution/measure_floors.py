"""One frozen floor measurement; only the scorer manifest and floors.json are written.

Portfolio workers receive only the public workspace and audit every file open. The real scorer's
submission reader is adapted to in-memory rows; the scoring arithmetic is unchanged. The floor of
each lane is the maximum metric over the cheap tier, every degenerate control, the optimised
distribution-derived envelope, and both one-shot competent tiers, except where a tier would leave
the lane with less than a 0.10 payable range, which is recorded as a disclosed exclusion.
The public reference is measured afterwards and never sets a floor.
"""
import copy
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests' / 'scoring'))
import score  # noqa: E402

DEAD_LANE = 0.10


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar_constant(actual, bound):
    knots = {0.0}
    for a in actual:
        d = max(abs(a), bound)
        knots.update((max(0.0, a - d), a, a + d))
    knots = sorted(knots)

    def objective(value):
        return -score.relative_agreement([(value, a) for a in actual], bound)

    candidates = [(objective(v), v) for v in knots]
    for left, right in zip(knots, knots[1:]):
        fit = minimize_scalar(objective, bounds=(left, right), method='bounded', options={'xatol': 1e-8, 'maxiter': 70})
        candidates.append((float(fit.fun), float(fit.x)))
    loss, value = min(candidates)
    return value, {'domain': [0.0, knots[-1]], 'intervals': len(knots) - 1, 'value': value, 'attained_metric': -loss,
                   'proof': 'affine/positive-convex quasiconcavity on every error breakpoint interval; beyond domain score=0'}


def distribution_constant(actual):
    vectors = [score._distribution_vector(v, 8) for v in actual]
    assert all(v is not None for v in vectors)
    segments = []
    for j in range(9):
        previous, values = 0.0, sorted(v[j] for v in vectors)
        for i, value in enumerate(values):
            if value > previous:
                segments.append((len(values) - i, j, value - previous))
            previous = value
    q, remaining = [0.0] * 9, 1.0
    for slope, j, width in sorted(segments, key=lambda s: (-s[0], s[1])):
        mass = min(remaining, width)
        q[j] += mass
        remaining -= mass
        if remaining <= 1e-15:
            break
    if remaining > 1e-15:
        q[8] += remaining
    if math.fsum(q[:8]) > 1.0:
        q[:8] = [v / math.fsum(q[:8]) for v in q[:8]]
    return q[:8], {'vector_including_uncollected': q, 'segments': len(segments), 'proof': 'exact empirical marginal-slope allocation over the complete 9-category simplex'}


def prediction_mapping(rows):
    seen, duplicates = {}, set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('record_id'), str):
            continue
        key = row['record_id']
        if key in seen:
            duplicates.add(key)
        seen[key] = row
    return {k: v for k, v in seen.items() if k not in duplicates}


def main():
    manifest_path = ROOT / 'tests/scoring/scorer_manifest.json'
    old_manifest = json.loads(manifest_path.read_text())
    workers = {}
    for mode in ('oneshot', 'cheap'):
        worker = subprocess.run([sys.executable, '-B', str(ROOT / 'solution/portfolio.py'), str(ROOT / 'environment/workspace'), mode],
                                check=True, capture_output=True, text=True, cwd=ROOT / 'solution',
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        workers[mode] = json.loads(worker.stdout)
        assert workers[mode]['audit']['violations'] == 0
    methods = dict(workers['cheap']['methods'], **workers['oneshot']['methods'])
    controls = workers['cheap']['controls']
    truth_path = ROOT / 'tests/hidden/truth.jsonl'
    truth = score.read_jsonl(truth_path)
    constants, envelope = {}, {}
    for lane, bound in (('dilution_reserve', score.DILUTION_BOUND), ('loss_reserve', score.LOSS_BOUND)):
        constants[lane], envelope[lane] = scalar_constant([r[lane] for r in truth], bound)
    constants['collection_profile'], envelope['collection_profile'] = distribution_constant([r['collection_profile'] for r in truth])
    constants['dispute_flag'] = 1
    best_rank = max(range(1, 281), key=lambda c: score.rank_agreement([(c, r['availability_rank']) for r in truth]))
    constants['availability_rank'] = best_rank
    labels = sorted({r['recovery_tier'] for r in truth})
    constants['recovery_tier'] = max(labels, key=lambda c: score.macro_f1([(c, r['recovery_tier']) for r in truth], labels))
    envelope['dispute_flag'] = {'constant': 1, 'proof': 'positive-class F1 best constant is all-positive'}
    envelope['recovery_tier'] = {'constant': constants['recovery_tier'], 'labels': labels, 'proof': 'exhaust all admissible constant labels'}
    envelope['availability_rank'] = {'constant': best_rank, 'proof': 'exhaust every constant rank 1..280 under the tolerance-band metric'}
    rows = dict(methods, **controls)
    rows['degenerate_envelope'] = [dict(constants, record_id=r['record_id']) for r in truth]
    names = list(rows)

    def evaluate(name, manifest_file=manifest_path):
        with patch.object(score, 'read_submission', lambda submission_dir, tripped=None: prediction_mapping(rows[name])):
            report = score.evaluate_report(name, truth_path, str(manifest_file))
        assert len(report['lanes']) == 6, report
        return report

    initial = {name: evaluate(name) for name in names}
    manifest = copy.deepcopy(old_manifest)
    decisions, excluded = {}, {}
    for lane in score.LANES:
        ranked = sorted(names, key=lambda n: -initial[n]['lanes'][lane]['metric'])
        eligible = list(ranked)
        # drop the strongest member while it would leave less than the dead-lane payable range,
        # but only one-shot members may be dropped; cheap methods and controls always count
        while eligible and 1 - initial[eligible[0]]['lanes'][lane]['metric'] < DEAD_LANE and eligible[0].startswith('oneshot_'):
            excluded.setdefault(lane, []).append({'method': eligible[0], 'metric': initial[eligible[0]]['lanes'][lane]['metric']})
            eligible.pop(0)
        source = eligible[0]
        floor = initial[source]['lanes'][lane]['metric']
        assert math.isfinite(floor) and 0.0 <= floor < 1.0, (lane, floor)
        manifest['lanes'][lane].update(floor=floor, floor_source=source)
        decisions[lane] = {'measured_max': floor, 'source': source, 'ranked_top5': [(n, initial[n]['lanes'][lane]['metric']) for n in ranked[:5]],
                           'excluded_from_floor': excluded.get(lane, []), 'payable': 1 - floor, 'dead_lane_risk': 1 - floor < DEAD_LANE}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    measured = {name: evaluate(name) for name in names}
    zero_names = [n for n in names if not any(x['method'] == n for lane in excluded for x in excluded[lane])]
    for name in zero_names:
        assert measured[name]['score'] == 0.0, (name, measured[name]['score'])
    results = ROOT / 'solution/measurements/results'
    reports = {}
    for variant, flag in (('public_reference', []), ('public_reference_asof', ['--asof'])):
        out = results / variant
        subprocess.run([sys.executable, '-B', str(ROOT / 'solution/public_reference.py'), '--workspace', str(ROOT / 'environment/workspace'),
                        '--output', str(out / 'predictions.jsonl'), '--audit', str(out / 'audit.json')] + flag,
                       check=True, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        reports[variant] = score.evaluate_report(out, truth_path, str(manifest_path))
    oracle_dir, empty_dir = results / 'oracle', results / 'empty'
    oracle_dir.mkdir(parents=True, exist_ok=True)
    empty_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-B', str(ROOT / 'solution/estimators.py'), '--workspace', str(ROOT / 'environment/workspace'),
                    '--output', str(oracle_dir / 'predictions.jsonl')], check=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    (empty_dir / 'predictions.jsonl').write_text('')
    oracle = score.evaluate_report(oracle_dir, truth_path, str(manifest_path))
    nop = score.evaluate_report(empty_dir, truth_path, str(manifest_path))
    assert oracle['score'] == 1.0 and nop['score'] == 0.0, (oracle['score'], nop['score'])
    assert all(v['metric'] == v['fraction'] == v['points'] == 1.0 for v in oracle['lanes'].values())
    assert sha(oracle_dir / 'predictions.jsonl') == sha(truth_path), 'oracle must recompute the frozen truth byte for byte'
    for invalid in (float('nan'), float('inf'), 1.0, 1.01, -0.1):
        bad = copy.deepcopy(manifest)
        bad['lanes']['recovery_tier']['floor'] = invalid
        try:
            score.lane_points({lane: 1.0 for lane in score.LANES}, bad)
        except ValueError as exc:
            assert str(exc) == 'invalid lane floor'
        else:
            raise AssertionError('invalid lane floor accepted')
    output = {'floors': manifest['lanes'], 'old_floors': old_manifest['lanes'], 'dead_lane_threshold': DEAD_LANE,
              'methods': {n: measured[n] for n in methods}, 'controls': {n: measured[n] for n in controls},
              'degenerate_envelope': measured['degenerate_envelope'], 'envelope_parameters': envelope, 'decisions': decisions,
              'exact_zero_asserted': zero_names, 'public_reference': reports['public_reference'],
              'public_reference_asof_private_diagnostic': reports['public_reference_asof'], 'oracle': oracle, 'nop': nop,
              'oracle_recomputes_truth_bytes': True, 'invalid_floor_checks': 5,
              'audits': {n: w['audit'] for n, w in workers.items()}, 'public_is_floor_setter': False,
              'sha256': {str(p.relative_to(ROOT)): sha(p) for p in (truth_path, manifest_path, Path(__file__), ROOT / 'solution/portfolio.py',
                                                                      ROOT / 'solution/cheap_portfolio.py', ROOT / 'solution/public_reference.py',
                                                                      ROOT / 'solution/estimators.py', ROOT / 'tests/scoring/score.py')}}
    (ROOT / 'solution/floors.json').write_text(json.dumps(output, indent=2, allow_nan=False) + '\n')
    print('FLOORS lane | floor | payable | source | excluded')
    for lane, spec in manifest['lanes'].items():
        print(lane, round(spec['floor'], 4), round(1 - spec['floor'], 4), spec['floor_source'], [x['method'] for x in excluded.get(lane, [])], sep=' | ')
    print('PROFILE lane order:', ', '.join(score.LANES))
    for name, report in dict(measured, PUBLIC=reports['public_reference'], PUBLIC_ASOF=reports['public_reference_asof']).items():
        print(name, [round(report['lanes'][l]['metric'], 3) for l in score.LANES], [round(report['lanes'][l]['points'], 3) for l in score.LANES], report['score'], sep=' | ')
    print('ENDPOINTS oracle=', oracle['score'], 'nop=', nop['score'])
    for name, worker in workers.items():
        print('AUDIT', name, 'reads=', worker['audit']['permitted_reads'], 'unique_paths=', len(worker['audit']['paths']), 'violations=', worker['audit']['violations'])


if __name__ == '__main__':
    main()
