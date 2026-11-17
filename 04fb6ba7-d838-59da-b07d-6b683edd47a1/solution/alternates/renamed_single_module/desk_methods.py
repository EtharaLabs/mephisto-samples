"""Alternate oracle A: the desk methods with renamed identifiers in one module.

Standard library only. Each lane carries its own fitted estimator over its own data view,
and no estimator reads another lane's data, labels, or fitted object; the only shared code is
transport (file reading) and ordering helpers that hold no fitted state.

Ledger discipline, applied identically in every lane: a surveillance record at month q is
fitted on closed rows booked strictly before q, and each closed row enters the fit with the
values the ledger carried at q. A row restated at or after q enters with its as_booked values.

"""
import json
import math
import sys
from pathlib import Path
from statistics import median

LANES = ('dilution_reserve', 'collection_profile', 'dispute_flag', 'recovery_tier', 'availability_rank', 'loss_reserve')
FIT_PERIODS = (8, 10, 12, 16, 20)
BUCKET_UPPER_DAYS = [15, 30, 45, 60, 90, 120, 180, 270]


# --- transport and ordering helpers (no fitted state) ---------------------------------------

def load_jsonl(path):
    with open(path) as stream:
        return [json.loads(line) for line in stream if line.strip()]


def load_view(workspace, name):
    return [row for path in sorted((Path(workspace) / name).glob('*.jsonl'), key=lambda p: (len(p.stem), p.stem))
            for row in load_jsonl(path)]


def ledger_at(rows, q):
    """Closed rows booked before q, each carrying the values the ledger held at q."""
    out = []
    for r in rows:
        if r.get('kind') != 'closed' or r['booked_period'] >= q:
            continue
        if 'restated_period' in r and r['restated_period'] >= q:
            r = dict(r, **r['as_booked'])
        out.append(r)
    return out


def age_weight(q, booked, tau):
    return math.exp(-(q - 1 - booked) / tau)


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x)) if x > -700 else 0.0


def log_odds(p):
    return math.log(p / (1 - p))


def robust_scale(values, floor):
    centre = median(values)
    return max(floor, median(abs(v - centre) for v in values))


def gauss_jordan(matrix):
    """Gauss-Jordan on an augmented matrix; returns the solution vector."""
    width = len(matrix)
    m = [list(row) for row in matrix]
    for i in range(width):
        pivot = max(range(i, width), key=lambda j: abs(m[j][i]))
        m[i], m[pivot] = m[pivot], m[i]
        divisor = m[i][i] if abs(m[i][i]) > 1e-12 else 1e-12
        m[i] = [v / divisor for v in m[i]]
        for j in range(width):
            if i != j and m[j][i] != 0.0:
                factor = m[j][i]
                m[j] = [a - factor * b for a, b in zip(m[j], m[i])]
    return [m[i][-1] for i in range(width)]


def dense_rank_desc(values):
    order = {value: i + 1 for i, value in enumerate(sorted(set(values.values()), reverse=True))}
    return {key: order[value] for key, value in values.items()}


# --- lane 1: dilution reserve, local linear regression per product mix ----------------------

DILUTION_KEYS = ('promo_intensity', 'return_propensity', 'pricing_dispute_index', 'invoice_size_log', 'terms_days')


def dilution_row(x, scales, centre):
    z = [(x[k] - centre[k]) / scales[k] for k in DILUTION_KEYS]
    return z + [1.0 if x['channel'] == 1 else 0.0, 1.0 if x['channel'] == 2 else 0.0]


def weighted_local_fit(group, z0, h, exclude=None):
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
    return gauss_jordan(normal)[0]


def fit_dilution_reserve(root):
    rows = load_view(root, 'dilution')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = ledger_at(rows, q)
        groups = {}
        for mix in range(4):
            g = [r for r in closed if r['product_mix'] == mix]
            centre = {k: median(r[k] for r in g) for k in DILUTION_KEYS}
            scales = {k: robust_scale([r[k] for r in g], 0.05 if k != 'terms_days' else 5.0) for k in DILUTION_KEYS}
            design = [(dilution_row(r, scales, centre), log_odds(r['dilution_ratio']), age_weight(q, r['booked_period'], 9.0)) for r in g]
            probes = sorted(range(len(design)), key=lambda i: g[i]['case_id'])[:60]
            best = None
            for h in (0.9, 1.3, 1.8):
                error = 0.0
                for i in probes:
                    fit = weighted_local_fit(design, design[i][0][:5], h, exclude=i)
                    error += (design[i][1] - (fit if fit is not None else 0.0)) ** 2
                if best is None or error < best[0]:
                    best = (error, h)
            groups[mix] = {'design': design, 'centre': centre, 'scales': scales, 'bandwidth': best[1], 'loo_error': best[0]}
        models[q] = groups
    return {'models': models, 'observations': observations}


