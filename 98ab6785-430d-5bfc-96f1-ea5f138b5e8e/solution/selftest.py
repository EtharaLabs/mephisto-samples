"""Local verification only; no Trinity, container, network or harness invocation."""
import ast
import contextlib
import copy
import hashlib
import io
import importlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from unittest.mock import patch

from recompute import ROOT, regenerate, scoring
from reserving_reference import read_jsonl, solve as oracle_solve
from rung_study import assert_design, print_report
from hardening_study import measure as measure_hardening, panel_digest, digest, protected_source_checks
from anchor_study import source_checks


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    print("PASS " + label)


def snapshot():
    paths = json.loads((ROOT / "solution/derived_manifest.json").read_text())
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in [*paths, "solution/derived_manifest.json"]}


def main():
    # Validation-only dependency, possibly supplied via a scratch PYTHONPATH.
    yaml = importlib.import_module("yaml")
    check(sys.dont_write_bytecode, "bytecode writes disabled")
    check(yaml.__version__ == "6.0.3", "PyYAML 6.0.3")
    print("PYTHON " + sys.version.split()[0])
    for path in ROOT.rglob("*.yaml"):
        yaml.safe_load(path.read_text())
    for path in ROOT.rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    for path in ROOT.rglob("*.sh"):
        subprocess.run(["sh", "-n", str(path)], check=True)
    check(True, "YAML parsing, Python AST parsing, shell sh -n")
    anchors = (ROOT / "tests/scoring/scorer_manifest.json").read_bytes()
    before = json.loads((ROOT / "solution/measurements/before_hardening.json").read_text())
    check(all(protected_source_checks(before).values()),
          "historical hardening hashes and exact declared baseline-anchor scoring delta verified")
    check(all(source_checks().values()), "generator, config, all targets, public data, solvers and transport byte-unchanged since anchor capture")
    mismatched = copy.deepcopy(before)
    protected = "solution/reserving_reference.py"
    mismatched["protected_source_sha256"][protected] = "0" * 64
    guarded = protected_source_checks(mismatched)
    check(not guarded[protected] and guarded["anchor:" + protected] and not all(guarded.values()),
          "passing anchor hash cannot overwrite a failed historical source guard")
    regenerate()
    first = snapshot()
    summary = regenerate()
    check(first == snapshot(), "byte-idempotent consecutive regeneration of every derived artifact")
    check(all(source_checks().values()), "regeneration preserves all pre-anchor protected bytes, including cash targets")
    check(anchors == (ROOT / "tests/scoring/scorer_manifest.json").read_bytes(), "scoring anchors unchanged by regeneration")
    check(len(scoring.LANES) == 5 and sum(v["weight"] for v in scoring.LANES.values()) == 100
          and max(v["weight"] for v in scoring.LANES.values()) == 20,
          "five explicit lane weights sum to exactly 100; largest lane 20; no padding")
    check(all(v["anchor_floor"] < v["anchor_full"] and v["component"] and v["trivial_strategy"]
              for v in scoring.LANES.values()), "every lane declares floor, full anchor, trivial strategy and component")
    train = read_jsonl(ROOT / "environment/attachments/train.jsonl")
    queries = read_jsonl(ROOT / "environment/attachments/queries.jsonl")
    truth = read_jsonl(ROOT / "tests/hidden_test_data/outcomes.jsonl")
    check(panel_digest(train, queries) == before["unmodified_panel_fields_sha256"],
          "reports, primary losses, exposure, indices and reopening events/payments unchanged in every public row")
    check(digest([{k: v for k, v in t.items() if k != "cash_pattern"} for t in truth]) == before["noncash_targets_sha256"],
          "all four noncash targets unchanged, including every reopening label")
    check(len(train) == 25000 and len(queries) == len(truth) == 5000
          and sum(len(q["history"]) for q in queries) == 20000,
          "25000 training rows; 5000 queries; 20000 observed history rows; 5000 deterministic targets")
    check({r["record_id"] for r in train}.isdisjoint(r["record_id"] for r in truth), "train/query keys disjoint")
    check(max(r["calendar_period"] for r in train) < min(q["history"][0]["accident_period"] for q in queries),
          "all training realizations precede query accident periods")
    allowed = {"record_id", "lob", "cohort", "accident_period", "development_lag", "calendar_period", "exposure",
               "risk_index", "inflation_index", "primary_paid", "settlement_paid", "reopening_paid", "paid",
               "case_reserve", "incurred", "reported_count", "new_reported_count", "reopened_count"}
    check(all(set(r) == allowed for r in train) and all(set(q) == {"record_id", "history"}
          and all(set(r) == allowed for r in q["history"]) for q in queries), "public corpus observable-field allowlist")
    public_paths = [ROOT / "instruction.md", *sorted((ROOT / "environment").rglob("*"))]
    check(all(not p.is_symlink() for p in public_paths), "no public symlinks into private trees")
    check({p.name for p in (ROOT / "environment").iterdir()} == {"Dockerfile", "attachments"},
          "work environment contains only build recipe and attachments")
    check({p.name for p in (ROOT / "environment/attachments").iterdir()} == {"train.jsonl", "queries.jsonl"},
          "work data payload contains only two observable datasets")
    public_text = "\n".join(p.read_text() for p in public_paths if p.is_file())
    check(not any(k in public_text for k in ("future_primary", "future_settlement", "future_reopening",
                                            "priority_raw", "tail_raw", "reopen_raw")),
          "no private intermediate or simulated future fields in public payload")
    check(all(json.dumps(r, sort_keys=True, separators=(",", ":")) not in public_text for r in truth),
          "no complete private target record in public payload")
    g = json.loads((ROOT / "solution/grounding.yaml").read_text())
    check(not any('"' + k + '"' in public_text for k in g), "no serialized generator configuration keys in public payload")
    snippets = [line.strip() for path in (ROOT / "solution/reserving_reference.py", ROOT / "solution/process.py")
                for line in path.read_text().splitlines() if len(line.strip()) > 65 and not line.lstrip().startswith(('"', '#'))]
    check(not any(line in public_text for line in snippets), "no private method/generator source fragments in public payload")
    access = []
    original = Path.read_text

    def record_read(path, *args, **kwargs):
        access.append(path.resolve())
        return original(path, *args, **kwargs)

    with patch.object(Path, "read_text", record_read):
        oracle = oracle_solve(ROOT / "environment/attachments")
    check(set(access) == {ROOT / "environment/attachments/train.jsonl", ROOT / "environment/attachments/queries.jsonl"},
          "oracle reads only observable train and queries, never targets or generator parameters")
    check(oracle["predictions"] == truth, "oracle independently reproduces every deterministic target")
    check(scoring.evaluate(oracle, truth)["score"] == 100.0, "ORACLE SCORES EXACTLY 100")
    check(scoring.evaluate({}, truth)["score"] == 0, "empty scores exactly zero")
    full = scoring.evaluate(oracle, truth)
    broken = copy.deepcopy(oracle)
    broken["self_reported_metrics"] = {}
    check(scoring.evaluate(broken, truth) == full, "inert self-report award removed; summaries cannot veto predictions")
    for lane, field in scoring.FIELDS.items():
        broken = copy.deepcopy(oracle)
        for r in broken["predictions"]:
            r[field] = None
        report = scoring.evaluate(broken, truth)
        assert report["lanes"][lane]["points"] == 0
        assert report["score"] == 80.0
        for other in scoring.FIELDS:
            if other != lane:
                assert report["lanes"][other] == full["lanes"][other]
    check(True, "each missing field loses exactly its own 20 points; other four lanes identical")
    broken = copy.deepcopy(oracle)
    broken["predictions"] *= 2
    check(scoring.evaluate(broken, truth)["score"] == 0, "duplicate-key invalidation prevents duplicate gaming")
    for value in (None, True, [], "bad", float("nan"), float("inf"), float("-inf"), -1, 1e101, 10 ** 1000):
        sample = {"predictions": [{"record_id": truth[0]["record_id"], "ultimate_severity": value}]}
        report = scoring.evaluate(sample, truth[:1])
        assert report["lanes"]["severity"]["points"] == 0
        json.dumps(report, allow_nan=False)
    for field in ("cash_pattern", "reporting_pattern"):
        for value in (None, [], [0] * 9, [0] * 11, [True] * 10, [-0.1] * 10,
                      [float("nan")] * 10, [float("inf")] * 10, [float("-inf")] * 10, [1e100] * 10, [0.2] * 10, [0] * 10):
            sample = {"predictions": [{"record_id": truth[0]["record_id"], field: value}]}
            report = scoring.evaluate(sample, truth[:1])
            assert report["score"] == 0
            json.dumps(report, allow_nan=False)
    for top in (None, [], 0, True, {"predictions": {}}, {"predictions": [None, 1, []]}):
        assert scoring.evaluate(top, truth[:1])["score"] == 0
    check(True, "adversarial scalar/structure cases fail closed with finite reports")
    periods = sorted({t["accident_period"] for t in truth})
    check(all(sum(t["reopening_flag"] for t in truth if t["accident_period"] == period) == 20 for period in periods),
          "reopening prevalence exactly 20 percent in every period")
    study = json.loads((ROOT / "solution/measurements/rung_study.json").read_text())
    check(len(study["components"]) == 5 and all(len(s["factorial_scores"]) == 32
          and len(s["all_120_repair_orders"]) == 120 for s in study["controls"].values()),
          "five problems; full factorial measured from naive and competent controls")
    check(all(abs(sum(path["gains"]) - (100 - s["naive_score"])) < 1e-10
              for s in study["controls"].values() for path in s["all_120_repair_orders"]),
          "all 240 diagnostic repair paths telescope to oracle; not agent trajectories")
    rejected = copy.deepcopy(study)
    rejected["checks"]["cross_problem_gains_equal"] = False
    try:
        assert_design(rejected)
    except AssertionError:
        pass
    else:
        raise AssertionError("design failure was ignored")
    check(True, "design assertion rejects failed independence; nonzero selftest exit retained")
    check(all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
              for path, digest in study["protected_source_sha256"].items()),
          "study records exact baseline, adapter, scorer and anchor source digests")
    spec = tomllib.loads((ROOT / "task.toml").read_text())
    check("python3 -I -B /tests/scoring/entrypoint.py" in (ROOT / "tests/test.sh").read_text(),
          "tests/test.sh invokes isolated evaluator with default /logs/verifier reward.txt and reward.json outputs")
    check(spec["agent"]["timeout_sec"] == 43200.0 and spec["verifier"]["timeout_sec"] == 3600.0
          and spec["verifier"]["environment_mode"] == "separate" and "steps" not in spec
          and "multi_step_reward_strategy" not in spec, "single-turn timeouts and separate verifier")
    check(spec["environment"]["network_mode"] == spec["verifier"]["environment"]["network_mode"] == "no-network",
          "both environments no-network")
    extension = spec["extensions"]["sforge"]
    check(extension["base_image"] == "python" and extension["submit_paths"] == ["reserving.py", "requirements.txt", "reserving_results.json"]
          and all('/' not in extension[k] and ':' not in extension[k] for k in ("work_image_tag", "judge_image_tag")),
          "three submit paths, Python base and tag-only placeholders")
    check("difficulty" not in spec["metadata"] and len(spec["task"]["authors"]) == 1
          and spec["task"]["authors"][0]["email"].endswith("@ethara.ai"), "author and metadata constraints")
    provenance = spec["upstream_provenance"]
    import datetime
    datetime.date.fromisoformat(provenance["provenance_date"])
    check(provenance["origin"] == "original" and provenance["source_kind"] == "synthetic"
          and provenance["source"]["generator"] and provenance["source"]["generation_inputs"], "synthetic original provenance with date-only date")
    with tempfile.TemporaryDirectory(prefix="selftest-", dir=ROOT / "solution") as tmp:
        scratch = Path(tmp)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        subprocess.run(["sh", str(ROOT / "solution/solve.sh"), str(scratch), str(ROOT / "environment/attachments")], env=env, check=True)
        artifacts = ("reserving.py", "requirements.txt", "reserving_results.json")
        check(all((scratch / name).is_file() and not (scratch / name).is_symlink() for name in artifacts)
              and (scratch / "requirements.txt").read_text() == ""
              and (scratch / "reserving.py").read_bytes() == (ROOT / "solution/reserving_reference.py").read_bytes()
              and json.loads((scratch / "reserving_results.json").read_text()) == oracle,
              "solution/solve.sh emits exact oracle and all three artifacts")
        for name, wrapper in {"empty": "empty", "copy_forward": "copy_forward", "chain_ladder": "chain_ladder", "public_reference": "public_data"}.items():
            output = scratch / (name + ".json")
            subprocess.run([sys.executable, "-B", str(ROOT / f"solution/baselines/{wrapper}.py"), "--data-dir", str(ROOT / "environment/attachments"),
                            "--output", str(output)], env=env, check=True, capture_output=True)
            assert json.loads(output.read_text()) == json.loads((ROOT / f"solution/measurements/{name}.json").read_text())
        check(True, "all four non-oracle standalone controls reproduce measured submissions")
        (scratch / "reserving.py").write_text("raise RuntimeError('must never execute')\n")
        command = [sys.executable, "-I", "-B", str(ROOT / "tests/scoring/entrypoint.py"), "--submission-dir", str(scratch),
                   "--input", str(ROOT / "tests/hidden_test_data/outcomes.jsonl"), "--log-dir", str(scratch / "logs")]
        result = subprocess.run(command, env=env, check=True, text=True, capture_output=True)
        report = json.loads((scratch / "logs/reward.json").read_text())
        check(float((scratch / "logs/reward.txt").read_text()) == report["score"] == 100.0
              and ">>>>> Start Structured Result" in result.stdout and ">>>>> End Structured Result" in result.stdout,
              "isolated judge CLI scores solve.sh at 100, writes bare reward and structured markers; never executes submission")
        (scratch / "reserving_results.json").write_text("{not valid json")
        subprocess.run(command, env=env, check=True, capture_output=True)
        check(float((scratch / "logs/reward.txt").read_text()) == 0, "malformed JSON yields zero")
        malformed_report = json.loads((scratch / "logs/reward.json").read_text())
        for token in ("NaN", "Infinity", "-Infinity"):
            for location in ("scored", "ignored"):
                document = copy.deepcopy(oracle)
                if location == "scored":
                    document["predictions"][0]["ultimate_severity"] = float(token)
                else:
                    document["ignored"] = {"nested": [float(token)]}
                (scratch / "reserving_results.json").write_text(json.dumps(document))
                result = subprocess.run(command, env=env, check=True, text=True, capture_output=True)
                report = json.loads((scratch / "logs/reward.json").read_text())
                check(float((scratch / "logs/reward.txt").read_text()) == report["score"] == 0
                      and report["submission_error"] == f"nonstandard JSON constant: {token}"
                      and set(report) == set(malformed_report)
                      and {k: v for k, v in report.items() if k != "submission_error"}
                      == {k: v for k, v in malformed_report.items() if k != "submission_error"}
                      and ">>>>> Start Structured Result" in result.stdout
                      and ">>>>> End Structured Result" in result.stdout,
                      f"{token} in {location} field yields zero through malformed-JSON reporting")
        document = copy.deepcopy(oracle)
        document["ignored"] = {"nested": [1.25, -2.5, 0.0, 42, None, {"array": []}]}
        (scratch / "reserving_results.json").write_text(json.dumps(document, allow_nan=False))
        subprocess.run(command, env=env, check=True, capture_output=True)
        report = json.loads((scratch / "logs/reward.json").read_text())
        check(report == full and float((scratch / "logs/reward.txt").read_text()) == 100.0,
              "legitimate floats, integers, nulls, nested objects and arrays retain oracle score exactly 100")
        (scratch / "reserving_results.json").unlink()
        (scratch / "reserving_results.json").symlink_to(ROOT / "solution/measurements/oracle.json")
        subprocess.run(command, env=env, check=True, capture_output=True)
        check(float((scratch / "logs/reward.txt").read_text()) == 0, "symlinked submission rejected")
    scores = [summary["scores"][name]["score"] for name in summary["ordering"]]
    for name, value in zip(summary["ordering"], scores):
        print(f"SCORE {name}: {value:.6f}/100")
    values = {name: report["score"] for name, report in summary["scores"].items()}
    check(values["oracle"] == 100.0 and values["empty"] == 0.0, "baseline-anchor endpoints remain exactly 100 and 0")
    check(all(values[name] < values["public_reference"] < values["oracle"]
              for name in ("empty", "copy_forward", "chain_ladder")),
          "every non-reference control below public_reference, which remains below oracle")
    check(all(0 <= spec["anchor_floor"] < spec["anchor_full"] == 1 for spec in scoring.LANES.values()),
          "every baseline floor strictly below 1.0")
    check(all(0 <= values[name] < 1.0 for name in ("copy_forward", "chain_ladder")),
          "textbook_baselines_approximately_zero: both below 1 point of 100, not necessarily exactly zero")
    print("BASELINE ANCHOR RECORD " + json.dumps(study["baseline_anchor_record"], sort_keys=True))
    hardening = measure_hardening(verbose=False)
    check(hardening["large_loss_ceiling"]["before"] == hardening["large_loss_ceiling"]["after"] == 1.0,
          "large-loss attainable public-input ceiling measured before/after: 1.000000 / 1.000000")
    probe = hardening["conditional_public_cash_probe"]["after"]
    print("CASH PROBES " + json.dumps(hardening["conditional_public_cash_probe"], sort_keys=True))
    check(probe["cash_metric"] > summary["scores"]["public_reference"]["lanes"]["cash_timing"]["metric"],
          "public-only exposure conditioning improves the unchanged cash baseline")
    check(probe["conditional_cohort_mean"] > probe["cohort_mean"],
          "public-only exposure conditioning beats the cohort-mean cash control")
    check(not any(p.name == "__pycache__" or p.suffix == ".pyc" or p.name.startswith("._") for p in ROOT.rglob("*")),
          "no __pycache__, pyc or AppleDouble files")
    print("FUNCTIONAL SELFTEST PASSED; design qualification follows and is not implied.")
    print_report(study)
    # Deliberately fail the overall selftest when the requested design is not
    # supported. Do not weaken assertions or mark a rejected design as passing.
    assert_design(study)
    print("SELFTEST PASSED INCLUDING CROSS-SUB-PROBLEM QUALIFICATION; NOT A DURATION CLAIM")


if __name__ == "__main__":
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            try:
                main()
            except AssertionError as exc:
                print("SELFTEST FAILED: " + str(exc))
                raise SystemExit(1) from None
            except Exception as exc:
                print(f"SELFTEST FAILED: {type(exc).__name__}: {exc}")
                raise SystemExit(1) from None
    finally:
        text = output.getvalue()
        print(text, end="")
        (ROOT / "solution/measurements/selftest.txt").write_text(text)
