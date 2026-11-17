"""Separate verifier entry point; publish machine-readable score and lane reports."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission-dir', required=True)
    parser.add_argument('--log-dir', required=True)
    args = parser.parse_args()
    logs = Path(args.log_dir)
    logs.mkdir(parents=True, exist_ok=True)
    report = evaluate(args.submission_dir)
    # Never expose raw metrics alongside fractions: that pair reveals the floor.
    for lane in report['lanes'].values():
        lane.pop('metric', None)
    (logs / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (logs / 'reward.txt').write_text(str(report['score']) + '\n')
    (logs / 'reward.json').write_text(json.dumps({'reward': report['score']}) + '\n')
    tests = [{'name': k, 'status': 'passed' if v['fraction'] > 0 else 'failed', 'duration': 0}
             for k, v in report['lanes'].items()]
    passed = sum(t['status'] == 'passed' for t in tests)
    ctrf = {'results': {'tool': {'name': 'nav-oversight'}, 'summary': {'tests': 6, 'passed': passed, 'failed': 6-passed,
                         'pending': 0, 'skipped': 0, 'other': 0, 'start': 0, 'stop': 0}, 'tests': tests}}
    (logs / 'ctrf.json').write_text(json.dumps(ctrf) + '\n')
    # Emit only the sforge structured-result contract: per-lane status and earned
    # fraction. Never the floor or the raw metric, which together reveal the floor.
    block = {'score': report['score'],
             'details': [{'name': k, 'status': 'passed' if v['fraction'] > 0 else 'failed',
                          'score': v['fraction'], 'weight': v.get('max', 1.0)}
                         for k, v in sorted(report['lanes'].items())]}
    print('>>>>> Start Structured Result')
    print(json.dumps(block, sort_keys=True, allow_nan=False))
    print('>>>>> End Structured Result')
    print(f"TOTAL_SCORE {report['score']:.4f}")


if __name__ == '__main__':
    main()