def predict_dilution_reserve(model, obligor, month, root):
    x = model['observations'][obligor, month]
    g = model['models'][month][x['product_mix']]
    z0 = dilution_row(x, g['scales'], g['centre'])
    fit = weighted_local_fit(g['design'], z0[:5], g['bandwidth'])
    if fit is None:
        fit = weighted_local_fit(g['design'], z0[:5], 3.0 * g['bandwidth'])
    # channel effect enters through the local design, so add it back at the fitted point
    ratio = min(0.6, max(0.001, sigmoid(fit if fit is not None else -3.0)))
    return round(x['open_balance'] * ratio, 2)


# --- lane 2: collection profile, accelerated-time warp of a cell survival curve ---------------

COLLECTION_KEYS = ('past_due_share', 'dispute_share', 'payment_regularity', 'remittance_lag')
TERMS_BAND = {30: 0, 45: 1, 60: 2, 90: 3}


def product_limit(rows, weights):
    survival, curve = 1.0, []
    for b in range(8):
        risk = sum(w for r, w in zip(rows, weights) if r['last_observed_bucket'] >= b and (r['paid_bucket'] < 0 or r['paid_bucket'] >= b))
        events = sum(w for r, w in zip(rows, weights) if r['paid_bucket'] == b)
        hazard = events / risk if risk > 0 else 0.0
        survival *= 1 - min(0.98, hazard)
        curve.append(survival)
    return curve


def area_under_survival(curve):
    total, previous, s_prev = 0.0, 0.0, 1.0
    for s, upper in zip(curve, BUCKET_UPPER_DAYS):
        total += s_prev * (upper - previous)
        previous, s_prev = upper, s
    return total


def interpolate_survival(curve, t):
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


def fit_collection_profile(root):
    rows = load_view(root, 'collections')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = ledger_at(rows, q)
        weights = [age_weight(q, r['booked_period'], 8.0) for r in closed]
        scales = {k: robust_scale([r[k] for r in closed], 0.03) for k in COLLECTION_KEYS}
        cells = {}
        for region in range(4):
            pool_idx = [i for i, r in enumerate(closed) if r['region'] == region]
            pool_curve = product_limit([closed[i] for i in pool_idx], [weights[i] for i in pool_idx])
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
                cells[region, band] = {'curve': curve, 'mean_time': area_under_survival(curve), 'support': len(idx)}
        models[q] = {'rows': closed, 'weights': weights, 'scales': scales, 'cells': cells}
    return {'models': models, 'observations': observations}


def predict_collection_profile(model, obligor, month, root):
    m = model['models'][month]
    x = model['observations'][obligor, month]
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
    curve = product_limit([r for _, _, r, _ in near], kernel)
    n_eff = sum(kernel) ** 2 / sum(k * k for k in kernel)
    ratio = cell['mean_time'] / max(1.0, area_under_survival(curve))
    acceleration = min(3.5, max(0.3, ratio ** (n_eff / (n_eff + 2.0))))
    previous, result, s_prev = 0.0, [], 1.0
    for upper in BUCKET_UPPER_DAYS:
        s = interpolate_survival(cell['curve'], acceleration * upper)
        result.append(math.floor(max(0.0, s_prev - s) * 10 ** 8) / 10 ** 8)
        s_prev = s
    return result


# --- lane 3: dispute flag, ridge logistic regression with a prevalence-matched threshold ------

def dispute_raw(x):
    return [x['open_dispute_count'], x['invoice_error_rate'], x['po_mismatch_rate'], math.log1p(x['days_since_last_dispute']),
            x['contact_responsiveness'], x['invoice_error_rate'] * x['po_mismatch_rate'],
            x['open_dispute_count'] * (1 - x['contact_responsiveness'])]


def dispute_row(x, means, sds):
    f = dispute_raw(x)
    return [1.0] + [(v - m) / s for v, m, s in zip(f, means, sds)] + [1.0 if x['contract_type'] == c else 0.0 for c in (1, 2, 3)]


