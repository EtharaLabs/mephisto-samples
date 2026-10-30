"""Scoring-version evidence; retrospective rescoring is not a new agent pilot."""
import argparse
import difflib
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "solution/measurements"
SOURCES = ("tests/scoring/score.py", "tests/scoring/scorer_manifest.json", "instruction.md")
BASELINES = {"severity": "chain_ladder", "report_timing": "chain_ladder",
             "cash_timing": "chain_ladder", "large_loss": "copy_forward"}
RESCALE = 'max(0.0, min(1.0, (metric - spec["anchor_floor"]) / (1 - spec["anchor_floor"])))'


def capture():
    path = OUT / "before_anchors.json"
    if path.exists():
        raise RuntimeError("Refusing to overwrite pre-anchor evidence")
    protected = ["solution/process.py", "solution/grounding.yaml", "solution/reserving_reference.py",
                 "solution/public_reference.py", "environment/attachments/train.jsonl", "environment/attachments/queries.jsonl",
                 "tests/hidden_test_data/outcomes.jsonl", "tests/test.sh", "tests/scoring/entrypoint.py",
                 "tests/scoring/eval_script.py"]
    protected += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "solution/baselines").glob("*.py"))]
    evidence = {"sources": {p: (ROOT / p).read_text() for p in SOURCES},
                "summary": json.loads((OUT / "summary.json").read_text()),
                "protected_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in protected}}
    path.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    print("Captured pre-anchor scorer, manifest, public instruction, metrics and protected hashes")


def source_checks():
    before = json.loads((OUT / "before_anchors.json").read_text())
    relocated = {f"environment/{name}.jsonl": f"environment/attachments/{name}.jsonl"
                 for name in ("train", "queries")}
    checks = {p: hashlib.sha256((ROOT / (relocated[p] if p in relocated else p)).read_bytes()).hexdigest() == expected
              for p, expected in before["protected_sha256"].items()}
    expected = before["sources"][SOURCES[0]].replace(
        "fraction = max(0.0, min(1.0, metric)) * coverage", f"fraction = {RESCALE} * coverage")
    expected = expected.replace("fraction = metric\n", f"fraction = {RESCALE}\n")
    checks["exact_three_branch_rescale_only"] = (ROOT / SOURCES[0]).read_text() == expected
    manifest = json.loads((ROOT / SOURCES[1]).read_text())
    old = json.loads(before["sources"][SOURCES[1]])
    for lane, original in zip(manifest["lanes"], old["lanes"]):
        name = lane["id"]
        if name in BASELINES:
            baseline = BASELINES[name]
            checks[name + "_measured_floor"] = lane["anchor_floor"] == before["summary"]["scores"][baseline]["lanes"][name]["metric"]
            checks[name + "_named_source"] = baseline in lane["anchor_source"]
            for key in ("anchor_floor", "anchor_source", "trivial_strategy"):
                lane[key] = original[key]
        checks[name + "_otherwise_unchanged"] = lane == original
    for key in ("calibration", "anchor_notes"):
        manifest.pop(key, None)
        old.pop(key, None)
    checks["manifest_other_fields_unchanged"] = manifest == old
    return checks


def measure(archive=None):
    from recompute import scoring, write_json
    from reserving_reference import read_jsonl
    before = json.loads((OUT / "before_anchors.json").read_text())
    checks = source_checks()
    assert all(checks.values()), checks
    truth = read_jsonl(ROOT / "tests/hidden_test_data/outcomes.jsonl")
    scores = {name: scoring.evaluate(json.loads((OUT / f"{name}.json").read_text()), truth)
              for name in before["summary"]["ordering"]}
    rounded = {"severity": 0.923520, "report_timing": 0.890890, "reopening": 0.788000,
               "cash_timing": 0.758190, "large_loss": 0.562780}
    opus = {}
    for name, metric in rounded.items():
        floor = scoring.LANES[name]["anchor_floor"]
        old_floor = 1 / 3 if name == "reopening" else 0
        opus[name] = {"metric": metric, "before": 20 * max(0, (metric - old_floor) / (1 - old_floor)),
                      "after": 20 * max(0, (metric - floor) / (1 - floor))}
    evidence = {"source_checks": checks, "scores": scores, "rounded_opus_metrics": opus,
                "rounded_opus_before": sum(r["before"] for r in opus.values()),
                "rounded_opus_after": sum(r["after"] for r in opus.values()),
                "textbook_baselines_approximately_zero": {
                    "definition": "Each textbook baseline earns less than 1 point of 100; not exactly zero.",
                    "scores": {n: scores[n]["score"] for n in ("copy_forward", "chain_ladder")}},
                "strict_five_point_ordering": all(a["score"] < b["score"] for a, b in zip(list(scores.values()), list(scores.values())[1:])),
                "interpretation": "New stricter competent-reference bar, selected after observing the old pilot. Retrospective only; no new pilot or duration evidence."}
    if archive is not None:
        with gzip.open(archive, "rt") as stream:
            document = json.load(stream)
        evidence["archived_agent45"] = scoring.evaluate(document, truth)
        evidence["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    write_json(OUT / "anchors.json", evidence)
    for path, original in before["sources"].items():
        diff = "".join(difflib.unified_diff(original.splitlines(True), (ROOT / path).read_text().splitlines(True),
                                          fromfile="before/" + path, tofile="after/" + path))
        (OUT / (Path(path).name + ".anchors.diff")).write_text(diff)
    print(json.dumps(evidence, sort_keys=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("capture", "measure"))
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.mode == "capture":
        capture()
    else:
        measure(args.archive)
