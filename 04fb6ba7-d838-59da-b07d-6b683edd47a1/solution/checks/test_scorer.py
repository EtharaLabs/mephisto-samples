"""Checker adequacy tests for tests/scoring/score.py: easy sentinels the scorer must pass, malformed
cases it must fail, and the manifest invariants. Run: python3 -B -m unittest solution/checks/test_scorer.py"""
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('score', ROOT / 'tests/scoring/score.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class ScorerTests(unittest.TestCase):
    def test_duplicates_dropped_entirely(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'predictions.jsonl').write_text('\n'.join(json.dumps({'record_id': x}) for x in ('a', 'b', 'a')))
            tripped = set()
            self.assertEqual(set(score.read_submission(folder, tripped)), {'b'})
            self.assertIn('duplicate_answer_rows', tripped)

    def test_malformed_rows_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'predictions.jsonl').write_text('null\n[1]\nwrong\n{"record_id":2}\n{"record_id":"x"}\n')
            self.assertEqual(set(score.read_submission(folder)), {'x'})

    def test_non_finite_tripped(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'predictions.jsonl').write_text('{"record_id":"x","loss_reserve":NaN}\n')
            tripped = set()
            self.assertEqual(score.read_submission(folder, tripped), {})
            self.assertIn('non_finite_values', tripped)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'real.jsonl').write_text('{"record_id":"x"}\n')
            Path(folder, 'predictions.jsonl').symlink_to(Path(folder, 'real.jsonl'))
            tripped = set()
            with self.assertRaises(ValueError):
                score.read_submission(folder, tripped)
            self.assertIn('submission_symlink', tripped)

    def test_relative_exact_missing_invalid_bound(self):
        self.assertEqual(score.relative_agreement([(4, 4)], 1), 1.0)
        self.assertEqual(score.relative_agreement([(None, 4)], 1), 0.0)
        self.assertLess(score.relative_agreement([(4, 4), (None, 4)], 1), 1.0)
        for value in (-1, True, float('nan'), float('inf'), '4'):
            self.assertEqual(score.relative_agreement([(value, 4)], 1), 0.0)
        self.assertAlmostEqual(score.relative_agreement([(0, 10)], 100), 0.9 / 1.1)

    def test_distribution_rules(self):
        self.assertIsNone(score._distribution_vector([0] * 7, 8))
        for vector in ([-1] + [0] * 7, [float('nan')] + [0] * 7, [1] * 8, [True] + [0] * 7):
            self.assertIsNone(score._distribution_vector(vector, 8))
        self.assertEqual(score.distribution_overlap([([0] * 8, [1] + [0] * 7)], 8), 0.0)
        self.assertEqual(score.distribution_overlap([([0] * 8, [0] * 8)], 8), 1.0)
        self.assertEqual(score.distribution_overlap([(None, [0] * 8)], 8), 0.0)

    def test_macro_not_micro(self):
        pairs = [(0, 0)] * 90 + [(0, 1)] * 10
        self.assertAlmostEqual(score.macro_f1(pairs, [0, 1]), (180 / 190) / 2)
        self.assertEqual(score.macro_f1([(2, 2)], [2]), 1.0)

    def test_positive_f1(self):
        self.assertEqual(score.f1_detection([(0, 0), (0, 1)]), 0.0)
        self.assertAlmostEqual(score.f1_detection([(1, 0), (1, 1)]), 2 / 3)

    def test_rank_metric(self):
        self.assertEqual(score.rank_agreement([(1, 1), (2, 2)]), 1.0)
        self.assertEqual(score.rank_agreement([(1, 40), (50, 2)]), 0.0)
        self.assertEqual(score.rank_agreement([(5, 15), (5, 16)]), 0.5)
        self.assertEqual(score.rank_agreement([(None, 1), (float('nan'), 2)]), 0.0)
        self.assertEqual(score._ranks([8, 8, 1]), [1.5, 1.5, 0.0])

    def test_cohorts_and_coverage(self):
        truth = {}
        for p in (16, 20):
            for n in (1, 2):
                rid = f'OB{n}:p{p}'
                truth[rid] = dict(record_id=rid, period=p, dilution_reserve=10000.0, dispute_flag=1, collection_profile=[0.1] * 8,
                                  loss_reserve=1000.0, recovery_tier=1, availability_rank=n)
        predicted = {k: dict(v) for k, v in truth.items()}
        metrics = score.lane_metrics(predicted, truth)[0]
        self.assertTrue(all(v == 1.0 for v in metrics.values()))
        predicted = {k: v for k, v in predicted.items() if v['period'] == 16}
        metrics = score.lane_metrics(predicted, truth)[0]
        self.assertEqual(metrics['dispute_flag'], 0.5)
        self.assertEqual(metrics['recovery_tier'], 0.5)
        self.assertEqual(metrics['collection_profile'], 0.5)
        self.assertEqual(metrics['availability_rank'], 0.5)

    def test_floor_rules(self):
        for floor in (1.0, float('inf'), float('nan'), -0.1):
            manifest = {'lanes': {n: {'floor': floor, 'weight': 1.0} for n in score.LANES}}
            with self.assertRaises(ValueError):
                score.lane_points({n: 1.0 for n in score.LANES}, manifest)
        manifest = {'lanes': {n: {'floor': 0.6, 'weight': 1.0} for n in score.LANES}}
        self.assertTrue(all(v == 0.0 for v in score.lane_points({n: 0.6 for n in score.LANES}, manifest).values()))

    def test_manifest(self):
        manifest = json.loads(Path(score.MANIFEST_PATH).read_text())
        self.assertEqual(tuple(manifest['lanes']), score.LANES)
        for lane in manifest['lanes'].values():
            self.assertEqual(lane['weight'], 1.0)
            self.assertTrue(math.isfinite(lane['floor']) and 0.0 <= lane['floor'] < 1.0)

    def test_empty_submission_zero_and_ctrf(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'predictions.jsonl').write_text('')
            report = score.evaluate_report(folder, ROOT / 'tests/hidden/truth.jsonl')
            self.assertEqual(report['score'], 0.0)
            ctrf = score.ctrf(report)
            self.assertEqual([t['name'] for t in ctrf['results']['tests']], list(score.CHEAT_CHECKS))


if __name__ == '__main__':
    unittest.main()
