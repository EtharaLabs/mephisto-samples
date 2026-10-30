"""Regenerate panel, deterministic targets, controls and ablations in this draft."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
from process import simulate
from public_reference import solve as public_solve
from reserving_reference import run, package
from baselines.common import solve as baseline_solve
from baselines.adapt import adapt
from rung_study import measure, print_report

scoring_spec = importlib.util.spec_from_file_location("reserving_scoring", ROOT / "tests/scoring/score.py")
if scoring_spec is None or scoring_spec.loader is None:
    raise ImportError("Cannot load trusted scorer")
scoring = importlib.util.module_from_spec(scoring_spec)
scoring_spec.loader.exec_module(scoring)


def write_json(path, value, lines=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if lines:
        text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for row in value)
    else:
        text = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def regenerate_artifacts():
    g = json.loads((ROOT / "solution/grounding.yaml").read_text())
    train, queries, _, _ = simulate(g)
    data = ROOT / "environment/attachments"
    write_json(data / "train.jsonl", train, True)
    write_json(data / "queries.jsonl", queries, True)
    truth = run(train, queries)
    write_json(ROOT / "tests/hidden_test_data/outcomes.jsonl", truth, True)
    return train, queries, truth


def regenerate():
    train, queries, truth = regenerate_artifacts()
    data = ROOT / "environment/attachments"
    submissions = {name: adapt(baseline_solve(name, data), train, queries, name)
                   for name in ("empty", "copy_forward", "chain_ladder")}
    submissions["public_reference"] = adapt(public_solve(data), train, queries)
    submissions["oracle"] = package(truth)
    reports = {}
    for name, document in submissions.items():
        write_json(ROOT / f"solution/measurements/{name}.json", document)
        reports[name] = scoring.evaluate(document, truth)
    study = measure(train, queries, submissions, scoring.evaluate, scoring.LANES)
    write_json(ROOT / "solution/measurements/rung_study.json", study)
    names = list(submissions)
    summary = {"scores": reports, "ordering": names,
               "separations": {f"{a}->{b}": reports[b]["score"] - reports[a]["score"] for a, b in zip(names, names[1:])},
               "train_rows": len(train), "query_rows": len(queries), "hidden_rows": len(truth),
               "query_history_rows": sum(len(q["history"]) for q in queries),
               "anchor_sha256": hashlib.sha256((ROOT / "tests/scoring/scorer_manifest.json").read_bytes()).hexdigest(),
               "interpretation": "Deterministic-method imitation; no outcome-noise ceiling. Author controls are not agent trajectories."}
    write_json(ROOT / "solution/measurements/summary.json", summary)
    derived = ["environment/attachments/train.jsonl", "environment/attachments/queries.jsonl", "tests/hidden_test_data/outcomes.jsonl"]
    derived += [f"solution/measurements/{name}.json" for name in names]
    derived += ["solution/measurements/summary.json"]
    derived += ["solution/measurements/rung_study.json"]
    write_json(ROOT / "solution/derived_manifest.json", {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in derived})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Also regenerate measurements and the derived manifest")
    args = parser.parse_args()
    if args.full:
        s = regenerate()
        for name in s["ordering"]:
            print(f"{name}: {s['scores'][name]['score']:.6f}/100")
        print_report(json.loads((ROOT / "solution/measurements/rung_study.json").read_text()))
    else:
        regenerate_artifacts()
