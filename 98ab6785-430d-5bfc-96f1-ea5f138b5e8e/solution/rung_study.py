"""Factorial cross-sub-problem independence, not a duration or discovery proof."""
import copy
import hashlib
from itertools import permutations
from pathlib import Path


def measure(train, queries, submissions, evaluate, lanes):
    truth = submissions["oracle"]["predictions"]
    fields = {name: spec["field"] for name, spec in lanes.items()}
    names = list(fields)
    full_mask = (1 << len(names)) - 1
    studies = {}
    for control in ("copy_forward", "public_reference"):
        naive = submissions[control]
        by_key = {r["record_id"]: r for r in truth}
        reports = {}
        for mask in range(full_mask + 1):
            doc = copy.deepcopy(naive)
            for row in doc["predictions"]:
                for i, name in enumerate(names):
                    if mask & (1 << i):
                        row[fields[name]] = by_key[row["record_id"]][fields[name]]
            reports[mask] = evaluate(doc, truth)
        rows = []
        for i, name in enumerate(names):
            bit = 1 << i
            cold = reports[bit]["score"] - reports[0]["score"]
            warm = reports[full_mask]["score"] - reports[full_mask ^ bit]["score"]
            gains = [reports[mask | bit]["score"] - reports[mask]["score"] for mask in reports if not mask & bit]
            off_target = max(abs(reports[mask | bit]["lanes"][other]["points"] - reports[mask]["lanes"][other]["points"])
                             for mask in reports if not mask & bit for other in names if other != name)
            rows.append({"subproblem": name, "field": fields[name], "gain_when_others_naive": cold,
                         "gain_when_others_reference": warm, "discrepancy": abs(cold - warm),
                         "min_gain_all_contexts": min(gains), "max_gain_all_contexts": max(gains),
                         "max_off_target_change": off_target})
        paths = []
        for order in permutations(range(len(names))):
            mask, gains = 0, []
            for i in order:
                nxt = mask | (1 << i)
                gains.append(reports[nxt]["score"] - reports[mask]["score"])
                mask = nxt
            paths.append({"order": [names[i] for i in order], "gains": gains})
        additive_error = max(abs(reports[mask]["score"] - reports[0]["score"] - sum(rows[i]["gain_when_others_naive"] for i in range(len(names)) if mask & (1 << i))) for mask in reports)
        studies[control] = {"naive_score": reports[0]["score"], "components": rows,
                            "factorial_scores": {str(mask): r["score"] for mask, r in reports.items()},
                            "all_120_repair_orders": paths, "max_additivity_error": additive_error}
    scores = {name: evaluate(document, truth)["score"] for name, document in submissions.items()}
    checks = {
        "five_distinct_output_fields": len(fields) == len(set(fields.values())) == 5,
        "weights_sum_100_and_max_20": sum(s["weight"] for s in lanes.values()) == 100 and max(s["weight"] for s in lanes.values()) <= 20,
        "cross_problem_gains_equal": all(r["discrepancy"] <= 1e-10 for s in studies.values() for r in s["components"]),
        "all_80_edges_per_control_local": all(r["max_off_target_change"] == 0 for s in studies.values() for r in s["components"]),
        "all_32_combinations_additive": all(s["max_additivity_error"] <= 1e-10 for s in studies.values()),
        "every_problem_has_naive_headroom": all(r["min_gain_all_contexts"] > 0.01 for r in studies["copy_forward"]["components"]),
        "every_problem_has_competent_headroom": all(r["min_gain_all_contexts"] > 0.01 for r in studies["public_reference"]["components"]),
        "all_120_orders_monotone": all(g > 0 for s in studies.values() for path in s["all_120_repair_orders"] for g in path["gains"]),
        "oracle_exactly_100": scores["oracle"] == 100.0,
        "empty_exactly_zero": scores["empty"] == 0,
        "controls_below_public_reference": all(scores[name] < scores["public_reference"] for name in ("empty", "copy_forward", "chain_ladder")),
        "public_reference_below_oracle": scores["public_reference"] < scores["oracle"],
        "floors_strictly_below_one": all(0 <= s["anchor_floor"] < s["anchor_full"] == 1 for s in lanes.values()),
        "textbook_baselines_approximately_zero": all(0 <= scores[name] < 1.0 for name in ("copy_forward", "chain_ladder")),
    }
    root = Path(__file__).resolve().parents[1]
    sources = ("solution/reserving_reference.py", "solution/public_reference.py", "solution/baselines/adapt.py", "solution/rung_study.py", "tests/scoring/score.py", "tests/scoring/scorer_manifest.json")
    return {"status": "ACCEPT_STRUCTURE" if all(checks.values()) else "REJECT", "checks": checks,
            "scores": scores, "controls": studies, "components": studies["copy_forward"]["components"],
            "baseline_anchor_record": {"name": "textbook_baselines_approximately_zero",
                                      "definition": "Each textbook baseline is below 1 point of 100, not necessarily exactly zero.",
                                      "scores": {name: scores[name] for name in ("copy_forward", "chain_ladder")},
                                      "strict_five_point_ordering": all(b > a for a, b in zip(scores.values(), list(scores.values())[1:]))},
            "scope": "Independent available score gains, NOT learned repair paths or demonstrated hours of progress",
            "protected_source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources}}


def assert_design(study):
    failures = [name for name, passed in study["checks"].items() if not passed]
    assert not failures, "Cross-sub-problem qualification failed: " + ", ".join(failures)


def print_report(study):
    for control, data in study["controls"].items():
        print(f"INDEPENDENCE {control}: problem | others-naive gain | others-reference gain | discrepancy")
        for row in data["components"]:
            print(f"{row['subproblem']}: {row['gain_when_others_naive']:.6f} | {row['gain_when_others_reference']:.6f} | {row['discrepancy']:.12f}")
        print(f"FACTORIAL {control}: 32 combinations, 80 edges, 120 orders; max additivity error {data['max_additivity_error']:.3g}")
    for name, passed in study["checks"].items():
        print(f"DESIGN {'PASS' if passed else 'FAIL'} {name}")
    print("DESIGN VERDICT: " + study["status"] + "; duration unverified")
