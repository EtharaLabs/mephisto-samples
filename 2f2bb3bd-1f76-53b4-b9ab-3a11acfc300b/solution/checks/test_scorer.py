"""Checker adequacy: invalid values remain lane-local and every query remains graded.

Run with ``python3 -B -m unittest discover -s solution/checks`` from the bundle root.
Temporary submission directories are created inside solution/measurements only.
"""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('desk_score', ROOT / 'tests/scoring/score.py')
assert spec is not None and spec.loader is not None
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / 'solution/measurements')
        self.folder = Path(self.temporary.name)
        self.truth = score.read_jsonl(ROOT / 'tests/hidden/truth.jsonl')

    def tearDown(self):
        self.temporary.cleanup()

    def submit(self, rows):
        (self.folder / 'predictions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        return score.evaluate_report(self.folder, ROOT / 'tests/hidden/truth.jsonl')

    def test_exact_oracle(self):
        report = self.submit(self.truth)
        self.assertEqual(report['score'], 1.0)
        self.assertTrue(all(v['fraction'] == 1 for v in report['lanes'].values()))

    def test_missing_file(self):
        self.assertEqual(score.evaluate(self.folder, ROOT / 'tests/hidden/truth.jsonl'), 0.0)

    def test_empty_file(self):
        self.assertEqual(self.submit([])['score'], 0.0)

    def test_duplicates_dropped_entirely(self):
        self.submit(self.truth + self.truth)
        tripped = set()
        self.assertEqual(score.read_submission(self.folder, tripped), {})
        self.assertIn('duplicate_answer_rows', tripped)

    def test_unknown_ids(self):
        self.assertEqual(self.submit([dict(r, record_id='unknown-' + r['record_id']) for r in self.truth])['score'], 0)

    def test_symlink(self):
        target = self.folder / 'actual.jsonl'
        target.write_text('{}\n')
        (self.folder / 'predictions.jsonl').symlink_to(target)
        report = score.evaluate_report(self.folder, ROOT / 'tests/hidden/truth.jsonl')
        self.assertEqual(report['score'], 0)
        self.assertTrue(report['cheat_checks']['submission_symlink'])

    def test_oversized_file(self):
        with (self.folder / 'predictions.jsonl').open('wb') as stream:
            stream.truncate(score.MAX_ANSWER_BYTES + 1)
        self.assertTrue(score.evaluate_report(self.folder, ROOT / 'tests/hidden/truth.jsonl')['cheat_checks']['oversized_answer_file'])

    def test_malformed_lines(self):
        (self.folder / 'predictions.jsonl').write_text('null\n[]\nwrong\n{"record_id":3}\n')
        self.assertEqual(score.evaluate(self.folder, ROOT / 'tests/hidden/truth.jsonl'), 0)

    def test_partial_lane_credit(self):
        rows = [{k: v for k, v in r.items() if k in ('record_id', *score.LANES[:3])} for r in self.truth]
        self.assertEqual(self.submit(rows)['score'], 0.5)

    def test_every_bad_lane_is_local(self):
        for lane in score.LANES:
            for invalid in (None, True, 'invalid', {}, -1, float('inf')):
                with self.subTest(lane=lane, invalid=invalid):
                    report = self.submit([dict(r, **{lane: invalid}) for r in self.truth])
                    self.assertEqual(report['score'], 0.8333)
                    self.assertEqual(report['lanes'][lane]['fraction'], 0)
                    self.assertTrue(all(v['fraction'] == 1 for k, v in report['lanes'].items() if k != lane))

    def test_nonfinite_lane_local(self):
        report = self.submit([dict(r, charge_reserve=float('nan')) for r in self.truth])
        self.assertTrue(report['cheat_checks']['non_finite_values'])
        self.assertEqual(report['score'], 0.8333)

    def test_profile_residual(self):
        self.assertEqual(score.distribution_overlap([([0] * 8, [0] * 8)]), 1)
        self.assertEqual(score.distribution_overlap([([0] * 8, [1] + [0] * 7)]), 0)
        for vector in ([0] * 7, [1] * 8, [-1] + [0] * 7, [True] + [0] * 7, [float('inf')] * 8):
            self.assertIsNone(score._distribution_vector(vector))

    def test_integer_types(self):
        for lane in ('refusal_flag', 'tenor_tier', 'examiner_priority_rank'):
            report = self.submit([dict(r, **{lane: float(r[lane])}) for r in self.truth])
            self.assertEqual(report['lanes'][lane]['fraction'], 0)

    def test_magnitude_precision(self):
        self.assertEqual(score.relative_agreement([(1.111, 1.11)], 0.5), 0)
        self.assertEqual(score.relative_agreement([(1.11, 1.11)], 0.5), 1)

    def test_magnitude_variance_penalty(self):
        spread = score.relative_agreement([(10, 10), (0, 10)], 0.5)
        even = score.relative_agreement([(5, 10), (5, 10)], 0.5)
        self.assertLess(spread, even)

    def test_macro_not_weighted(self):
        pairs = [(0, 0)] * 90 + [(0, 1)] * 10
        self.assertAlmostEqual(score.macro_f1(pairs, [0, 1]), (180 / 190) / 2)

    def test_positive_class_only(self):
        self.assertEqual(score.f1_detection([(0, 0), (0, 1)]), 0)
        self.assertAlmostEqual(score.f1_detection([(1, 0), (1, 1)]), 2 / 3)

    def test_rank_tolerance_and_range(self):
        pairs = [(1, 11)] * 20
        self.assertEqual(score.rank_agreement(pairs), 1)
        self.assertEqual(score.rank_agreement([(1, 12)] * 20), 0)
        for invalid in (0, -1, 21, 1.0, True, None):
            self.assertEqual(score.rank_agreement([(invalid, 1)] * 20), 0)

    def test_cohort_average_not_pooled(self):
        truth = {f'BE{i}:p{p}': dict(self.truth[0], record_id=f'BE{i}:p{p}', examiner_priority_rank=i + 1)
                 for p, count in ((16, 30), (20, 50)) for i in range(count)}
        predictions = {k: r for k, r in truth.items() if k.endswith('p16')}
        self.assertEqual(score.lane_metrics(predictions, truth)[0]['examiner_priority_rank'], 0.5)

    def test_missing_values_preserve_population(self):
        truth = {r['record_id']: r for r in self.truth}
        half = {k: r for k, r in truth.items() if k.endswith(':p16')}
        metrics, coverage, expected, present = score.lane_metrics(half, truth)
        self.assertEqual((coverage, expected, present), (0.5, 560, 280))
        for lane in ('discrepancy_class_profile', 'examiner_priority_rank'):
            self.assertEqual(metrics[lane], 0.5)
        for lane in ('refusal_flag', 'tenor_tier'):
            self.assertGreaterEqual(metrics[lane], 0)
            self.assertLess(metrics[lane], 1)

    def test_selective_invalidity_cannot_improve_classification(self):
        truth = {r['record_id']: r for r in self.truth}
        for lane, labels in (('refusal_flag', range(2)), ('tenor_tier', range(4))):
            for actual in labels:
                chosen = next(k for k, r in truth.items() if r[lane] == actual)
                invalid = {k: dict(r) for k, r in truth.items()}
                invalid[chosen][lane] = None
                bad_metric = score.lane_metrics(invalid, truth)[0][lane]
                for predicted in labels:
                    valid = {k: dict(r) for k, r in truth.items()}
                    valid[chosen][lane] = predicted
                    self.assertLessEqual(bad_metric, score.lane_metrics(valid, truth)[0][lane])

    def test_invalid_floor(self):
        manifest = json.loads(score.MANIFEST_PATH.read_text())
        for invalid in (float('nan'), float('inf'), 1, -0.1, True):
            bad = copy.deepcopy(manifest)
            bad['lanes']['tenor_tier']['floor'] = invalid
            with self.assertRaises(ValueError):
                score.lane_points({lane: 1 for lane in score.LANES}, bad)

    def test_manifest_weights(self):
        manifest = json.loads(score.MANIFEST_PATH.read_text())
        self.assertEqual(tuple(manifest['lanes']), score.LANES)
        self.assertTrue(all(r['weight'] == 1 for r in manifest['lanes'].values()))


if __name__ == '__main__':
    unittest.main()
