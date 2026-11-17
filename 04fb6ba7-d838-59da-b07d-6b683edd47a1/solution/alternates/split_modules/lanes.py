"""Alternate oracle B, lane methods: six fitted estimators over six views."""
import json
import math
from pathlib import Path
from statistics import median

from transport import *  # noqa: F401,F403
from transport import FIT_PERIODS, BUCKET_UPPER_DAYS, read_rows, asof, recency, expit, logit, mad_scale, solve, dense_ranks_descending, read_tree

# --- lane 1: dilution reserve, local linear regression per product mix ----------------------

DILUTION_KEYS = ('promo_intensity', 'return_propensity', 'pricing_dispute_index', 'invoice_size_log', 'terms_days')


def _dilution_design(x, scales, centre):
    z = [(x[k] - centre[k]) / scales[k] for k in DILUTION_KEYS]
    return z + [1.0 if x['channel'] == 1 else 0.0, 1.0 if x['channel'] == 2 else 0.0]


def _local_linear(group, z0, h, exclude=None):
    """Weighted local linear fit centred on z0; returns the fitted value at z0."""
    width = 1 + len(z0) + 2
    normal = [[0.0] * (width + 1) for _ in range(width)]
    for idx, (z, y, w) in enumerate(group):
        if idx == exclude:
            continue
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(z[:5], z0)))
        u = d / h
        if u >= 1.0:
            continue
        k = w * (1 - u ** 3) ** 3
        row = [1.0] + [a - b for a, b in zip(z[:5], z0)] + z[5:]
        for i in range(width):
            ri = row[i] * k
            for j in range(i, width):
                normal[i][j] += ri * row[j]
            normal[i][width] += ri * y
    for i in range(width):
        for j in range(i):
            normal[i][j] = normal[j][i]
        if i > 0:
            normal[i][i] += 0.05
    if normal[0][0] < 1e-9:
        return None
    return solve(normal)[0]


def fit_dilution_reserve(workspace_dir):
    rows = read_tree(workspace_dir, 'dilution')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        groups = {}
        for mix in range(4):
            g = [r for r in closed if r['product_mix'] == mix]
            centre = {k: median(r[k] for r in g) for k in DILUTION_KEYS}
            scales = {k: mad_scale([r[k] for r in g], 0.05 if k != 'terms_days' else 5.0) for k in DILUTION_KEYS}
            design = [(_dilution_design(r, scales, centre), logit(r['dilution_ratio']), recency(q, r['booked_period'], 9.0)) for r in g]
            probes = sorted(range(len(design)), key=lambda i: g[i]['case_id'])[:60]
            best = None
            for h in (0.9, 1.3, 1.8):
                error = 0.0
                for i in probes:
                    fit = _local_linear(design, design[i][0][:5], h, exclude=i)
                    error += (design[i][1] - (fit if fit is not None else 0.0)) ** 2
                if best is None or error < best[0]:
                    best = (error, h)
            groups[mix] = {'design': design, 'centre': centre, 'scales': scales, 'bandwidth': best[1], 'loo_error': best[0]}
        models[q] = groups
    return {'models': models, 'observations': observations}


def predict_dilution_reserve(fitted_object, obligor_id, period, workspace_dir):
    x = fitted_object['observations'][obligor_id, period]
    g = fitted_object['models'][period][x['product_mix']]
    z0 = _dilution_design(x, g['scales'], g['centre'])
    fit = _local_linear(g['design'], z0[:5], g['bandwidth'])
    if fit is None:
        fit = _local_linear(g['design'], z0[:5], 3.0 * g['bandwidth'])
    # channel effect enters through the local design, so add it back at the fitted point
    ratio = min(0.6, max(0.001, expit(fit if fit is not None else -3.0)))
    return round(x['open_balance'] * ratio, 2)


# --- lane 2: collection profile, accelerated-time warp of a cell survival curve ---------------

COLLECTION_KEYS = ('past_due_share', 'dispute_share', 'payment_regularity', 'remittance_lag')
TERMS_BAND = {30: 0, 45: 1, 60: 2, 90: 3}


