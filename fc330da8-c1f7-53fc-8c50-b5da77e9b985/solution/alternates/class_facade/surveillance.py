"""Alternate oracle C: the desk methods behind a Surveillance class facade.

Standard library only. Each lane carries its own fitted estimator over its own data view, and
no estimator reads another lane's data, labels or fitted object; the only shared code is
transport (file reading) and ordering helpers that hold no fitted state.

Ledger discipline, applied identically in every lane: a surveillance record at period q is
fitted on closed rows booked strictly before q, and each closed row enters the fit with the
values the ledger carried at q. A row restated at or after q enters with its as_booked values.

"""
import json
import math
import sys
from bisect import bisect_right
from pathlib import Path
from statistics import median

LANES = ('aging_reserve', 'turn_profile', 'sot_flag', 'variance_tier', 'headroom_rank', 'loss_reserve')
FIT_PERIODS = (8, 10, 12, 16, 20)
TURN_UPPER_DAYS = [30, 60, 90, 120, 150, 180, 240, 365]
VARIANCE_CUTS = (0.02, 0.05, 0.10)


# --- transport and ordering helpers (no fitted state) ---------------------------------------

def read_rows(path):
    with open(path) as stream:
        return [json.loads(line) for line in stream if line.strip()]


def read_tree(workspace, name):
    return [row for path in sorted((Path(workspace) / name).glob('*.jsonl'), key=lambda p: (len(p.stem), p.stem))
            for row in read_rows(path)]


def asof(rows, q):
    """Closed rows booked before q, each carrying the values the ledger held at q."""
    out = []
    for r in rows:
        if r.get('kind') != 'closed' or r['booked_period'] >= q:
            continue
        if 'restated_period' in r and r['restated_period'] >= q:
            r = dict(r, **r['as_booked'])
        out.append(r)
    return out


def recency(q, booked, tau):
    return math.exp(-(q - 1 - booked) / tau)


def expit(x):
    return 1.0 / (1.0 + math.exp(-x)) if x > -700 else 0.0


def logit(p):
    return math.log(p / (1 - p))


def mad_scale(values, floor):
    centre = median(values)
    return max(floor, median(abs(v - centre) for v in values))


def solve(matrix):
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


def dense_ranks_descending(values):
    order = {value: i + 1 for i, value in enumerate(sorted(set(values.values()), reverse=True))}
    return {key: order[value] for key, value in values.items()}


def tier_of(fraction):
    return sum(fraction > c for c in VARIANCE_CUTS)


