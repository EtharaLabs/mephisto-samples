"""One full author-side certification; never writes outside this bundle.

Checks oracle bytes, alternate layouts, source/floor binding, lane deletion independence,
public-data schemas, syntax, scorer adversarial tests and the actual verifier entry point.
Docker runtime checks are reported separately; no claim is inferred from a source check.
"""
import ast
import hashlib
import json
import os
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'solution'))
import estimators
import make_alternates

WORKSPACE = ROOT / 'environment/workspace'
OUT = ROOT / 'solution/measurements'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, **kwargs):
    result = subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
                                     OPENBLAS_NUM_THREADS='1', PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'],
                                     **kwargs.pop('environment', {})), **kwargs)
    print(result.stdout, end='')
    return result


def main():
    report = {}
    for path in list((ROOT / 'solution').rglob('*.py')) + list((ROOT / 'tests').rglob('*.py')):
        compile(path.read_text(), str(path), 'exec')
    config = tomllib.loads((ROOT / 'task.toml').read_text())
    assert config['agent']['timeout_sec'] == 43200.0
    assert config['environment']['network_mode'] == 'no-network'
    report['syntax_and_config'] = True
    floors = json.loads((ROOT / 'solution/floors.json').read_text())
    assert all(sha(ROOT / path) == digest for path, digest in floors['sha256'].items())
    assert all(sha(WORKSPACE / path) == digest for path, digest in floors['workspace_sha256'].items())
    report['floor_source_and_workspace_hashes_match'] = True
    # Terms are a deliberate verbatim copy of the reference bundle; attribution differs by design.
    license_text = (ROOT / 'LICENSE').read_text()
    assert f"Task: {config['task']['name']}\n" in license_text, 'LICENSE must name this task'
    report['license_attributes_this_task'] = True
    reference_license = Path(os.environ.get(
        'REFERENCE_LICENSE',
        '/Users/apple/mephisto/staging/04fb6ba7-d838-59da-b07d-6b683edd47a1/LICENSE'))
    if reference_license.exists():
        marker = 'License scope'
        assert license_text.split(marker, 1)[1] == reference_license.read_text().split(marker, 1)[1]
        assert license_text.splitlines()[0] == reference_license.read_text().splitlines()[0]
        report['license_terms_identical_to_reference'] = True
    else:
        report['license_terms_identical_to_reference'] = 'reference not available on this machine'
    queries = estimators.read_rows(WORKSPACE / 'queries.jsonl')
    assert len(queries) == 560 and len({r['record_id'] for r in queries}) == 560
    assert len(list((WORKSPACE / 'credit_register').glob('*.json'))) == 360
    assert len(estimators.read_rows(WORKSPACE / 'history/examination.jsonl')) == 240
    for index in range(6):
        snaps, closed = estimators.load_view(WORKSPACE, index)
        assert len(snaps) == 7200 and len(closed) == 2200
        assert all((r['beneficiary_id'], r['period']) in snaps for r in queries)
    report['dataset_schema'] = True
    models = {lane: getattr(estimators, 'fit_' + lane)(WORKSPACE) for lane in estimators.LANES}
    predictions = {lane: [getattr(estimators, 'predict_' + lane)(models[lane], r['beneficiary_id'], r['period'], WORKSPACE)
                          for r in queries] for lane in estimators.LANES}
    changed = {}
    for removed in estimators.LANES:
        kept = {lane: model for lane, model in models.items() if lane != removed}
        for lane in kept:
            kept[lane].pop('rank_cache', None)
            out = [getattr(estimators, 'predict_' + lane)(kept[lane], r['beneficiary_id'], r['period'], WORKSPACE) for r in queries]
            changed[f'{removed}->{lane}'] = sum(a != b for a, b in zip(out, predictions[lane]))
    assert not any(changed.values())
    report['deletion_ablation_changed_rows'] = changed
    (OUT / 'independence.json').write_text(json.dumps(changed, indent=2) + '\n')
    for node in ast.walk(ast.parse((ROOT / 'solution/portfolio.py').read_text())):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] + [getattr(node, 'module', '') or '']
            assert not any('estimators' in name or 'score' in name or 'generate' in name for name in names)
    report['portfolio_has_no_oracle_or_scorer_import'] = True
    oracle = OUT / 'results/oracle'
    run(['sh', 'solution/solve.sh', str(WORKSPACE), str(oracle)])
    assert (oracle / 'predictions.jsonl').read_bytes() == (ROOT / 'tests/hidden/truth.jsonl').read_bytes()
    report['oracle_recomputes_truth_bytes'] = True
    make_alternates.main()
    report['alternate_bytes'] = {}
    for folder in ('renamed_single_module', 'split_modules', 'class_facade'):
        output = OUT / 'results' / folder
        run(['sh', f'solution/alternates/{folder}/solve.sh', str(WORKSPACE), str(output)])
        report['alternate_bytes'][folder] = sha(output / 'predictions.jsonl') == sha(oracle / 'predictions.jsonl')
    assert all(report['alternate_bytes'].values())
    tests = unittest.defaultTestLoader.discover(str(ROOT / 'solution/checks'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    report['scorer_tests'] = dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors))
    assert result.wasSuccessful()
    verifier = {}
    for name in ('oracle', 'hybrid', 'constant', 'empty'):
        logs = OUT / 'verifier' / name
        run(['sh', 'tests/test.sh', str(OUT / 'results' / name)], environment={'VERIFIER_LOG_DIR': str(logs)})
        reward = json.loads((logs / 'reward.json').read_text())['reward']
        structured = json.loads((logs / 'report.json').read_text())
        assert reward == float((logs / 'reward.txt').read_text()) == structured['score']
        verifier[name] = reward
    assert verifier['oracle'] == 1 and verifier['constant'] == verifier['empty'] == 0
    assert 0.35 <= verifier['hybrid'] <= 0.55
    report['verifier_scores'] = verifier
    ladder = json.loads((OUT / 'ladder.json').read_text())
    report['distinct_ladder_scores'] = len({r['score'] for r in ladder.values()})
    assert report['distinct_ladder_scores'] >= 8
    report['python'] = sys.version
    report['numpy'] = __import__('numpy').__version__
    report['scikit_learn'] = __import__('sklearn').__version__
    report['platform'] = sys.platform
    report['docker_execution'] = 'not run by this command'
    (OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    truth_record = ROOT / 'solution/TRUTH.md'
    text = truth_record.read_text().split('\n## Executed certification\n')[0]
    text += ('\n## Executed certification\n\n'
             + 'The final native certification completed successfully. Observed verifier scores: '
             + ', '.join(f'{name} **{value:.4f}**' for name, value in verifier.items()) + '.\n\n'
             + f"Scorer tests executed: **{result.testsRun}**, failures **{len(result.failures)}**, errors **{len(result.errors)}**. "
             + f"Lane-deletion comparisons: **{len(changed)}**, changed predictions **{sum(changed.values())}**. "
             + f"All **{len(report['alternate_bytes'])}** alternate layouts produced byte-identical truth. "
             + 'The oracle independently recomputed the frozen truth bytes; floor source and workspace hashes matched. '
             + 'See `measurements/verification.json` for machine-readable evidence.\n')
    truth_record.write_text(text)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
