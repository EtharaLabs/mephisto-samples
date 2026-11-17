"""Adversarial scorer tests: each malformed field costs only its own lane."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests' / 'scoring'))
from score import LANES, evaluate, f1, load_submission, raw_metrics, read_rows, score_rows


class ScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.truth = read_rows(ROOT / 'tests' / 'hidden' / 'truth.jsonl')
        cls.manifest = json.loads((ROOT / 'tests' / 'scoring' / 'scorer_manifest.json').read_text())

    def test_oracle_and_empty(self):
        self.assertEqual(score_rows(self.truth, self.truth, self.manifest)['score'], 1.0)
        self.assertEqual(score_rows({}, self.truth, self.manifest)['score'], 0.0)

    def test_independent_lanes(self):
        for lane in LANES:
            rows = [{k: v for k, v in r.items() if k != lane} for r in self.truth]
            report = score_rows(rows, self.truth, self.manifest)
            self.assertEqual(report['score'], .8333)
            self.assertEqual(report['lanes'][lane]['fraction'], 0)
            for other in LANES:
                if other != lane:
                    self.assertEqual(report['lanes'][other]['fraction'], 1)

    def test_vectors_and_nonfinite(self):
        for invalid in ([.2]*8, [-.1]*8, [0.0]*7, [float('nan')]*8, [float('inf')]*8):
            rows = [dict(r, fee_accrual_profile=invalid) for r in self.truth]
            self.assertEqual(score_rows(rows, self.truth, self.manifest)['score'], .8333)
        for invalid in (True, -1, float('nan'), float('inf'), 10**500, 2.001):
            rows = [dict(r, nav_break_magnitude=invalid) for r in self.truth]
            self.assertEqual(score_rows(rows, self.truth, self.manifest)['score'], .8333)

    def test_types_and_bounds(self):
        for lane, bad in [('restatement_flag', 1.0), ('pricing_source_tier', 4), ('oversight_rank', 281)]:
            rows = [dict(r, **{lane: bad}) for r in self.truth]
            self.assertEqual(score_rows(rows, self.truth, self.manifest)['score'], .8333)

    def test_duplicates_and_sparse(self):
        self.assertEqual(score_rows(self.truth + self.truth, self.truth, self.manifest)['score'], 0)
        report = score_rows(self.truth[:1], self.truth, self.manifest)
        self.assertEqual(report['score'], 0)

    def test_macro_not_weighted(self):
        truth = [dict(r, pricing_source_tier=int(i < 500)) for i, r in enumerate(self.truth)]
        rows = {r['record_id']: dict(r, pricing_source_tier=1) for r in truth}
        raw = raw_metrics(rows, truth)[0]['pricing_source_tier']
        self.assertAlmostEqual(raw, (2*500/(2*500+60))/2)

    def test_rank_cohorts_and_boundary(self):
        rows: dict[str, dict[str, Any]] = {r['record_id']: dict(r, oversight_rank=min(280, r['oversight_rank']+10)) for r in self.truth}
        self.assertEqual(raw_metrics(rows, self.truth)[0]['oversight_rank'], 1)
        for r in rows.values():
            if r['record_id'].endswith(':p20'):
                r['oversight_rank'] = None
        self.assertEqual(raw_metrics(rows, self.truth)[0]['oversight_rank'], .5)

    def test_file_safety(self):
        # Explicit dir keeps all test writes inside the allowed authoring root.
        with tempfile.TemporaryDirectory(dir=ROOT / 'solution' / 'measurements') as directory:
            path = Path(directory) / 'predictions.jsonl'
            path.symlink_to(ROOT / 'tests' / 'hidden' / 'truth.jsonl')
            self.assertEqual(load_submission(path)[0], {})
            path.unlink()
            path.write_text('{not json}\n')
            self.assertEqual(evaluate(directory)['score'], 0)
            path.write_text(json.dumps(self.truth[0]) + '\n' + json.dumps(self.truth[0]) + '\n')
            self.assertEqual(load_submission(path)[0], {})
            path.write_text('{"record_id":"FD0080:p16","nav_break_magnitude":NaN}\n')
            self.assertIsNone(load_submission(path)[0]['FD0080:p16']['nav_break_magnitude'])
            with path.open('wb') as stream:
                stream.truncate(20_000_001)
            self.assertEqual(load_submission(path)[0], {})


if __name__ == '__main__':
    unittest.main()