def _weighted_km(rows, weights):
    survival, curve = 1.0, []
    for b in range(8):
        risk = sum(w for r, w in zip(rows, weights) if r['last_observed_bucket'] >= b and (r['paid_bucket'] < 0 or r['paid_bucket'] >= b))
        events = sum(w for r, w in zip(rows, weights) if r['paid_bucket'] == b)
        hazard = events / risk if risk > 0 else 0.0
        survival *= 1 - min(0.98, hazard)
        curve.append(survival)
    return curve


def _restricted_mean(curve):
    total, previous, s_prev = 0.0, 0.0, 1.0
    for s, upper in zip(curve, BUCKET_UPPER_DAYS):
        total += s_prev * (upper - previous)
        previous, s_prev = upper, s
    return total


def _survival_at(curve, t):
    """Log-linear interpolation of the knot survival curve at day t, extrapolated past 270."""
    if t <= 0:
        return 1.0
    knots = [0.0] + [float(u) for u in BUCKET_UPPER_DAYS]
    values = [1.0] + [max(1e-9, s) for s in curve]
    for i in range(1, len(knots)):
        if t <= knots[i]:
            frac = (t - knots[i - 1]) / (knots[i] - knots[i - 1])
            return math.exp(math.log(values[i - 1]) + frac * (math.log(values[i]) - math.log(values[i - 1])))
    slope = (math.log(values[-1]) - math.log(values[-2])) / (knots[-1] - knots[-2])
    return math.exp(math.log(values[-1]) + slope * (t - knots[-1]))


def fit_collection_profile(workspace_dir):
    rows = read_tree(workspace_dir, 'collections')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        weights = [recency(q, r['booked_period'], 8.0) for r in closed]
        scales = {k: mad_scale([r[k] for r in closed], 0.03) for k in COLLECTION_KEYS}
        cells = {}
        for region in range(4):
            pool_idx = [i for i, r in enumerate(closed) if r['region'] == region]
            pool_curve = _weighted_km([closed[i] for i in pool_idx], [weights[i] for i in pool_idx])
            for band in range(4):
                idx = [i for i in pool_idx if TERMS_BAND[closed[i]['terms_days']] == band]
                # cell curve shrunk toward the regional pool with four pseudo-cohorts per bucket
                survival, curve = 1.0, []
                pool_prev = 1.0
                for b in range(8):
                    risk = sum(weights[i] for i in idx if closed[i]['last_observed_bucket'] >= b and (closed[i]['paid_bucket'] < 0 or closed[i]['paid_bucket'] >= b))
                    events = sum(weights[i] for i in idx if closed[i]['paid_bucket'] == b)
                    pool_hazard = 1 - pool_curve[b] / pool_prev if pool_prev > 0 else 0.0
                    pool_prev = pool_curve[b]
                    hazard = (events + 4.0 * pool_hazard) / (risk + 4.0)
                    survival *= 1 - min(0.98, hazard)
                    curve.append(survival)
                cells[region, band] = {'curve': curve, 'mean_time': _restricted_mean(curve), 'support': len(idx)}
        models[q] = {'rows': closed, 'weights': weights, 'scales': scales, 'cells': cells}
    return {'models': models, 'observations': observations}


def predict_collection_profile(fitted_object, obligor_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][obligor_id, period]
    band = TERMS_BAND[x['terms_days']]
    cell = m['cells'][x['region'], band]
    distances = []
    for r, w in zip(m['rows'], m['weights']):
        d = sum(((x[k] - r[k]) / s) ** 2 for k, s in m['scales'].items())
        d += 1.0 * (r['region'] != x['region']) + 0.5 * abs(TERMS_BAND[r['terms_days']] - band)
        distances.append((d, r['case_id'], r, w))
    near = sorted(distances, key=lambda v: (v[0], v[1]))[:30]
    radius = max(0.01, near[-1][0])
    kernel = [math.exp(-4.0 * d / radius) * w for d, _, _, w in near]
    curve = _weighted_km([r for _, _, r, _ in near], kernel)
    n_eff = sum(kernel) ** 2 / sum(k * k for k in kernel)
    ratio = cell['mean_time'] / max(1.0, _restricted_mean(curve))
    acceleration = min(3.5, max(0.3, ratio ** (n_eff / (n_eff + 2.0))))
    previous, result, s_prev = 0.0, [], 1.0
    for upper in BUCKET_UPPER_DAYS:
        s = _survival_at(cell['curve'], acceleration * upper)
        result.append(math.floor(max(0.0, s_prev - s) * 10 ** 8) / 10 ** 8)
        s_prev = s
    return result


