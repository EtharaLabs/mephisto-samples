"""Verifier step one: score the lanes, write report.json, ctrf.json and reward.txt, and print the
single structured result block the sforge judge parses. Reward Kit (step two) reads report.json
and writes Harbor's reward.json. Nothing here runs at import time.
"""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission-dir', default='/workspace')
    parser.add_argument('--input', default=str(HERE.parent / 'hidden' / 'truth.jsonl'))
    parser.add_argument('--log-dir', default='/logs/verifier')
    args = parser.parse_args()
    score = _load(HERE / 'score.py', 'receivables_score')
    report = score.evaluate_report(args.submission_dir, args.input)
    text = json.dumps(report, sort_keys=True, allow_nan=False)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / 'report.json').write_text(text + '\n', encoding='utf-8')
    (log_dir / 'ctrf.json').write_text(json.dumps(score.ctrf(report), sort_keys=True) + '\n', encoding='utf-8')
    (log_dir / 'reward.txt').write_text(f"{report['score']}\n", encoding='utf-8')
    block = {'score': report['score'],
             'details': [{'name': lane_id, 'status': 'passed' if lane['fraction'] > 0 else 'failed',
                          'score': lane['fraction'], 'weight': lane['max']} for lane_id, lane in sorted(report['lanes'].items())]}
    print('>>>>> Start Structured Result')
    print(json.dumps(block, sort_keys=True, allow_nan=False))
    print('>>>>> End Structured Result')
    print(f"TOTAL_SCORE {report['score']:.4f}")


if __name__ == '__main__':
    main()
