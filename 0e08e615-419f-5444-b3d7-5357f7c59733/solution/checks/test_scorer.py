"""Adversarial lane-local checks using synthetic submissions, not fitted methods."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/scoring'))
import score


class ScorerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.truth = {r['record_id']:r for r in score.read_jsonl(ROOT/'tests/hidden/truth.jsonl')}
        cls.manifest = json.loads((ROOT/'tests/scoring/scorer_manifest.json').read_text())

    def test_perfect_and_empty(self):
        self.assertTrue(all(v==1 for v in score.lane_metrics(self.truth,self.truth)[0].values()))
        self.assertTrue(all(v==0 for v in score.lane_metrics({},self.truth)[0].values()))

    def test_lane_local_invalidity(self):
        for lane in score.LANES:
            for bad in (None,False,'0',{},[],float('nan'),float('inf'),-1):
                pred = copy.deepcopy(self.truth)
                for row in pred.values():
                    row[lane] = bad
                metrics = score.lane_metrics(pred,self.truth)[0]
                self.assertEqual(metrics[lane],0,(lane,bad))
                self.assertTrue(all(metrics[k]==1 for k in score.LANES if k!=lane))

    def test_distribution_and_residual(self):
        for bad in ([0]*7,[0]*9,[0.2]*8,[1e308]*8,[0,0,0,0,0,0,0,-0.1]):
            self.assertIsNone(score._distribution_vector(bad))
        self.assertEqual(score.distribution_overlap([([0]*8,[0]*8)]),1)
        self.assertEqual(score.distribution_overlap([([1]+[0]*7,[0]*8)]),0)

    def test_macro_is_unweighted(self):
        pairs = [(0,0)]*90+[(0,1)]*10
        self.assertAlmostEqual(score.macro_f1(pairs,[0,1]),(180/190)/2)

    def test_rank_bounds(self):
        self.assertEqual(score.rank_agreement([(0,1)]),0)
        self.assertEqual(score.rank_agreement([(1.0,1)]),0)
        self.assertEqual(score.rank_agreement([(2,1)]),0)

    def test_duplicates_symlink_and_malformed(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'solution/measurements') as folder:
            path = Path(folder)/'predictions.jsonl'
            row = next(iter(self.truth.values()))
            path.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\nmalformed\n')
            flags = set()
            self.assertEqual(score.read_submission(folder,flags),{})
            self.assertIn('duplicate_answer_rows',flags)
            path.unlink()
            path.symlink_to(ROOT/'tests/hidden/truth.jsonl')
            with self.assertRaises(ValueError):
                score.read_submission(folder)

    def test_oversized_and_nonfinite(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'solution/measurements') as folder:
            path = Path(folder)/'predictions.jsonl'
            with path.open('wb') as stream:
                stream.truncate(score.MAX_ANSWER_BYTES+1)
            with self.assertRaises(ValueError):
                score.read_submission(folder)
            row = copy.deepcopy(next(iter(self.truth.values())))
            row['adjustment_magnitude'] = float('nan')
            path.write_text(json.dumps(row)+'\n')
            flags = set()
            parsed = score.read_submission(folder,flags)
            self.assertIsNone(parsed[row['record_id']]['adjustment_magnitude'])
            self.assertEqual(parsed[row['record_id']]['method_tier'],row['method_tier'])
            self.assertIn('non_finite_values',flags)

    def test_bad_floors(self):
        for bad in (-0.1,1.0,float('nan'),float('inf')):
            manifest = copy.deepcopy(self.manifest)
            manifest['lanes'][score.LANES[0]]['floor'] = bad
            with self.assertRaises(ValueError):
                score.lane_points(dict.fromkeys(score.LANES,1.0),manifest)


if __name__ == '__main__':
    unittest.main()