def weighted_quantiles(values, weights, count):
    """count interior weighted quantile knots of the (value, weight) sample, distinct and sorted."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    total = sum(weights)
    knots, cumulative, k = [], 0.0, 1
    for i in order:
        cumulative += weights[i]
        while k <= count and cumulative >= total * k / (count + 1):
            knots.append(values[i])
            k += 1
    return sorted(set(knots))


# --- lane 1: aging reserve, boosted regression stumps on logit haircut -------------------------

AGING_KEYS = ('aged_share', 'days_supply', 'model_year_age', 'demand_index', 'incentive_intensity', 'price_volatility')
AGING_ROUNDS = 80
AGING_SHRINK = 0.1
AGING_LEAF_RIDGE = 1.0


def _aging_columns(x):
    cols = [x[k] for k in AGING_KEYS]
    cols += [1.0 if x['segment'] == c else 0.0 for c in range(1, 4)]
    cols += [1.0 if x['franchise'] == c else 0.0 for c in range(1, 4)]
    return cols


def fit_aging_reserve(workspace_dir):
    rows = read_tree(workspace_dir, 'aging')
    observations = {(r['dealer_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        columns = [_aging_columns(r) for r in closed]
        y = [logit(r['haircut_ratio']) for r in closed]
        w = [recency(q, r['booked_period'], 9.0) for r in closed]
        width = len(columns[0])
        total_w = sum(w)
        f0 = sum(wi * yi for wi, yi in zip(w, y)) / total_w
        fitted = [f0] * len(closed)
        orders, knots = [], []
        for j in range(width):
            values = [c[j] for c in columns]
            orders.append(sorted(range(len(closed)), key=lambda i: (values[i], i)))
            knots.append(weighted_quantiles(values, w, 12) if j < len(AGING_KEYS) else [0.5])
        stumps = []
        for _ in range(AGING_ROUNDS):
            residual = [yi - fi for yi, fi in zip(y, fitted)]
            best = None
            for j in range(width):
                order = orders[j]
                values = [columns[i][j] for i in order]
                # prefix sums of weight and weighted residual along the sorted order
                pw, pr = [0.0], [0.0]
                for i in order:
                    pw.append(pw[-1] + w[i])
                    pr.append(pr[-1] + w[i] * residual[i])
                for t in knots[j]:
                    left = bisect_right(values, t)
                    if left == 0 or left == len(order):
                        continue
                    wl, rl = pw[left], pr[left]
                    wr, rr = pw[-1] - wl, pr[-1] - rl
                    cl, cr = rl / (wl + AGING_LEAF_RIDGE), rr / (wr + AGING_LEAF_RIDGE)
                    gain = 2 * cl * rl - cl * cl * wl + 2 * cr * rr - cr * cr * wr
                    if best is None or gain > best[0]:
                        best = (gain, j, t, cl, cr)
            if best is None:
                break
            _, j, t, cl, cr = best
            stumps.append((j, t, cl, cr))
            for i in range(len(closed)):
                fitted[i] += AGING_SHRINK * (cl if columns[i][j] <= t else cr)
        models[q] = {'f0': f0, 'stumps': stumps, 'support': len(closed)}
    return {'models': models, 'observations': observations}


def aging_score(fitted_object, obligor_id, period):
    m = fitted_object['models'][period]
    cols = _aging_columns(fitted_object['observations'][obligor_id, period])
    value = m['f0']
    for j, t, cl, cr in m['stumps']:
        value += AGING_SHRINK * (cl if cols[j] <= t else cr)
    return value


def predict_aging_reserve(fitted_object, dealer_id, period, workspace_dir):
    x = fitted_object['observations'][dealer_id, period]
    ratio = min(0.5, max(0.002, expit(aging_score(fitted_object, dealer_id, period))))
    return round(x['floored_balance'] * x['aged_share'] * ratio, 2)


# --- lane 2: turn profile, discrete-time complementary log-log hazard ------------------------

TURN_KEYS = ('lot_velocity', 'demand_index', 'pricing_discipline', 'marketing_spend_log', 'stock_age_mix')
TURN_RIDGE = 0.5
TURN_ITERATIONS = 18


TURN_STRATA = 4
TURN_BASELINES = 8 * TURN_STRATA


def _turn_covariates(x, centre, scale):
    """Standardised covariates, region indicators and the segment stratum carried last."""
    z = [(x[k] - centre[k]) / scale[k] for k in TURN_KEYS]
    z += [1.0 if x['region'] == c else 0.0 for c in range(1, 4)]
    return z + [float(x['segment'])]


def _turn_design(bucket, z):
    """One baseline per (segment, band), the covariates, and a late-band stock-age interaction."""
    stratum = int(z[-1])
    baseline = [0.0] * TURN_BASELINES
    baseline[stratum * 8 + bucket] = 1.0
    late = z[4] if bucket >= 4 else 0.0
    return baseline + z[:-1] + [late]


def _cloglog_hazard(eta):
    eta = max(-30.0, min(3.0, eta))
    mu = math.exp(eta)
    survive = math.exp(-mu)
    return mu, survive, min(1 - 1e-12, max(1e-12, 1.0 - survive))


def _turn_objective(beta, design, events, weights):
    total = 0.0
    for d, yv, wv in zip(design, events, weights):
        _, _, h = _cloglog_hazard(sum(bi * di for bi, di in zip(beta, d)))
        total += wv * (math.log(h) if yv else math.log(1 - h))
    return total - 0.5 * TURN_RIDGE * sum(b * b for b in beta[TURN_BASELINES:])


def fit_turn_profile(workspace_dir):
    rows = read_tree(workspace_dir, 'turns')
    observations = {(r['dealer_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        centre = {k: median(r[k] for r in closed) for k in TURN_KEYS}
        scale = {k: mad_scale([r[k] for r in closed], 0.03) for k in TURN_KEYS}
        design, events, weights = [], [], []
        for r in closed:
            z = _turn_covariates(r, centre, scale)
            w = recency(q, r['booked_period'], 8.0)
            last = r['sold_bucket'] if r['sold_bucket'] >= 0 else r['last_observed_bucket']
            for b in range(last + 1):
                design.append(_turn_design(b, z))
                events.append(1.0 if r['sold_bucket'] == b else 0.0)
                weights.append(w)
        width = len(design[0])
        # baseline log-log hazards from the empirical hazard per (segment, band) stratum
        beta = [0.0] * width
        for b in range(TURN_BASELINES):
            risk = sum(wv for d, wv in zip(design, weights) if d[b] == 1.0)
            fired = sum(wv for d, yv, wv in zip(design, events, weights) if d[b] == 1.0 and yv)
            rate = min(0.95, max(0.02, (fired + 1.0) / (risk + 2.0)))
            beta[b] = math.log(-math.log(1 - rate))
        objective = _turn_objective(beta, design, events, weights)
        for _ in range(TURN_ITERATIONS):
            normal = [[0.0] * (width + 1) for _ in range(width)]
            for d, yv, wv in zip(design, events, weights):
                mu, survive, h = _cloglog_hazard(sum(bi * di for bi, di in zip(beta, d)))
                dh = mu * survive
                info = wv * dh * dh / (h * (1 - h))
                score = wv * (yv - h) * dh / (h * (1 - h))
                for i in range(width):
                    di = d[i]
                    if di == 0.0:
                        continue
                    row = normal[i]
                    for j in range(width):
                        row[j] += info * di * d[j]
                    row[width] += score * di
            for i in range(TURN_BASELINES, width):
                normal[i][i] += TURN_RIDGE
                normal[i][width] -= TURN_RIDGE * beta[i]
            for i in range(width):
                normal[i][i] += 1e-8
            step = solve(normal)
            scale_factor, improved = 1.0, False
            for _ in range(12):
                candidate = [b + scale_factor * s for b, s in zip(beta, step)]
                value = _turn_objective(candidate, design, events, weights)
                if value >= objective - 1e-12:
                    beta, objective, improved = candidate, value, True
                    break
                scale_factor *= 0.5
            if not improved or max(abs(s) for s in step) * scale_factor < 1e-9:
                break
        models[q] = {'beta': beta, 'centre': centre, 'scale': scale, 'expanded_rows': len(design), 'objective': objective}
    return {'models': models, 'observations': observations}


def predict_turn_profile(fitted_object, dealer_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][dealer_id, period]
    z = _turn_covariates(x, m['centre'], m['scale'])
    survival, result = 1.0, []
    for b in range(8):
        _, _, h = _cloglog_hazard(sum(bi * di for bi, di in zip(m['beta'], _turn_design(b, z))))
        mass = survival * h
        result.append(math.floor(max(0.0, mass) * 10 ** 8) / 10 ** 8)
        survival *= 1.0 - h
    return result


# --- lane 3: sold-out-of-trust flag, distance-weighted neighbour vote with an F1 threshold ------

SOT_KEYS = ('audit_variance_rate', 'late_payoff_count', 'days_since_audit', 'cash_strain', 'insurance_lapses', 'curtailment_misses')
SOT_K = 35


def _sot_point(x, scale):
    return [x[k] / scale[k] for k in SOT_KEYS]


def _sot_vote(points, z0, franchise, exclude=None):
    distances = []
    for idx, (z, f, y, w) in enumerate(points):
        if idx == exclude:
            continue
        d = sum((a - b) ** 2 for a, b in zip(z, z0)) + (1.0 if f != franchise else 0.0)
        distances.append((d, idx, y, w))
    near = sorted(distances)[:SOT_K]
    radius = max(0.01, near[-1][0])
    num = den = 0.0
    for d, _, y, w in near:
        k = w * math.exp(-3.0 * d / radius)
        num += k * y
        den += k
    return num / den


def fit_sot_flag(workspace_dir):
    rows = read_tree(workspace_dir, 'audits')
    observations = {(r['dealer_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        scale = {k: mad_scale([r[k] for r in closed], 0.05 if k in ('audit_variance_rate', 'cash_strain') else 0.5) for k in SOT_KEYS}
        points = [(_sot_point(r, scale), r['franchise'], float(r['sot_event']), recency(q, r['booked_period'], 8.0)) for r in closed]
        recent = [i for i, r in enumerate(closed) if r['booked_period'] >= q - 6]
        posteriors = [(_sot_vote(points, points[i][0], points[i][1], exclude=i), points[i][2], points[i][3]) for i in recent]
        candidates = sorted({round(p, 6) for p, _, _ in posteriors})
        best = None
        for tau in candidates:
            tp = sum(w for p, y, w in posteriors if p >= tau and y == 1.0)
            fp = sum(w for p, y, w in posteriors if p >= tau and y == 0.0)
            fn = sum(w for p, y, w in posteriors if p < tau and y == 1.0)
            # precision-weighted F0.5: a flag commits an audit visit, so false flags cost more than misses
            value = 1.25 * tp / (1.25 * tp + 0.25 * fn + fp) if tp > 0 else 0.0
            if best is None or value >= best[0] - 1e-12:
                best = (value, tau)
        models[q] = {'points': points, 'scale': scale, 'threshold': best[1], 'fitted_fhalf': best[0], 'recent': len(recent)}
    return {'models': models, 'observations': observations}


def predict_sot_flag(fitted_object, dealer_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][dealer_id, period]
    p = _sot_vote(m['points'], _sot_point(x, m['scale']), x['franchise'])
    return int(round(p, 6) >= m['threshold'])


# --- lane 4: variance tier, proportional-odds ordinal regression ------------------------------

VARIANCE_KEYS = ('unit_count_log', 'reconciliation_lag', 'staff_turnover', 'prior_findings', 'location_count')
VARIANCE_RIDGE = 0.5
VARIANCE_ITERATIONS = 40


def _variance_covariates(x, means, sds):
    z = [(x[k] - m) / s for k, m, s in zip(VARIANCE_KEYS, means, sds)]
    stage = [1.0 if x['audit_stage'] == c else 0.0 for c in range(1, 4)]
    # staff turnover acts differently at each audit stage, and reconciliation lag saturates
    return z + stage + [z[2] * s for s in stage] + [z[1] * z[1]]


def _ordinal_probabilities(theta, eta):
    gamma = [expit(t - eta) for t in theta]
    cumulative = [0.0] + gamma + [1.0]
    return [max(1e-12, cumulative[k + 1] - cumulative[k]) for k in range(4)], gamma


def _ordinal_objective(theta, beta, design, labels, weights):
    total = 0.0
    for d, t, w in zip(design, labels, weights):
        probabilities, _ = _ordinal_probabilities(theta, sum(b * v for b, v in zip(beta, d)))
        total += w * math.log(probabilities[t])
    return total - 0.5 * VARIANCE_RIDGE * sum(b * b for b in beta)


def fit_variance_tier(workspace_dir):
    rows = read_tree(workspace_dir, 'reconciliations')
    observations = {(r['dealer_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        raw = [[r[k] for k in VARIANCE_KEYS] for r in closed]
        means = [sum(f[i] for f in raw) / len(raw) for i in range(5)]
        sds = [max(1e-6, math.sqrt(sum((f[i] - means[i]) ** 2 for f in raw) / len(raw))) for i in range(5)]
        design = [_variance_covariates(r, means, sds) for r in closed]
        labels = [tier_of(r['variance_fraction']) for r in closed]
        weights = [recency(q, r['booked_period'], 8.0) for r in closed]
        width = len(design[0])
        theta, beta = [-1.0, 0.0, 1.0], [0.0] * width
        objective = _ordinal_objective(theta, beta, design, labels, weights)
        for _ in range(VARIANCE_ITERATIONS):
            size = 3 + width
            normal = [[0.0] * (size + 1) for _ in range(size)]
            for d, t, w in zip(design, labels, weights):
                eta = sum(b * v for b, v in zip(beta, d))
                probabilities, gamma = _ordinal_probabilities(theta, eta)
                pi = probabilities[t]
                slope = [g * (1 - g) for g in gamma]
                upper = slope[t] if t < 3 else 0.0
                lower = slope[t - 1] if t > 0 else 0.0
                g = [0.0] * size
                if t < 3:
                    g[t] += upper / pi
                if t > 0:
                    g[t - 1] -= lower / pi
                for j in range(width):
                    g[3 + j] = -d[j] * (upper - lower) / pi
                for i in range(size):
                    gi = g[i]
                    if gi == 0.0:
                        continue
                    row = normal[i]
                    for j in range(size):
                        row[j] += w * gi * g[j]
                    row[size] += w * gi
            for j in range(width):
                normal[3 + j][3 + j] += VARIANCE_RIDGE
                normal[3 + j][size] -= VARIANCE_RIDGE * beta[j]
            for i in range(size):
                normal[i][i] += 1e-6
            step = solve(normal)
            scale = 1.0
            improved = False
            for _ in range(12):
                new_theta = [t + scale * s for t, s in zip(theta, step[:3])]
                new_beta = [b + scale * s for b, s in zip(beta, step[3:])]
                if new_theta[0] < new_theta[1] < new_theta[2]:
                    candidate = _ordinal_objective(new_theta, new_beta, design, labels, weights)
                    if candidate >= objective - 1e-12:
                        theta, beta, objective, improved = new_theta, new_beta, candidate, True
                        break
                scale *= 0.5
            if not improved or max(abs(s) for s in step) * scale < 1e-9:
                break
        models[q] = {'theta': theta, 'beta': beta, 'means': means, 'sds': sds, 'objective': objective}
    return {'models': models, 'observations': observations}


def predict_variance_tier(fitted_object, dealer_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][dealer_id, period]
    probabilities, _ = _ordinal_probabilities(m['theta'], sum(b * v for b, v in zip(m['beta'], _variance_covariates(x, m['means'], m['sds']))))
    return max(range(4), key=lambda k: (probabilities[k], -k))


# --- lane 5: headroom rank, mixed-effects line model with shrunk dealer intercepts -----------

HEADROOM_RIDGE = 0.3
HEADROOM_KAPPA = 5.0


def headroom_basis(r):
    phase = 2 * math.pi * r['oem_incentive_phase']
    return [1.0, r['sales_momentum'], r['inventory_days'] / 100.0, r['curtailment_backlog'], r['payoff_lag'] / 20.0,
            math.cos(phase), math.sin(phase), r['sales_momentum'] * r['curtailment_backlog'],
            math.log(r['credit_line']) - 13.0] + [1.0 if r['franchise'] == c else 0.0 for c in range(1, 4)] \
        + [1.0 if r['region'] == c else 0.0 for c in range(1, 4)]


def fit_headroom_rank(workspace_dir):
    rows = read_tree(workspace_dir, 'lines')
    observations = {(r['dealer_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        xs = [headroom_basis(r) for r in closed]
        ys = [logit(r['available_fraction']) for r in closed]
        ws = [recency(q, r['booked_period'], 8.0) for r in closed]
        width = len(xs[0])
        normal = [[sum(w * x[i] * x[j] for x, w in zip(xs, ws)) + (HEADROOM_RIDGE if i == j and i else 0.0) for j in range(width)]
                  + [sum(w * x[i] * y for x, y, w in zip(xs, ys, ws))] for i in range(width)]
        coefficients = solve(normal)
        effects = {}
        for r, x, y, w in zip(closed, xs, ys, ws):
            residual = y - sum(a * b for a, b in zip(x, coefficients))
            total = effects.setdefault(r['dealer_id'], [0.0, 0.0])
            total[0] += w * residual
            total[1] += w
        intercepts = {d: num / (den + HEADROOM_KAPPA) for d, (num, den) in effects.items()}
        models[q] = {'coefficients': coefficients, 'intercepts': intercepts, 'support': len(closed)}
    return {'models': models, 'observations': observations}


def headroom_value(fitted_object, dealer_id, period):
    """Estimated undrawn line headroom: credit line times the fitted available fraction, less outstanding and pending payoffs."""
    m = fitted_object['models'][period]
    x = fitted_object['observations'][dealer_id, period]
    fixed = sum(a * b for a, b in zip(headroom_basis(x), m['coefficients']))
    fraction = expit(fixed + m['intercepts'].get(dealer_id, 0.0))
    return x['credit_line'] * fraction - x['outstanding'] - x['pending_payoffs']


def predict_headroom_rank(fitted_object, dealer_id, period, workspace_dir):
    queries = read_rows(Path(workspace_dir) / 'queries.jsonl')
    cohort = [r['dealer_id'] for r in queries if r['period'] == period]
    if dealer_id not in cohort:
        cohort = [a for (a, q), r in fitted_object['observations'].items() if q == period and r['cohort'] == 'reference']
    cache = fitted_object.setdefault('rank_cache', {})
    key = (period, tuple(sorted(cohort)))
    if key not in cache:
        cache[key] = dense_ranks_descending({a: round(headroom_value(fitted_object, a, period), 6) for a in cohort})
    return cache[key][dealer_id]


# --- lane 6: loss reserve, hierarchical credibility with a Hill-estimated tail loading ---------

LOSS_FREQUENCY_K = 6.0
LOSS_SEVERITY_K = 4.0
LOSS_BAND_K = 10.0
LOSS_TAIL_SHARE = 0.15
LOSS_TAIL_LOAD = 0.1


def _tercile(value, cuts):
    return sum(value > c for c in cuts)


def fit_loss_reserve(workspace_dir):
    rows = read_tree(workspace_dir, 'repossessions')
    observations = {(r['dealer_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        ws = [recency(q, r['booked_period'], 8.0) for r in closed]
        cuts = {k: weighted_quantiles([r[k] for r in closed], ws, 2) for k in ('dealer_cash_score', 'market_stress')}
        global_rate = (sum(w for r, w in zip(closed, ws) if r['loss_amount'] > 0) + 1.0) / (sum(ws) + 2.0)
        positives = [(r, w) for r, w in zip(closed, ws) if r['loss_amount'] > 0]
        global_log = sum(w * math.log(r['loss_amount'] / r['exposure']) for r, w in positives) / sum(w for _, w in positives)
        bands, cells = {}, {}
        for band in range(4):
            g = [(r, w) for r, w in zip(closed, ws) if r['rating_band'] == band]
            n = sum(w for _, w in g)
            events = sum(w for r, w in g if r['loss_amount'] > 0)
            rate = (events + LOSS_BAND_K * global_rate) / (n + LOSS_BAND_K)
            pos = [(r, w) for r, w in g if r['loss_amount'] > 0]
            logs = [math.log(r['loss_amount'] / r['exposure']) for r, _ in pos]
            pw = [w for _, w in pos]
            centre = (sum(w * v for v, w in zip(logs, pw)) + LOSS_BAND_K * global_log) / (sum(pw) + LOSS_BAND_K)
            variance = sum(w * (v - centre) ** 2 for v, w in zip(logs, pw)) / sum(pw) if pw else 0.0
            rates = sorted(r['loss_amount'] / r['exposure'] for r, _ in pos)
            tail_start = int(math.floor((1 - LOSS_TAIL_SHARE) * len(rates)))
            tail = rates[tail_start:]
            threshold = rates[tail_start - 1] if tail_start > 0 else rates[0]
            hill = len(tail) / sum(math.log(v / threshold) for v in tail) if tail and threshold > 0 and sum(math.log(v / threshold) for v in tail) > 0 else 5.0
            alpha = max(1.5, hill)
            bands[band] = {'rate': rate, 'log_centre': centre, 'log_variance': variance, 'threshold': threshold, 'alpha': alpha,
                           'exceedance': sum(w for r, w in pos if r['loss_amount'] / r['exposure'] > threshold) / sum(pw) if pw else 0.0}
            for c1 in range(3):
                for c2 in range(3):
                    members = [(r, w) for r, w in g if _tercile(r['dealer_cash_score'], cuts['dealer_cash_score']) == c1
                               and _tercile(r['market_stress'], cuts['market_stress']) == c2]
                    cn = sum(w for _, w in members)
                    ce = sum(w for r, w in members if r['loss_amount'] > 0)
                    cell_rate = (ce + LOSS_FREQUENCY_K * rate) / (cn + LOSS_FREQUENCY_K)
                    cp = [(math.log(r['loss_amount'] / r['exposure']), w) for r, w in members if r['loss_amount'] > 0]
                    cell_centre = (sum(w * v for v, w in cp) + LOSS_SEVERITY_K * centre) / (sum(w for _, w in cp) + LOSS_SEVERITY_K)
                    cells[band, c1, c2] = {'rate': cell_rate, 'log_centre': cell_centre, 'support': len(members)}
        models[q] = {'cuts': cuts, 'bands': bands, 'cells': cells}
    return {'models': models, 'observations': observations}


def predict_loss_reserve(fitted_object, dealer_id, period, workspace_dir):
    m = fitted_object['models'][period]
    x = fitted_object['observations'][dealer_id, period]
    band = m['bands'][x['rating_band']]
    cell = m['cells'][x['rating_band'], _tercile(x['dealer_cash_score'], m['cuts']['dealer_cash_score']), _tercile(x['market_stress'], m['cuts']['market_stress'])]
    mean_rate = math.exp(cell['log_centre'] + 0.5 * band['log_variance'])
    tail_mean = band['threshold'] * band['alpha'] / (band['alpha'] - 1)
    expected = cell['rate'] * (mean_rate + LOSS_TAIL_LOAD * band['exceedance'] * tail_mean)
    collateral = max(0.0, 1.0 - 0.6 * min(1.0, x['collateral_coverage']))
    return round(max(0.0, x['exposure'] * expected * collateral), 2)




class Surveillance:
    """Fits every lane once and answers records on demand."""

    def __init__(self, workspace):
        self.workspace = Path(workspace)
        self.models = {lane: globals()["fit_" + lane](self.workspace) for lane in LANES}

    def record(self, dealer_id, period):
        out = {"record_id": f"{dealer_id}:p{period}"}
        for lane in LANES:
            out[lane] = globals()["predict_" + lane](self.models[lane], dealer_id, period, self.workspace)
        return out


def main(argv):
    if len(argv) != 2:
        raise SystemExit("surveillance facade needs <workspace> <output>")
    desk = Surveillance(argv[0])
    queries = read_rows(desk.workspace / "queries.jsonl")
    answers = {}
    for r in reversed(queries):
        answers[r["record_id"]] = desk.record(r["dealer_id"], r["period"])
    with open(argv[1], "w") as handle:
        for r in queries:
            handle.write(json.dumps(answers[r["record_id"]], sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