# --- lane 3: dispute flag, ridge logistic regression with a prevalence-matched threshold ------

def _dispute_features(x):
    return [x['open_dispute_count'], x['invoice_error_rate'], x['po_mismatch_rate'], math.log1p(x['days_since_last_dispute']),
            x['contact_responsiveness'], x['invoice_error_rate'] * x['po_mismatch_rate'],
            x['open_dispute_count'] * (1 - x['contact_responsiveness'])]


def _dispute_design(x, means, sds):
    f = _dispute_features(x)
    return [1.0] + [(v - m) / s for v, m, s in zip(f, means, sds)] + [1.0 if x['contract_type'] == c else 0.0 for c in (1, 2, 3)]


def fit_dispute_flag(workspace_dir):
    rows = read_tree(workspace_dir, 'disputes')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        raw = [_dispute_features(r) for r in closed]
        means = [sum(f[i] for f in raw) / len(raw) for i in range(7)]
        sds = [max(1e-6, math.sqrt(sum((f[i] - means[i]) ** 2 for f in raw) / len(raw))) for i in range(7)]
        design = [_dispute_design(r, means, sds) for r in closed]
        y = [r['escalated'] for r in closed]
        w = [recency(q, r['booked_period'], 8.0) for r in closed]
        width = len(design[0])
        beta = [0.0] * width
        ridge = 1.0
        for _ in range(30):
            p = [expit(sum(b * v for b, v in zip(beta, d))) for d in design]
            gradient = [sum(wi * (yi - pi) * d[i] for wi, yi, pi, d in zip(w, y, p, design)) - (ridge * beta[i] if i else 0.0) for i in range(width)]
            hessian = [[0.0] * (width + 1) for _ in range(width)]
            for wi, pi, d in zip(w, p, design):
                k = wi * pi * (1 - pi)
                for i in range(width):
                    for j in range(width):
                        hessian[i][j] += k * d[i] * d[j]
            for i in range(width):
                if i:
                    hessian[i][i] += ridge
                hessian[i][width] = gradient[i]
            step = solve(hessian)
            beta = [b + s for b, s in zip(beta, step)]
            if max(abs(s) for s in step) < 1e-8:
                break
        recent = [(d, yi, wi) for d, yi, wi, r in zip(design, y, w, closed) if r['booked_period'] >= q - 6]
        prevalence = sum(yi * wi for _, yi, wi in recent) / sum(wi for _, _, wi in recent)
        scored = sorted(((expit(sum(b * v for b, v in zip(beta, d))), wi) for d, _, wi in recent), reverse=True)
        total, cumulative, threshold = sum(wi for _, wi in scored), 0.0, scored[0][0]
        for p, wi in scored:
            cumulative += wi
            threshold = p
            if cumulative >= prevalence * total:
                break
        models[q] = {'beta': beta, 'means': means, 'sds': sds, 'threshold': threshold, 'prevalence': prevalence}
    return {'models': models, 'observations': observations}


def predict_dispute_flag(fitted_object, obligor_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][obligor_id, period]
    p = expit(sum(b * v for b, v in zip(m['beta'], _dispute_design(x, m['means'], m['sds']))))
    return int(p >= m['threshold'])


# --- lane 4: recovery tier, kernel regression with cohort quartiles --------------------------

RECOVERY_KEYS = ('days_past_due', 'secured_share', 'guarantor_strength', 'prior_cures', 'exposure_log')


def _recovery_point(x, scales):
    return [x[k] / scales[k] for k in RECOVERY_KEYS]


def _nadaraya_watson(points, z0, h, kappa, prior, exclude=None):
    num, den = kappa * prior, kappa
    for idx, (z, y, w) in enumerate(points):
        if idx == exclude:
            continue
        d2 = sum((a - b) ** 2 for a, b in zip(z, z0))
        k = w * math.exp(-d2 / (2 * h * h))
        num += k * y
        den += k
    return num / den