def fit_dispute_flag(root):
    rows = load_view(root, 'disputes')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = ledger_at(rows, q)
        raw = [dispute_raw(r) for r in closed]
        means = [sum(f[i] for f in raw) / len(raw) for i in range(7)]
        sds = [max(1e-6, math.sqrt(sum((f[i] - means[i]) ** 2 for f in raw) / len(raw))) for i in range(7)]
        design = [dispute_row(r, means, sds) for r in closed]
        y = [r['escalated'] for r in closed]
        w = [age_weight(q, r['booked_period'], 8.0) for r in closed]
        width = len(design[0])
        beta = [0.0] * width
        ridge = 1.0
        for _ in range(30):
            p = [sigmoid(sum(b * v for b, v in zip(beta, d))) for d in design]
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
            step = gauss_jordan(hessian)
            beta = [b + s for b, s in zip(beta, step)]
            if max(abs(s) for s in step) < 1e-8:
                break
        recent = [(d, yi, wi) for d, yi, wi, r in zip(design, y, w, closed) if r['booked_period'] >= q - 6]
        prevalence = sum(yi * wi for _, yi, wi in recent) / sum(wi for _, _, wi in recent)
        scored = sorted(((sigmoid(sum(b * v for b, v in zip(beta, d))), wi) for d, _, wi in recent), reverse=True)
        total, cumulative, threshold = sum(wi for _, wi in scored), 0.0, scored[0][0]
        for p, wi in scored:
            cumulative += wi
            threshold = p
            if cumulative >= prevalence * total:
                break
        models[q] = {'beta': beta, 'means': means, 'sds': sds, 'threshold': threshold, 'prevalence': prevalence}
    return {'models': models, 'observations': observations}


def predict_dispute_flag(model, obligor, month, root):
    m = model['models'][month]
    x = model['observations'][obligor, month]
    p = sigmoid(sum(b * v for b, v in zip(m['beta'], dispute_row(x, m['means'], m['sds']))))
    return int(p >= m['threshold'])


# --- lane 4: recovery tier, kernel regression with cohort quartiles --------------------------

RECOVERY_KEYS = ('days_past_due', 'secured_share', 'guarantor_strength', 'prior_cures', 'exposure_log')


def recovery_point(x, scales):
    return [x[k] / scales[k] for k in RECOVERY_KEYS]


def kernel_average(points, z0, h, kappa, prior, exclude=None):
    num, den = kappa * prior, kappa
    for idx, (z, y, w) in enumerate(points):
        if idx == exclude:
            continue
        d2 = sum((a - b) ** 2 for a, b in zip(z, z0))
        k = w * math.exp(-d2 / (2 * h * h))
        num += k * y
        den += k
    return num / den


def fit_recovery_tier(root):
    rows = load_view(root, 'delinquencies')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = ledger_at(rows, q)
        stages = {}
        for stage in range(4):
            g = [r for r in closed if r['legal_stage'] == stage]
            scales = {k: robust_scale([r[k] for r in g], 0.02) for k in RECOVERY_KEYS}
            points = [(recovery_point(r, scales), r['recovered_fraction'], age_weight(q, r['booked_period'], 7.0)) for r in g]
            prior = sum(y * w for _, y, w in points) / sum(w for _, _, w in points)
            best = None
            probes = sorted(range(len(points)), key=lambda i: g[i]['case_id'])[:80]
            for h in (0.6, 0.9, 1.3, 1.9):
                error = sum((points[i][1] - kernel_average(points, points[i][0], h, 3.0, prior, exclude=i)) ** 2 for i in probes)
                if best is None or error < best[0]:
                    best = (error, h)
            stages[stage] = {'points': points, 'scales': scales, 'bandwidth': best[1], 'prior': prior, 'loo_error': best[0]}
        models[q] = stages
    return {'models': models, 'observations': observations}


def recovery_estimate(model, obligor, month):
    x = model['observations'][obligor, month]
    s = model['models'][month][x['legal_stage']]
    return kernel_average(s['points'], recovery_point(x, s['scales']), s['bandwidth'], 3.0, s['prior'])


