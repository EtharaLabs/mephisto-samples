"""Measure frozen competent floors and a public-only estimator ladder.

Prediction workers only receive the workspace; private truth is used for evaluation
after candidate artifacts have been produced. No fitted candidate reads truth.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/scoring'))
import score
from portfolio import METHODS, FLOOR_METHODS, LANES


def main():
    assert tuple(score.LANES) == LANES and METHODS[0] == 'naive_constant'
    results = ROOT/'solution/measurements/results'
    truth_path = ROOT/'tests/hidden/truth.jsonl'
    truth = {r['record_id']:r for r in score.read_jsonl(truth_path)}
    raw = {}
    for method in METHODS:
        path = results/method/'predictions.jsonl'
        path.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run([sys.executable,'-B',str(ROOT/'solution/portfolio.py'),'--workspace',str(ROOT/'environment/workspace'),
                        '--output',str(path),'--method',method],check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1'))
        raw[method] = score.lane_metrics(score.read_submission(path.parent),truth)[0]
        print(method,raw[method],flush=True)
    kinds = ('relative_agreement','distribution_overlap','f1_detection','macro_f1','rank_agreement','relative_agreement')
    manifest = {'lanes':{}}
    # Exhaust every class-constant; these protect macro F1 and positive F1 from degeneracy.
    for flag in (0,1):
        for tier in range(4):
            name = f'constant_flag{flag}_tier{tier}'
            baseline = score.read_submission(results/'naive_constant')
            for row in baseline.values():
                row.update(challenge_flag=flag,method_tier=tier,review_rank=11)
            raw[name] = score.lane_metrics(baseline,truth)[0]
    eligible = list(FLOOR_METHODS)+[n for n in raw if n.startswith('constant_')]
    for lane,kind in zip(score.LANES,kinds):
        winner = max(eligible,key=lambda m:raw[m][lane])
        floor = raw[winner][lane]
        assert 0 <= floor < 1,(lane,floor)
        manifest['lanes'][lane] = dict(weight=1.0,metric_kind=kind,floor=floor,floor_source=winner)
    manifest_path = ROOT/'tests/scoring/scorer_manifest.json'
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    reports = {m:score.evaluate_report(results/m,truth_path) for m in METHODS}
    for m in FLOOR_METHODS:
        assert reports[m]['score']==0,(m,reports[m])
    files = [truth_path,manifest_path,ROOT/'solution/estimators.py',ROOT/'solution/generate.py',
             ROOT/'solution/portfolio.py',Path(__file__),ROOT/'tests/scoring/score.py']
    record = dict(floors=manifest['lanes'],floor_methods=eligible,raw_metrics=raw,methods=reports,
                  sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (ROOT/'solution/floors.json').write_text(json.dumps(record,indent=2)+'\n')
    (ROOT/'solution/measurements/ladder.json').write_text(json.dumps(reports,indent=2)+'\n')
    print('LADDER',[(m,r['score']) for m,r in reports.items()],flush=True)


if __name__ == '__main__':
    main()