def fit_recovery_tier(workspace_dir):
    rows = read_tree(workspace_dir, 'delinquencies')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        stages = {}
        for stage in range(4):
            g = [r for r in closed if r['legal_stage'] == stage]
            scales = {k: mad_scale([r[k] for r in g], 0.02) for k in RECOVERY_KEYS}
            points = [(_recovery_point(r, scales), r['recovered_fraction'], recency(q, r['booked_period'], 7.0)) for r in g]
            prior = sum(y * w for _, y, w in points) / sum(w for _, _, w in points)
            best = None
            probes = sorted(range(len(points)), key=lambda i: g[i]['case_id'])[:80]
            for h in (0.6, 0.9, 1.3, 1.9):
                error = sum((points[i][1] - _nadaraya_watson(points, points[i][0], h, 3.0, prior, exclude=i)) ** 2 for i in probes)
                if best is None or error < best[0]:
                    best = (error, h)
            stages[stage] = {'points': points, 'scales': scales, 'bandwidth': best[1], 'prior': prior, 'loo_error': best[0]}
        models[q] = stages
    return {'models': models, 'observations': observations}


def recovery_score(fitted_object, obligor_id, period):
    x = fitted_object['observations'][obligor_id, period]
    s = fitted_object['models'][period][x['legal_stage']]
    return _nadaraya_watson(s['points'], _recovery_point(x, s['scales']), s['bandwidth'], 3.0, s['prior'])


