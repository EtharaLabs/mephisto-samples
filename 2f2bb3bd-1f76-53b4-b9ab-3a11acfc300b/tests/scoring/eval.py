"""Score static predictions and publish report, CTRF and numeric reward carriers.

Nothing runs at import time. Source loading uses an absolute trusted path, not the
submission directory or PYTHONPATH. The shell seeds zero rewards before invoking us.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission-dir', default='/workspace')
    parser.add_argument('--input', default=str(HERE.parent / 'hidden/truth.jsonl'))
    parser.add_argument('--log-dir', default='/logs/verifier')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('desk_score', HERE / 'score.py')
    assert spec is not None and spec.loader is not None
    score = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(score)
    report = score.evaluate_report(args.submission_dir, args.input)
    logs = Path(args.log_dir)
    logs.mkdir(parents=True, exist_ok=True)
    payloads = {'report.json': json.dumps(report, sort_keys=True, allow_nan=False),
                'ctrf.json': json.dumps(score.ctrf(report), sort_keys=True, allow_nan=False),
                'reward.txt': str(report['score']), 'reward.json': json.dumps({'reward': report['score']})}
    for name, text in payloads.items():
        temporary = logs / ('.' + name + '.tmp')
        temporary.write_text(text + '\n', encoding='utf-8')
        os.replace(temporary, logs / name)
    print('>>>>> Start Structured Result')
    print(json.dumps({'score': report['score'], 'details': [dict(name=n, score=r['fraction'], weight=r['max'],
                      status='passed' if r['fraction'] > 0 else 'failed') for n, r in report['lanes'].items()]}))
    print('>>>>> End Structured Result')
    print(f"TOTAL_SCORE {report['score']:.4f}")


if __name__ == '__main__':
    main()
