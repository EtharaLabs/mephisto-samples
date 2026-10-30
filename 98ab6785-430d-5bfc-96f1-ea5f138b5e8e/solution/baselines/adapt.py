"""Public-data controls; no private-method imports or deliberately omitted fields.

Cash forecasts remain the original copy-forward / chain-ladder / public model.
New estimators are needed for the four previously nonexistent artifact fields.
"""
import math
from collections import defaultdict


def normalize(xs):
    return [x / sum(xs) for x in xs] if sum(xs) else [0.0] * len(xs)


def adapt(document, train, queries, kind="public_reference"):
    if not document["predictions"]:
        return document
    histories = {q["record_id"]: q["history"] for q in queries}
    cohorts, lines = defaultdict(list), defaultdict(list)
    for r in train:
        cohorts[r["cohort"]].append(r)
        lines[r["lob"]].append(r)
    line_size, threshold, rates = {}, {}, {}
    for line, rows in lines.items():
        line_size[line] = sum(r["primary_paid"] / r["inflation_index"] for r in rows) / sum(r["new_reported_count"] for r in rows)
        sizes = sorted(r["primary_paid"] / r["inflation_index"] / r["new_reported_count"] for r in rows if r["new_reported_count"])
        threshold[line] = sizes[math.ceil(0.9 * len(sizes)) - 1]
    for cohort, rows in cohorts.items():
        final = [r for r in rows if r["development_lag"] == 10]
        rates[cohort] = sum(r["reopened_count"] for r in final) / sum(r["reported_count"] for r in final)
    records, risks = [], []
    for old in document["predictions"]:
        h = histories[old["record_id"]]
        last, age = h[-1], len(h)
        own, peer = cohorts[last["cohort"]], lines[last["lob"]]
        n = last["reported_count"]
        observed = sum(r["primary_paid"] / r["inflation_index"] for r in h)
        if kind == "copy_forward":
            severity = observed / max(n, 1)
            pattern = normalize([r["new_reported_count"] for r in h] + [0] * (10 - age))
            hazard = last["reopened_count"] / max(n, 1)
        elif kind == "chain_ladder":
            severity = line_size[last["lob"]]
            pattern = normalize([sum(r["new_reported_count"] for r in peer if r["development_lag"] == lag) for lag in range(1, 11)])
            final = [r for r in peer if r["development_lag"] == 10]
            hazard = sum(r["reopened_count"] for r in final) / sum(r["reported_count"] for r in final)
        else:
            own_size = sum(r["primary_paid"] / r["inflation_index"] for r in own) / sum(r["new_reported_count"] for r in own)
            prior = (25 * own_size + 8 * line_size[last["lob"]]) / 33
            severity = (observed + 100 * prior) / (n + 100)
            pattern = normalize([sum(r["new_reported_count"] for r in own if r["development_lag"] == lag) for lag in range(1, 11)])
            delay = min(r["development_lag"] for r in own if r["reopened_count"] > 0) - 1
            eligible = sum(r["new_reported_count"] for r in h if r["development_lag"] + delay <= age)
            hazard = (last["reopened_count"] + 50 * rates[last["cohort"]]) / (eligible + 50)
        def events(rows):
            return [r["primary_paid"] / r["inflation_index"] / r["new_reported_count"] > threshold[last["lob"]]
                    for r in rows if r["new_reported_count"]]
        recent = events(h)
        if kind == "copy_forward":
            tail = sum(recent) / max(len(recent), 1)
        else:
            past = events(own)
            prior_tail = (sum(past) + 1) / (len(past) + 10)
            tail = prior_tail if kind == "chain_ladder" else (sum(recent) + 10 * prior_tail) / (len(recent) + 10)
        records.append({"record_id": old["record_id"], "accident_period": last["accident_period"], "lob": last["lob"],
                        "observed_lag": age, "ultimate_severity": severity, "reporting_pattern": pattern,
                        "cash_pattern": old["cash_pattern"], "large_loss_score": tail})
        risks.append(hazard)
    buckets = defaultdict(list)
    for i, r in enumerate(records):
        buckets[r["accident_period"], r["lob"]].append(i)
    for ids in buckets.values():
        for i in ids:
            percentile = (sum(risks[j] < risks[i] for j in ids) + 0.5 * sum(risks[j] == risks[i] for j in ids)) / len(ids)
            records[i]["reopening_flag"] = percentile >= 0.8
        values = {i: records[i]["large_loss_score"] for i in ids}
        for i in ids:
            records[i]["large_loss_score"] = (sum(values[j] < values[i] for j in ids) + 0.5 * sum(values[j] == values[i] for j in ids)) / len(ids)
    return {"predictions": records, "self_reported_metrics": {"record_count": len(records)}}
