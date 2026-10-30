"""Private marked-Poisson claims process; no score-dependent parameters."""
import math
import random


def inflation(calendar, g):
    b = g["calendar_break"]
    trend = min(calendar, b) * g["calendar_growth_before"]
    trend += max(0, calendar - b) * g["calendar_growth_after"]
    return math.exp(trend + g["calendar_season_amplitude"] * math.sin(
        2 * math.pi * calendar / g["calendar_season_period"]))


def poisson(rng, mean):
    # Exact Poisson via exponential interarrival times, not a Gaussian shortcut.
    elapsed, count = 0.0, 0
    while True:
        elapsed += rng.expovariate(mean)
        if elapsed > 1:
            return count
        count += 1


def cohort_parameters(g):
    rng = random.Random(g["seed"])
    out = []
    for line in range(g["lines"]):
        for cohort in range(g["cohorts_per_line"]):
            latent = rng.gauss(0, g["cohort_log_sd"])
            tilt = rng.uniform(*g["delay_tilt_range"])
            weights = [w * math.exp(tilt * j) for j, w in enumerate(g["report_weights"])]
            out.append({
                "lob": f"L{line}", "cohort": f"L{line}C{cohort:02d}",
                "frequency": (g["frequency_base"] + line * g["frequency_line_step"]) * math.exp(latent),
                "severity": g["severity_base"] + line * g["severity_line_step"],
                "report_mass": [w / sum(weights) for w in weights],
                "settle_fraction": rng.uniform(*g["settlement_fraction_range"]),
                "reopen_probability": rng.uniform(*g["reopening_probability_range"]),
                "reopen_fraction": rng.uniform(*g["reopening_fraction_range"]),
                "booking_factor": rng.uniform(*g["booking_factor_range"]),
                "risk_index": math.exp(latent + rng.gauss(0, g["risk_index_noise_sd"])),
            })
    return out


def simulate(g):
    rng = random.Random(g["seed"] + 1)
    train, queries, outcomes = [], [], []
    params = cohort_parameters(g)
    periods = list(range(g["train_periods"][0], g["train_periods"][1] + 1))
    periods += list(range(g["query_periods"][0], g["query_periods"][1] + 1))
    for ap in periods:
        for ci, p in enumerate(params):
            exposure = rng.uniform(*g["exposure_range"])
            # Portfolio workload affects settlement service time. This uses an
            # already-observed covariate, without consuming the claims RNG or
            # changing reports, primary severities or reopening events/payments.
            settlement_delay = g["settlement_delay"]
            settlement_scale = g.get("settlement_amount_scale", 1.0)
            if "settlement_workload_split" in g:
                settlement_delay = g["settlement_workload_delays"][int(exposure > g["settlement_workload_split"])]
            horizon = g["development_horizon"]
            primary, settled, reopened = ([0.0] * (horizon + 1) for _ in range(3))
            reports, reopens = ([0] * (horizon + 1) for _ in range(2))
            base = [0.0] * (horizon + 1)
            for lag, mass in enumerate(p["report_mass"], 1):
                n = poisson(rng, exposure * p["frequency"] * mass)
                reports[lag] = n
                for _ in range(n):
                    sigma = g["severity_log_sd"]
                    severity = p["severity"] * math.exp(rng.gauss(-sigma * sigma / 2, sigma))
                    if rng.random() < g["large_loss_probability"]:
                        severity *= g["large_loss_multiplier"]
                    base[lag] += severity
                    primary[lag] += severity * inflation(ap + lag, g)
                    s = lag + settlement_delay
                    settled[s] += severity * p["settle_fraction"] * settlement_scale * inflation(ap + s, g)
                    r = lag + g["reopening_delay"]
                    if rng.random() < p["reopen_probability"]:
                        reopened[r] += severity * p["reopen_fraction"] * inflation(ap + r, g)
                        reopens[r] += 1
            history, cumulative, count, rc = [], 0.0, 0, 0
            record_id = f"{p['cohort']}-A{ap:03d}"
            for lag in range(1, horizon + 1):
                cumulative += primary[lag] + settled[lag] + reopened[lag]
                count += reports[lag]
                rc += reopens[lag]
                # Booked case only for known reports still awaiting settlement.
                outstanding = sum(base[r] for r in range(1, lag + 1)
                                  if r + settlement_delay > lag)
                case = outstanding * p["settle_fraction"] * settlement_scale * p["booking_factor"] * inflation(ap + lag, g)
                row = {"record_id": record_id, "lob": p["lob"], "cohort": p["cohort"],
                       "accident_period": ap, "development_lag": lag, "calendar_period": ap + lag,
                       "exposure": exposure, "risk_index": p["risk_index"],
                       "inflation_index": inflation(ap + lag, g),
                       "primary_paid": primary[lag], "settlement_paid": settled[lag],
                       "reopening_paid": reopened[lag], "paid": cumulative,
                       "case_reserve": case, "incurred": cumulative + case,
                       "reported_count": count, "new_reported_count": reports[lag],
                       "reopened_count": rc}
                row = {k: round(v, g["round_digits"]) if isinstance(v, float) else v for k, v in row.items()}
                history.append(row)
            if ap <= g["train_periods"][1]:
                train.extend(history)
            else:
                age = g["observed_lags"][(ap + ci) % len(g["observed_lags"])]
                queries.append({"record_id": record_id, "history": history[:age]})
                outcomes.append({"record_id": record_id, "accident_period": ap, "lob": p["lob"],
                                 "observed_lag": age, "paid_at_cutoff": history[age - 1]["paid"],
                                 "incurred_at_cutoff": history[age - 1]["incurred"],
                                 "future_primary": primary[age + 1:],
                                 "future_settlement": settled[age + 1:],
                                 "future_reopening": reopened[age + 1:]})
    return train, queries, outcomes, params
