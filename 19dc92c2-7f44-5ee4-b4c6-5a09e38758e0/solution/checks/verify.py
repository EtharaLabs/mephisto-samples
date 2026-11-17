"""One final verification pass, writing observed evidence only beneath this bundle."""
import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'solution'))
sys.path.insert(0, str(ROOT / 'tests' / 'scoring'))
import estimators
from public_reference import write_rows
from score import evaluate


def main():
    workspace = ROOT / 'environment' / 'workspace'
    measurements = ROOT / 'solution' / 'measurements'
    results = measurements / 'results'
    oracle_path = results / 'oracle' / 'predictions.jsonl'
    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-B', str(ROOT / 'solution' / 'estimators.py'), '--workspace', str(workspace),
                    '--output', str(oracle_path)], check=True)
    truth_path = ROOT / 'tests' / 'hidden' / 'truth.jsonl'
    assert oracle_path.read_bytes() == truth_path.read_bytes()
    assert evaluate(oracle_path.parent)['score'] == 1
    empty = results / 'empty'
    empty.mkdir(parents=True, exist_ok=True)
    (empty / 'predictions.jsonl').write_text('')
    assert evaluate(empty)['score'] == 0
    # Execute the actual separate-verifier shell interface without using /logs.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'],
               VERIFIER_LOG_DIR=str(measurements / 'verifier'))
    subprocess.run(['sh', str(ROOT / 'tests' / 'test.sh'), str(oracle_path.parent)], env=env, check=True)
    assert json.loads((measurements / 'verifier' / 'reward.json').read_text())['reward'] == 1
    subprocess.run([sys.executable, '-B', str(ROOT / 'solution' / 'checks' / 'test_scorer.py')], check=True)
    # Fit each lane with transport instrumented: any read of another lane fails.
    queries = estimators.read_rows(workspace / 'queries.jsonl')
    truth = {r['record_id']: r for r in estimators.read_rows(truth_path)}
    original = estimators.read_tree
    isolation = {}
    for lane, view in zip(estimators.LANES, estimators.VIEWS):
        def restricted(ws, requested, allowed=view):
            assert requested == allowed, (requested, allowed)
            return original(ws, requested)
        estimators.read_tree = restricted
        fitted = getattr(estimators, 'fit_' + lane)(workspace)
        mismatch = sum(getattr(estimators, 'predict_' + lane)(fitted, q['fund_id'], q['period'], workspace)
                       != truth[q['record_id']][lane] for q in queries)
        assert mismatch == 0
        isolation[lane] = {'allowed_view': view, 'mismatches': mismatch}
    estimators.read_tree = original
    alternate_path = results / 'split_modules' / 'predictions.jsonl'
    alternate_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-B', str(ROOT / 'solution' / 'alternates' / 'split_modules' / 'driver.py'),
                    str(workspace), str(alternate_path)], check=True)
    assert alternate_path.read_bytes() == oracle_path.read_bytes()
    facade = ROOT / 'solution' / 'alternates' / 'class_facade' / 'oversight.py'
    spec = importlib.util.spec_from_file_location('facade', facade)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    alternate_rows = module.OversightDesk(workspace).records()
    assert alternate_rows == estimators.read_rows(oracle_path)
    write_rows(results / 'class_facade' / 'predictions.jsonl', alternate_rows)
    floors = json.loads((ROOT / 'solution' / 'floors.json').read_text())
    for relative, digest in floors['source_sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
    for p in list((ROOT / 'solution').rglob('*.py')) + list((ROOT / 'tests').rglob('*.py')):
        ast.parse(p.read_text(), filename=str(p))
    report = {'oracle_score': 1.0, 'empty_score': 0.0, 'oracle_byte_identical': True,
              'split_modules_byte_identical': True, 'class_facade_byte_identical': True,
              'source_hashes_match': True, 'isolation': isolation, 'scorer_tests': 8,
              'shell_verifier': 'passed', 'python_syntax': 'passed', 'docker_build': 'not run',
              'cross_platform': 'not measured'}
    (measurements / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
