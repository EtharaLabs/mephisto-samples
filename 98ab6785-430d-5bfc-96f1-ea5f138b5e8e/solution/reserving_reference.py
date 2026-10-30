"""Private five-method reference, observable data only; no scorer imports.

CLI: python reserving.py --data-dir /workspace/data --output FILE
Each estimator returns its own artifact, never another estimator's output.
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

FIELDS = ("ultimate_severity", "reporting_pattern", "reopening_flag", "cash_pattern", "large_loss_score")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def normalize(values):
    total = sum(values)
    return [v / total for v in values] if total else [0.0] * len(values)


def groups(rows, key):
    buckets = defaultdict(list)
    for r in rows:
        buckets[r[key]].append(r)
    return buckets


def robust(values):
    center = statistics.median(values)
    scale = max(statistics.median(abs(v - center) for v in values), center * 0.1, 1e-9)
    return statistics.fmean(min(center + 2.5 * scale, max(center - 2.5 * scale, v)) for v in values)


def severity_estimates(train, queries):
    """Robust primary claim size, deflated; no report-timing or cash forecast."""
    cohorts, lines = groups(train, "cohort"), groups(train, "lob")
    priors = {}
    for cohort, rows in cohorts.items():
        own = [r for r in rows if r["new_reported_count"]]
        peer = [r for r in lines[rows[0]["lob"]] if r["new_reported_count"]]
        n = sum(r["new_reported_count"] for r in own)
        size = lambda rs: robust([r["primary_paid"] / r["inflation_index"] / r["new_reported_count"] for r in rs])
        priors[cohort] = (n * size(own) + 180 * size(peer)) / (n + 180)
    result = []
    for q in queries:
        h = q["history"]
        n = h[-1]["reported_count"]
        observed = sum(r["primary_paid"] / r["inflation_index"] for r in h)
        # Credibility prediction of ultimate average PRIMARY claim size, not
        # total ultimate dollars. Future event counts are not needed here.
        result.append((observed + 80 * priors[h[-1]["cohort"]]) / (n + 80))
    return result


def timing_estimates(train, queries):
    """Count-only reporting distribution; likelihood tilt from observed lag shares."""
    cohorts, lines = groups(train, "cohort"), groups(train, "lob")
    curves = {}
    for cohort, rows in cohorts.items():
        counts = [sum(r["new_reported_count"] for r in rows if r["development_lag"] == lag) for lag in range(1, 11)]
        peer = lines[rows[0]["lob"]]
        prior = normalize([sum(r["new_reported_count"] for r in peer if r["development_lag"] == lag) for lag in range(1, 11)])
        curves[cohort] = normalize([v + 120 * p for v, p in zip(counts, prior)])
    result = []
    for q in queries:
        h = q["history"]
        base, age = curves[h[-1]["cohort"]], len(h)
        # Penalized multinomial log-likelihood over the OBSERVED prefix.
        # Unobserved reports are not treated as zero; entire ten-lag curve is tilted.
        def loss(tilt):
            p = normalize([base[j] * math.exp(tilt * j) for j in range(age)])
            return -sum(r["new_reported_count"] * math.log(max(p[j], 1e-15)) for j, r in enumerate(h)) + 12 * tilt * tilt
        lo, hi = -1.5, 1.5
        for _ in range(48):
            a, b = (2 * lo + hi) / 3, (lo + 2 * hi) / 3
            if loss(a) <= loss(b):
                hi = b
            else:
                lo = a
        tilt = (lo + hi) / 2
        result.append(normalize([p * math.exp(tilt * j) for j, p in enumerate(base)]))
    return result


def peer_ranks(values, queries):
    buckets = defaultdict(list)
    for i, q in enumerate(queries):
        r = q["history"][-1]
        buckets[r["accident_period"], r["lob"]].append(i)
    result = [0.0] * len(values)
    for ids in buckets.values():
        for i in ids:
            result[i] = (sum(values[j] < values[i] for j in ids) + 0.5 * sum(values[j] == values[i] for j in ids)) / len(ids)
    return result


def reopening_estimates(train, queries):
    """Binomial event hazard with inferred count delay; no monetary inputs."""
    series = groups(train, "record_id")
    cohorts = defaultdict(list)
    for h in series.values():
        cohorts[h[0]["cohort"]].append(sorted(h, key=lambda r: r["development_lag"]))
    params = {}
    for cohort, histories in cohorts.items():
        candidates = []
        for delay in range(1, 6):
            pairs = [(h[j - delay]["new_reported_count"], h[j]["reopened_count"] - (h[j - 1]["reopened_count"] if j else 0))
                     for h in histories for j in range(delay, 10)]
            rate = min(1 - 1e-9, max(1e-9, sum(y for _, y in pairs) / max(sum(n for n, _ in pairs), 1)))
            # Impossible binomial counts strongly reject a candidate delay.
            deviance = sum(1e6 * max(0, y - n) - y * math.log(rate) - max(0, n - y) * math.log1p(-rate)
                           - (math.lgamma(n + 1) - math.lgamma(y + 1) - math.lgamma(max(0, n - y) + 1)) for n, y in pairs)
            early = sum(h[delay - 1]["reopened_count"] for h in histories)
            candidates.append((deviance + 1e6 * early, delay, rate))
        _, delay, rate = min(candidates)
        params[cohort] = delay, rate
    risks = []
    for q in queries:
        h = q["history"]
        delay, prior = params[h[-1]["cohort"]]
        eligible = sum(r["new_reported_count"] for r in h if r["development_lag"] + delay <= len(h))
        risks.append((h[-1]["reopened_count"] + 40 * prior) / (eligible + 40))
    return [p >= 0.8 for p in peer_ranks(risks, queries)]


def cash_estimates(train, queries):
    """Empirical matched-prefix cash timing, not severity times report counts."""
    histories = [sorted(h, key=lambda r: r["development_lag"]) for h in groups(train, "record_id").values()]
    cohorts = defaultdict(list)
    for h in histories:
        cohorts[h[0]["cohort"]].append(h)
    indices = {r["calendar_period"]: r["inflation_index"] for r in train}
    for q in queries:
        indices.update({r["calendar_period"]: r["inflation_index"] for r in q["history"]})
    def increments(h):
        return [(r["primary_paid"] + r["settlement_paid"] + r["reopening_paid"]) / r["inflation_index"] for r in h]
    result = []
    for q in queries:
        h, last = q["history"], q["history"][-1]
        age, calendar = len(h), last["calendar_period"]
        observed = normalize(increments(h))
        neighbors = []
        for historical in cohorts[last["cohort"]]:
            cash = increments(historical)
            prefix = normalize(cash[:age])
            distance = sum((a - b) ** 2 for a, b in zip(prefix, observed))
            neighbors.append((distance, historical[0]["record_id"], normalize(cash[age:])))
        selected = sorted(neighbors)[:8]
        weights = [1 / (0.02 + d) for d, _, _ in selected]
        pattern = [sum(w * row[j] for w, (_, _, row) in zip(weights, selected)) / sum(weights) for j in range(10 - age)]
        growth = statistics.median(math.log(indices[c] / indices[c - 4]) / 4 for c in range(calendar - 3, calendar + 1) if c in indices and c - 4 in indices)
        factors = []
        for lag in range(age + 1, 11):
            target = last["accident_period"] + lag
            phase = max(c for c in indices if c <= calendar and c % 4 == target % 4)
            factors.append(indices[phase] * math.exp(growth * (target - phase)))
        result.append([0.0] * age + normalize([p * f for p, f in zip(pattern, factors)]))
    return result


def tail_estimates(train, queries):
    """Exceedance incidence in aggregate cells, not mean severity or cash tail."""
    lines, cohorts = groups(train, "lob"), groups(train, "cohort")
    thresholds, centers = {}, {}
    def residual(r, center):
        n = r["new_reported_count"]
        return (r["primary_paid"] / r["inflation_index"] - n * center) / math.sqrt(max(n, 1))
    for line, rows in lines.items():
        nonzero = [r for r in rows if r["new_reported_count"]]
        center = statistics.median(r["primary_paid"] / r["inflation_index"] / r["new_reported_count"] for r in nonzero)
        centers[line] = center
        xs = sorted(residual(r, center) for r in nonzero)
        thresholds[line] = xs[math.ceil(0.9 * len(xs)) - 1]
    priors = {}
    for cohort, rows in cohorts.items():
        line = rows[0]["lob"]
        flags = [residual(r, centers[line]) > thresholds[line] for r in rows if r["new_reported_count"]]
        priors[cohort] = (sum(flags) + 2) / (len(flags) + 20)
    risks = []
    for q in queries:
        h, last = q["history"], q["history"][-1]
        flags = [residual(r, centers[last["lob"]]) > thresholds[last["lob"]] for r in h if r["new_reported_count"]]
        risks.append((sum(flags) + 8 * priors[last["cohort"]]) / (len(flags) + 8))
    return peer_ranks(risks, queries)


ESTIMATORS = dict(zip(FIELDS, (severity_estimates, timing_estimates, reopening_estimates, cash_estimates, tail_estimates)))


def run(train, queries):
    columns = {field: estimator(train, queries) for field, estimator in ESTIMATORS.items()}
    return [{"record_id": q["record_id"], "accident_period": q["history"][-1]["accident_period"],
             "lob": q["history"][-1]["lob"], "observed_lag": len(q["history"]),
             **{field: values[i] for field, values in columns.items()}} for i, q in enumerate(queries)]


def package(rows):
    # Informational only. Awarding points for this would be inert bookkeeping.
    return {"predictions": rows, "self_reported_metrics": {"record_count": len(rows)}}


def solve(data_dir):
    return package(run(read_jsonl(Path(data_dir) / "train.jsonl"), read_jsonl(Path(data_dir) / "queries.jsonl")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("/workspace/data"))
    parser.add_argument("--output", type=Path, default=Path("/workspace/reserving_results.json"))
    args = parser.parse_args()
    args.output.write_text(json.dumps(solve(args.data_dir), sort_keys=True, allow_nan=False) + "\n")
