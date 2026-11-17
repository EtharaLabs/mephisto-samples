"""Measure and freeze competent-method floors against this exact generated truth.

Every floor setter is kept; there are no hand-tuned floor constants, discarded
high baselines or payable-range caps. Source hashes bind the measurement inputs.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from cheap_portfolio import controls
from portfolio import FLOOR_METHODS
from public_reference import LANES, predictions, read_rows, write_rows

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests' / 'scoring'))
from score import raw_metrics


def main():
    workspace = ROOT / 'environment' / 'workspace'
    truth = read_rows(ROOT / 'tests' / 'hidden' / 'truth.jsonl')
    measured = {}
    for name, rows in controls(workspace):
        measured[name] = raw_metrics({r['record_id']: r for r in rows}, truth)[0]
    for name in FLOOR_METHODS:
        rows = predictions(workspace, name)
        write_rows(ROOT / 'solution' / 'measurements' / 'results' / name / 'predictions.jsonl', rows)
        measured[name] = raw_metrics({r['record_id']: r for r in rows}, truth)[0]
    # Distribution-informed constants are private safety controls, not analyst methods.
    base = predictions(workspace, 'constant')
    envelope = dict.fromkeys(LANES, 0.0)
    for lane in (LANES[0], LANES[5]):
        values = np.array([r[lane] for r in truth])
        for value in np.unique(np.round(np.quantile(values, np.linspace(0, 1, 101)), 2)):
            rows = {r['record_id']: dict(r, **{lane: float(value)}) for r in base}
            envelope[lane] = max(envelope[lane], raw_metrics(rows, truth)[0][lane])
    for rank in range(1, 281):
        rows = {r['record_id']: dict(r, oversight_rank=rank) for r in base}
        envelope[LANES[4]] = max(envelope[LANES[4]], raw_metrics(rows, truth)[0][LANES[4]])
    measured['constant_grid_envelope'] = envelope
    kinds = ('relative_agreement', 'distribution_overlap', 'f1_detection', 'macro_f1', 'rank_agreement', 'relative_agreement')
    lanes = {}
    for lane, kind in zip(LANES, kinds):
        source = max(measured, key=lambda name: measured[name][lane])
        floor = measured[source][lane]
        if floor >= 1:
            raise ValueError(f'dead lane: {lane}')
        lanes[lane] = {'weight': 1.0, 'floor': floor, 'floor_source': source, 'metric_kind': kind}
    (ROOT / 'tests' / 'scoring' / 'scorer_manifest.json').write_text(json.dumps({'lanes': lanes}, indent=2) + '\n')
    sources = [p for tree in ('solution', 'tests') for p in (ROOT / tree).rglob('*')
               if p.is_file() and 'measurements' not in p.parts and
               (p.suffix in ('.py', '.sh', '.toml') or p.name == 'Dockerfile')]
    sources += [ROOT / 'environment' / 'Dockerfile', ROOT / 'environment' / 'requirements.txt',
                ROOT / 'task.toml', ROOT / 'tests' / 'scoring' / 'scorer_manifest.json',
                ROOT / 'tests' / 'hidden' / 'truth.jsonl']
    sources += [p for p in (ROOT / 'environment' / 'workspace').rglob('*') if p.is_file()]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(sources))}
    report = {'floors': lanes, 'measurements': measured, 'source_sha256': hashes, 'excluded_methods': [],
              'public_reference_sets_floor': False, 'competent_methods': list(FLOOR_METHODS)}
    (ROOT / 'solution' / 'floors.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(lanes, indent=2))


if __name__ == '__main__':
    main()
