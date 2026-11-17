"""Write the structured verifier result and both numeric reward carriers."""
import argparse
import importlib.util
import json
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission-dir', default='/workspace')
    parser.add_argument('--input', default=str(here.parent / 'hidden/truth.jsonl'))
    parser.add_argument('--log-dir', default='/logs/verifier')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('settlement_score', here / 'score.py')
    assert spec is not None and spec.loader is not None
    score = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(score)
    logs = Path(args.log_dir)
    logs.mkdir(parents=True, exist_ok=True)
    (logs / 'reward.txt').write_text('0\n')
    (logs / 'reward.json').write_text('{"reward":0}\n')
    report = score.evaluate_report(args.submission_dir, args.input)
    (logs / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    (logs / 'ctrf.json').write_text(json.dumps(score.ctrf(report))+'\n')
    (logs / 'reward.txt').write_text(str(report['score'])+'\n')
    (logs / 'reward.json').write_text(json.dumps({'reward':report['score']})+'\n')
    print('>>>>> Start Structured Result')
    print(json.dumps({'score':report['score'],'details':[dict(name=k,score=v['fraction'],weight=v['max'],status='passed' if v['fraction']>0 else 'failed') for k,v in report['lanes'].items()]}))
    print('>>>>> End Structured Result')


if __name__ == '__main__':
    main()