def predict_recovery_tier(model, obligor, month, root):
    x = model['observations'][obligor, month]
    cache = model.setdefault('tier_cache', {})
    key = (month, x['legal_stage'])
    if key not in cache:
        cohort = sorted(a for (a, q), r in model['observations'].items() if q == month and r['legal_stage'] == x['legal_stage'])
        ordered = sorted(cohort, key=lambda a: (recovery_estimate(model, a, month), a))
        cache[key] = {a: min(3, 4 * position // len(ordered)) for position, a in enumerate(ordered)}
    return cache[key][obligor]


# --- lane 5: availability rank, ridge on a seasonal basis with robust residual kernel ---------

AVAILABILITY_KEYS = ('ineligible_share', 'concentration_index', 'cross_aged_share', 'insurance_coverage', 'dilution_history', 'seasonality_phase')


def seasonal_basis(r):
    phase = 2 * math.pi * r['seasonality_phase']
    return [1.0, r['ineligible_share'], r['concentration_index'], r['cross_aged_share'], r['insurance_coverage'],
            math.cos(phase), math.sin(phase), r['ineligible_share'] * r['concentration_index'], r['dilution_history'],
            math.log(r['gross_receivables']) - 12.5, math.sin(3.0 * r['concentration_index'] + 4.0 * r['cross_aged_share'])]


def fit_availability_rank(root):
    rows = load_view(root, 'borrowing_base')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = ledger_at(rows, q)
        scales = {}
        for k in AVAILABILITY_KEYS:
            ordered = sorted(r[k] for r in closed)
            scales[k] = max(0.02, ordered[3 * len(ordered) // 4] - ordered[len(ordered) // 4])
        bands = {}
        for band in range(4):
            g = [r for r in closed if r['advance_band'] == band]
            xs = [seasonal_basis(r) for r in g]
            ys = [log_odds(r['availability_ratio']) for r in g]
            ws = [age_weight(q, r['booked_period'], 8.0) for r in g]
            width = len(xs[0])
            normal = [[sum(w * x[i] * x[j] for x, w in zip(xs, ws)) + (0.2 if i == j and i else 0.0) for j in range(width)]
                      + [sum(w * x[i] * y for x, y, w in zip(xs, ys, ws))] for i in range(width)]
            coefficients = gauss_jordan(normal)
            residuals = [y - sum(a * b for a, b in zip(x, coefficients)) for x, y in zip(xs, ys)]
            centre = median(residuals)
            spread = max(0.01, median(abs(e - centre) for e in residuals))
            bands[band] = {'coefficients': coefficients, 'centre': centre, 'spread': spread,
                           'rows': [(r, e, w) for r, e, w in zip(g, residuals, ws)]}
        models[q] = {'scales': scales, 'bands': bands}
    return {'models': models, 'observations': observations}


def net_availability(model, obligor, month):
    """Undrawn headroom: gross receivables times the fitted ratio, less reserve holdback and drawn balance."""
    m = model['models'][month]
    x = model['observations'][obligor, month]
    band = m['bands'][x['advance_band']]
    base = sum(a * b for a, b in zip(seasonal_basis(x), band['coefficients']))
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
    ratio = sigmoid(base + num / den)
    return x['gross_receivables'] * ratio - x['reserve_holdback'] - x['drawn_balance']


def predict_availability_rank(model, obligor, month, root):
    queries = load_jsonl(Path(root) / 'queries.jsonl')
    cohort = [r['obligor_id'] for r in queries if r['period'] == month]
    if obligor not in cohort:
        cohort = [a for (a, q), r in model['observations'].items() if q == month and r['cohort'] == 'reference']
    cache = model.setdefault('rank_cache', {})
    key = (month, tuple(sorted(cohort)))
    if key not in cache:
        cache[key] = dense_rank_desc({a: round(net_availability(model, a, month), 6) for a in cohort})
    return cache[key][obligor]


# --- lane 6: loss reserve, two-part kernel model with empirical-Bayes severity ----------------

LOSS_KEYS = ('payment_score', 'sector_stress', 'years_relationship', 'credit_limit_utilisation')


def fit_loss_reserve(root):
    rows = load_view(root, 'writeoffs')
    observations = {(r['obligor_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = ledger_at(rows, q)
        scales = {k: robust_scale([r[k] for r in closed], 0.02) for k in LOSS_KEYS}
        scales['exposure_log'] = robust_scale([math.log(r['exposure']) for r in closed], 0.05)
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
                           'rows': [(r, age_weight(q, r['booked_period'], 8.0)) for r in g]}
        models[q] = {'scales': scales, 'bands': bands}
    return {'models': models, 'observations': observations}


def predict_loss_reserve(model, obligor, month, root):
    m = model['models'][month]
    x = model['observations'][obligor, month]
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


# --- oracle entry point ---------------------------------------------------------------------

def main(argv):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    queries = load_jsonl(workspace / 'queries.jsonl')
    fitted = {lane: globals()['fit_' + lane](workspace) for lane in LANES}
    with open(args.output, 'w') as handle:
        for r in queries:
            record = dict(record_id=r['record_id'], **{lane: globals()['predict_' + lane](fitted[lane], r['obligor_id'], r['period'], workspace) for lane in LANES})
            handle.write(json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
