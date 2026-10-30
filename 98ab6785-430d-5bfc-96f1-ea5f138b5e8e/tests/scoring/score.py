"""Five additive lanes. Each reads one submitted field and its own private target."""
import json
import math
import statistics
from pathlib import Path

MANIFEST = json.loads(Path(__file__).with_name("scorer_manifest.json").read_text())
LANES = {r["id"]: r for r in MANIFEST["lanes"]}
FIELDS = {k: v["field"] for k, v in LANES.items()}


def finite(x):
    return type(x) in (int, float) and abs(x) <= 1e100 and math.isfinite(x)


def ranks(xs):
    ordered = sorted(range(len(xs)), key=xs.__getitem__)
    result = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i + 1
        while j < len(xs) and xs[ordered[j]] == xs[ordered[i]]:
            j += 1
        for k in ordered[i:j]:
            result[k] = (i + j - 1) / 2
        i = j
    return result


def spearman(a, b):
    if len(a) < 2:
        return 0.0
    a, b = ranks(a), ranks(b)
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    va, vb = sum((x - ma) ** 2 for x in a), sum((y - mb) ** 2 for y in b)
    if not va or not vb:
        return 0.0
    if a == b:
        return 1.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def valid(value, kind, truth):
    if kind == "f1_detection":
        return type(value) is bool
    if kind == "distribution_overlap":
        return (isinstance(value, list) and len(value) == 10
                and all(finite(v) and 0 <= v <= 1 for v in value)
                and sum(value) <= 1 + 1e-6)
    return finite(value) and (kind != "relative_agreement" or value >= 0)


def lane_score(sub, truth, spec):
    field, kind = spec["field"], spec["metric"]
    pairs = []
    for t in truth:
        v = sub.get(t["record_id"], {}).get(field)
        if valid(v, kind, t):
            # Only cash timing requires zero mass in already-observed periods.
            if field == "cash_pattern" and any(v[:t["observed_lag"]]):
                continue
            pairs.append((v, t[field]))
    coverage = len(pairs) / len(truth)
    if not pairs:
        metric, fraction = 0.0, 0.0
    elif kind == "spearman_ic":
        metric = spearman([a for a, _ in pairs], [b for _, b in pairs])
        fraction = max(0.0, min(1.0, (metric - spec["anchor_floor"]) / (1 - spec["anchor_floor"]))) * coverage
    elif kind == "f1_detection":
        tp = sum(a and b for a, b in pairs)
        fp = sum(a and not b for a, b in pairs)
        fn = sum(t[field] for t in truth) - tp
        metric = 2 * tp / max(2 * tp + fp + fn, 1)
        fraction = max(0.0, min(1.0, (metric - spec["anchor_floor"]) / (1 - spec["anchor_floor"]))) * coverage
    elif kind == "relative_agreement":
        errors = [min(1.0, abs(a - b) / max(b, 1)) for a, b in pairs] + [1.0] * (len(truth) - len(pairs))
        metric = (1 - statistics.fmean(errors)) / (1 + math.sqrt(statistics.fmean(e * e for e in errors)))
        fraction = max(0.0, min(1.0, (metric - spec["anchor_floor"]) / (1 - spec["anchor_floor"])))
    else:
        # TV on ten periods plus an explicit unallocated-mass category.
        # Zero vectors earn zero, not half credit. Invalid/missing rows earn zero.
        qualities = [max(0.0, min(1.0, 1 - 0.5 * (sum(abs(x - y) for x, y in zip(a, b)) + abs(sum(a) - sum(b))))) if any(a) else 0.0 for a, b in pairs]
        metric = sum(qualities) / len(truth)
        fraction = max(0.0, min(1.0, (metric - spec["anchor_floor"]) / (1 - spec["anchor_floor"])))
    return {"metric": metric, "coverage": coverage, "fraction": fraction,
            "max": spec["weight"], "points": spec["weight"] * fraction}


def evaluate(document, truth):
    if not truth:
        raise ValueError("empty private target corpus: infrastructure failure")
    if not isinstance(document, dict) or not isinstance(document.get("predictions"), list):
        document = {"predictions": []}
    keys = {t["record_id"] for t in truth}
    sub, duplicates = {}, set()
    for r in document["predictions"]:
        if not isinstance(r, dict) or not isinstance(r.get("record_id"), str):
            continue
        key = r["record_id"]
        if key not in keys:
            continue
        if key in sub:
            duplicates.add(key)
        sub[key] = r
    for key in duplicates:
        sub.pop(key, None)
    result = {lane: lane_score(sub, truth, spec) for lane, spec in LANES.items()}
    # Deliberately no consistency veto, global stability or scored accounting.
    return {"score": sum(row["points"] for row in result.values()), "lanes": result,
            "valid_records": len(sub), "expected_records": len(truth)}
