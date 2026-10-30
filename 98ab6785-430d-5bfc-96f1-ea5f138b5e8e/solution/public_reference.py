"""Public-data-only credibility reserving. Stdlib; never reads private inputs.

CLI: python public_reference.py --data-dir environment --output results.json
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def inflation_forecaster(train):
    index = {r["calendar_period"]: r["inflation_index"] for r in train}
    end = max(index)
    growth = statistics.median(math.log(index[c] / index[c - 4]) / 4
                               for c in range(end - 3, end + 1))
    phase = {c % 4: math.log(index[c]) - growth * c for c in range(end - 3, end + 1)}
    return lambda c: math.exp(growth * c + phase[c % 4])


def fit(train):
    cohort_rows, line_rows = defaultdict(list), defaultdict(list)
    series = defaultdict(dict)
    for r in train:
        cohort_rows[r["cohort"]].append(r)
        line_rows[r["lob"]].append(r)
        series[r["record_id"]][r["development_lag"]] = r
    params = {}
    for cohort, rows in sorted(cohort_rows.items()):
        p = {"primary_rate": {}, "settle": 0.0, "reopen": 0.0}
        peer = line_rows[rows[0]["lob"]]
        risk_scale = rows[0]["risk_index"] / statistics.fmean(r["risk_index"] for r in peer)
        for lag in range(1, 11):
            obs = [r for r in rows if r["development_lag"] == lag]
            peers = [r for r in peer if r["development_lag"] == lag]
            own = sum(r["primary_paid"] / r["inflation_index"] for r in obs) / sum(r["exposure"] for r in obs)
            prior = sum(r["primary_paid"] / r["inflation_index"] for r in peers) / sum(r["exposure"] for r in peers)
            credibility = len(obs) / (len(obs) + 8.0)
            p["primary_rate"][lag] = credibility * own + (1 - credibility) * prior * risk_scale
        # Payment lags are inferred by pooled normalized regression residuals.
        for target, name in [("settlement_paid", "settle"), ("reopening_paid", "reopen")]:
            candidates = []
            for delay in range(1, 6):
                pairs = []
                for r in rows:
                    prev = series[r["record_id"]].get(r["development_lag"] - delay)
                    if prev:
                        pairs.append((prev["primary_paid"] / prev["inflation_index"],
                                      r[target] / r["inflation_index"]))
                denom = sum(x * x for x, _ in pairs)
                ratio = sum(x * y for x, y in pairs) / max(denom, 1e-9)
                error = sum((y - ratio * x) ** 2 for x, y in pairs)
                candidates.append((error / len(pairs), delay, pairs))
            _, delay, pairs = min(candidates, key=lambda x: x[0])
            p[name + "_delay"] = delay
            p[name] = sum(y for _, y in pairs) / max(sum(x for x, _ in pairs), 1e-9)
        params[cohort] = p
    return params, inflation_forecaster(train)


def forecast(history, p, future_index):
    latest = history[-1]
    age, ap = latest["development_lag"], latest["accident_period"]
    base = {r["development_lag"]: r["primary_paid"] / r["inflation_index"] for r in history}
    for lag in range(age + 1, 11):
        base[lag] = p["primary_rate"].get(lag, 0.0) * latest["exposure"]
    cash, reopening = {}, {}
    for lag in range(age + 1, 11):
        factor = future_index(ap + lag)
        reopening[lag] = base.get(lag - p["reopen_delay"], 0.0) * p["reopen"] * factor
        cash[lag] = (base.get(lag, 0.0) + base.get(lag - p["settle_delay"], 0.0) * p["settle"]) * factor + reopening[lag]
    return prediction(latest, cash, reopening)


def prediction(latest, cash, reopening):
    reserve = sum(cash.values())
    ultimate = latest["paid"] + reserve
    adequacy = ultimate / max(latest["incurred"], 1.0)
    return {"record_id": latest["record_id"], "ultimate": ultimate, "reserve": reserve,
            "next_cash": cash.get(latest["development_lag"] + 1, 0.0),
            "tail_cash": sum(v for lag, v in cash.items() if lag > 6),
            "risk_score": adequacy, "under_reserved": adequacy > 1.2,
            "reopen_cash": sum(reopening.values()),
            "cash_pattern": [cash.get(lag, 0.0) / reserve if reserve else 0.0 for lag in range(1, 11)]}


def package(predictions):
    return {"predictions": predictions, "self_reported_metrics": {
        "record_count": len(predictions),
        "total_ultimate": sum(r["ultimate"] for r in predictions),
        "total_reserve": sum(r["reserve"] for r in predictions)}}


def solve(data_dir):
    train = read_jsonl(Path(data_dir) / "train.jsonl")
    params, future_index = fit(train)
    return package([forecast(q["history"], params[q["history"][-1]["cohort"]], future_index)
                    for q in read_jsonl(Path(data_dir) / "queries.jsonl")])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("/workspace/data"))
    parser.add_argument("--output", type=Path, default=Path("/workspace/reserving_results.json"))
    args = parser.parse_args()
    args.output.write_text(json.dumps(solve(args.data_dir), sort_keys=True, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
