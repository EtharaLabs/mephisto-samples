"""Contract tests for the lane scorer.

These are author-side guards on the scoring manifest, not part of grading. The task
harness never executes this file: tests/test.sh names tests/scoring/entrypoint.py
explicitly and does not collect tests/. Run locally with pytest.
"""

import json
from pathlib import Path

SCORING = Path(__file__).parent / "scoring"
MANIFEST = json.loads((SCORING / "scorer_manifest.json").read_text())
LANES = MANIFEST["lanes"]

# The four branches implemented in score.py:lane_score.
IMPLEMENTED_METRICS = {
    "relative_agreement",
    "distribution_overlap",
    "f1_detection",
    "spearman_ic",
}

EXPECTED_LANES = {
    "severity",
    "report_timing",
    "reopening",
    "cash_timing",
    "large_loss",
}


def rescale(metric, floor):
    return max(0.0, min(1.0, (metric - floor) / (1 - floor)))


def test_lane_weights_sum_to_the_declared_total():
    assert sum(lane["weight"] for lane in LANES) == MANIFEST["lane_total"]
    assert MANIFEST["lane_total"] == MANIFEST["grand_max"] == 100


def test_lane_ids_are_unique_and_complete():
    ids = [lane["id"] for lane in LANES]
    assert len(ids) == len(set(ids)), f"duplicate lane id in {ids}"
    assert set(ids) == EXPECTED_LANES


def test_every_lane_metric_has_a_scorer_branch():
    for lane in LANES:
        assert lane["metric"] in IMPLEMENTED_METRICS, lane["id"]


def test_anchor_floors_are_well_posed():
    for lane in LANES:
        floor = lane["anchor_floor"]
        assert 0.0 <= floor < 1.0, (
            f"{lane['id']} floor {floor}: 1.0 divides by zero, above 1.0 inverts the scale"
        )
        assert lane["anchor_full"] == 1, lane["id"]


def test_rescale_maps_the_control_to_zero_and_the_reference_to_full():
    for lane in LANES:
        floor = lane["anchor_floor"]
        assert rescale(floor, floor) == 0.0, f"{lane['id']}: matching the control must earn zero"
        assert rescale(1.0, floor) == 1.0, f"{lane['id']}: the reference must earn full credit"
        assert rescale(floor * 0.5, floor) == 0.0, (
            f"{lane['id']}: falling below the control must clamp to zero, never go negative"
        )
        assert 0.0 < rescale((floor + 1.0) / 2.0, floor) < 1.0, (
            f"{lane['id']}: between control and reference must earn partial credit"
        )


def test_declared_scoring_files_are_present():
    for relative in MANIFEST["required_scoring_files"]:
        assert (SCORING / relative).resolve().is_file(), relative


def test_score_scale_is_internally_consistent():
    normalization = MANIFEST["score_normalization"]
    assert normalization["raw_max"] == MANIFEST["grand_max"]
    assert MANIFEST["score_output"]["scale_max"] == MANIFEST["grand_max"]
    assert MANIFEST["scoring_direction"] == "higher-better"
