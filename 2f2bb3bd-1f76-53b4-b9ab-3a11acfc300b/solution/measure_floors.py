"""Measure frozen competent floors, then freeze their source and data hashes.

Floors are the per-lane maximum of eligible default forests and public degenerate controls.
The history forest is excluded on profile and tenor to preserve headroom for other methods.
Re-running this command recomputes measurements against the delivered sources.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import cheap_portfolio
import portfolio

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / 'environment/workspace'
RESULTS = ROOT / 'solution/measurements/results'
spec = importlib.util.spec_from_file_location('desk_score', ROOT / 'tests/scoring/score.py')
assert spec is not None and spec.loader is not None
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
KINDS = ('relative_agreement', 'distribution_overlap', 'f1_detection', 'macro_f1', 'rank_agreement', 'relative_agreement')
EXCLUDED_METHODS = {
    'discrepancy_class_profile': ['history_forest'],
    'tenor_tier': ['history_forest'],
}
FLOOR_POLICY = (
    'max(default closed-case forest, default history forest, public constant controls); '
    'history_forest excluded on discrepancy_class_profile and tenor_tier, where it is '
    'near-oracle and left zero headroom for any other measured method'
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    predictions = cheap_portfolio.generate(WORKSPACE)
    predictions['oneshot_forest'] = portfolio.predict(WORKSPACE, 'oneshot_forest')
    predictions['history_forest'] = portfolio.predict(WORKSPACE, 'history_forest')
    truth_path = ROOT / 'tests/hidden/truth.jsonl'
    truth = {r['record_id']: r for r in score.read_jsonl(truth_path)}
    raw = {}
    for name, rows in predictions.items():
        portfolio.write_rows(RESULTS / name / 'predictions.jsonl', rows)
        raw[name] = score.lane_metrics({r['record_id']: r for r in rows}, truth)[0]
    manifest = {'lanes': {}, 'relative_agreement_bounds': {'discrepancy_count': score.COUNT_BOUND, 'charge_reserve': score.CHARGE_BOUND}}
    for lane, kind in zip(score.LANES, KINDS):
        eligible = [name for name in raw if name not in EXCLUDED_METHODS.get(lane, [])]
        source = max(eligible, key=lambda n: raw[n][lane])
        floor = raw[source][lane]
        assert 0 <= floor < 1, (lane, floor)
        manifest['lanes'][lane] = dict(weight=1.0, metric_kind=kind, floor=floor, floor_source=source)
    manifest_path = ROOT / 'tests/scoring/scorer_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    reports = {n: score.evaluate_report(RESULTS / n, truth_path) for n in predictions}
    for lane in score.LANES:
        eligible = [name for name in raw if name not in EXCLUDED_METHODS.get(lane, [])]
        assert manifest['lanes'][lane]['floor'] == max(raw[name][lane] for name in eligible)
        assert all(reports[name]['lanes'][lane]['points'] == 0 for name in eligible)
    excluded = {name for names in EXCLUDED_METHODS.values() for name in names}
    assert all(report['score'] == 0 for name, report in reports.items() if name not in excluded)
    sources = ['solution/generate.py', 'solution/estimators.py', 'solution/portfolio.py', 'solution/cheap_portfolio.py',
               'solution/measure_floors.py', 'tests/scoring/score.py', 'tests/scoring/scorer_manifest.json', 'tests/hidden/truth.jsonl']
    output = {'floor_policy': FLOOR_POLICY, 'excluded_methods': EXCLUDED_METHODS,
              'floors': manifest['lanes'], 'methods': reports, 'raw_metrics': raw,
              'sha256': {p: sha(ROOT / p) for p in sources},
              'workspace_sha256': {str(p.relative_to(WORKSPACE)): sha(p) for p in sorted(WORKSPACE.rglob('*')) if p.is_file()}}
    (ROOT / 'solution/floors.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