def predict_recovery_tier(fitted_object, obligor_id, period, workspace_dir):
    x = fitted_object['observations'][obligor_id, period]
    cache = fitted_object.setdefault('tier_cache', {})
    key = (period, x['legal_stage'])
    if key not in cache:
        cohort = sorted(a for (a, q), r in fitted_object['observations'].items() if q == period and r['legal_stage'] == x['legal_stage'])
        ordered = sorted(cohort, key=lambda a: (recovery_score(fitted_object, a, period), a))
        cache[key] = {a: min(3, 4 * position // len(ordered)) for position, a in enumerate(ordered)}
    return cache[key][obligor_id]


# --- lane 5: availability rank, ridge on a seasonal basis with robust residual kernel ---------

AVAILABILITY_KEYS = ('ineligible_share', 'concentration_index', 'cross_aged_share', 'insurance_coverage', 'dilution_history', 'seasonality_phase')


def availability_basis(r):
    phase = 2 * math.pi * r['seasonality_phase']
    return [1.0, r['ineligible_share'], r['concentration_index'], r['cross_aged_share'], r['insurance_coverage'],
            math.cos(phase), math.sin(phase), r['ineligible_share'] * r['concentration_index'], r['dilution_history'],
            math.log(r['gross_receivables']) - 12.5, math.sin(3.0 * r['concentration_index'] + 4.0 * r['cross_aged_share'])]


def fit_availability_rank(workspace_dir):
    rows = read_tree(workspace_dir, 'borrowing_base')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        scales = {}
        for k in AVAILABILITY_KEYS:
            ordered = sorted(r[k] for r in closed)
            scales[k] = max(0.02, ordered[3 * len(ordered) // 4] - ordered[len(ordered) // 4])
        bands = {}
        for band in range(4):
            g = [r for r in closed if r['advance_band'] == band]
            xs = [availability_basis(r) for r in g]
            ys = [logit(r['availability_ratio']) for r in g]
            ws = [recency(q, r['booked_period'], 8.0) for r in g]
            width = len(xs[0])
            normal = [[sum(w * x[i] * x[j] for x, w in zip(xs, ws)) + (0.2 if i == j and i else 0.0) for j in range(width)]
                      + [sum(w * x[i] * y for x, y, w in zip(xs, ys, ws))] for i in range(width)]
            coefficients = solve(normal)
            residuals = [y - sum(a * b for a, b in zip(x, coefficients)) for x, y in zip(xs, ys)]
            centre = median(residuals)
            spread = max(0.01, median(abs(e - centre) for e in residuals))
            bands[band] = {'coefficients': coefficients, 'centre': centre, 'spread': spread,
                           'rows': [(r, e, w) for r, e, w in zip(g, residuals, ws)]}
        models[q] = {'scales': scales, 'bands': bands}
    return {'models': models, 'observations': observations}


def availability_net(fitted_object, obligor_id, period):
    """Undrawn headroom: gross receivables times the fitted ratio, less reserve holdback and drawn balance."""
    m = fitted_object['models'][period]
    x = fitted_object['observations'][obligor_id, period]
    band = m['bands'][x['advance_band']]
    base = sum(a * b for a, b in zip(availability_basis(x), band['coefficients']))
    distances = []
    for r, e, w in band['rows']:
        d = sum(((x[k] - r[k]) / s) ** 2 for k, s in m['scales'].items())
        distances.append((d, r['case_id'], e, w))
    near = sorted(distances, key=lambda v: (v[0], v[1]))[:40]
    radius = max(0.01, near[-1][0])
    num, den = 6.0 * band['centre'], 6.0
    for d, _, e, w in near:
        k = math.exp(-2.0 * d / radius) * w
        num += k * max(band['centre'] - 3 * band['spread'], min(band['centre'] + 3 * band['spread'], e))
        den += k
    ratio = expit(base + num / den)
    return x['gross_receivables'] * ratio - x['reserve_holdback'] - x['drawn_balance']


def predict_availability_rank(fitted_object, obligor_id, period, workspace_dir):
    queries = read_rows(Path(workspace_dir) / 'queries.jsonl')
    cohort = [r['obligor_id'] for r in queries if r['period'] == period]
    if obligor_id not in cohort:
        cohort = [a for (a, q), r in fitted_object['observations'].items() if q == period and r['cohort'] == 'reference']
    cache = fitted_object.setdefault('rank_cache', {})
    key = (period, tuple(sorted(cohort)))
    if key not in cache:
        cache[key] = dense_ranks_descending({a: round(availability_net(fitted_object, a, period), 6) for a in cohort})
    return cache[key][obligor_id]


# --- lane 6: loss reserve, two-part kernel model with empirical-Bayes severity ----------------

LOSS_KEYS = ('payment_score', 'sector_stress', 'years_relationship', 'credit_limit_utilisation')


def fit_loss_reserve(workspace_dir):
    rows = read_tree(workspace_dir, 'writeoffs')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        scales = {k: mad_scale([r[k] for r in closed], 0.02) for k in LOSS_KEYS}
        scales['exposure_log'] = mad_scale([math.log(r['exposure']) for r in closed], 0.05)
        bands = {}
        for band in range(4):
            g = [r for r in closed if r['rating_band'] == band]
            positive = [r['loss_amount'] / r['exposure'] for r in g if r['loss_amount'] > 0]
            logs = [math.log(v) for v in positive]
            centre = sum(logs) / len(logs)
            variance = sum((v - centre) ** 2 for v in logs) / len(logs)
            tail = sorted(positive)[int(0.85 * (len(positive) - 1))]
            bands[band] = {'rate': (len(positive) + 1) / (len(g) + 2), 'log_centre': centre, 'log_variance': variance,
                           'tail': tail, 'exceedance': sum(v > tail for v in positive) / len(positive),
                           'rows': [(r, recency(q, r['booked_period'], 8.0)) for r in g]}
        models[q] = {'scales': scales, 'bands': bands}
    return {'models': models, 'observations': observations}


def predict_loss_reserve(fitted_object, obligor_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][obligor_id, period]
    band = m['bands'][x['rating_band']]
    distances = []
    for r, w in band['rows']:
        d = sum(min(25.0, ((x[k] - r[k]) / m['scales'][k]) ** 2) for k in LOSS_KEYS)
        d += min(25.0, ((math.log(x['exposure']) - math.log(r['exposure'])) / m['scales']['exposure_log']) ** 2)
        distances.append((d, r['case_id'], r, w))
    near = sorted(distances, key=lambda v: (v[0], v[1]))[:48]
    radius = max(0.01, near[-1][0])
    count, events, logsum, severity_n, excess = 5.0, 5.0 * band['rate'], 4.0 * band['log_centre'], 4.0, 4.0 * band['exceedance']
    for d, _, r, w in near:
        k = math.exp(-2.0 * d / radius) * w
        count += k
        if r['loss_amount'] > 0:
            rate = r['loss_amount'] / r['exposure']
            events += k
            severity_n += k
            logsum += k * math.log(rate)
            excess += k * (rate > band['tail'])
    mean_rate = math.exp(logsum / severity_n + 0.3 * band['log_variance'])
    expected = events / count * mean_rate + 0.2 * band['tail'] * excess / severity_n
    return round(max(0.0, x['exposure'] * expected * (1 - x['insured_share'])), 2)


