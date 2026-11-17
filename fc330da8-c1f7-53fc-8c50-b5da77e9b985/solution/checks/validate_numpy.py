"""Independent certification of the oracle: a numpy re-implementation of the six desk methods that
shares no code with solution/estimators.py, run over the public workspace and compared with the
frozen truth lane by lane. Exact-match counts (after the published rounding) and the largest
absolute difference are recorded in solution/measurements/numpy_validation.json. Vectorised sums
differ from the oracle's sequential sums at floating-point precision, so the continuous lanes are
certified to a stated tolerance and the discrete lanes exactly.

Run: PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python -B solution/checks/validate_numpy.py
"""
import json
import math
import sys
from bisect import bisect_right
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / 'environment/workspace'
FIT = (16, 20)
CUTS = (0.02, 0.05, 0.10)


def rows(view):
    out = []
    for p in sorted((W / view).glob('*.jsonl'), key=lambda p: (len(p.stem), p.stem)):
        out += [json.loads(l) for l in open(p) if l.strip()]
    return out


def closed_at(view_rows, q):
    out = []
    for r in view_rows:
        if r.get('kind') != 'closed' or r['booked_period'] >= q:
            continue
        if 'restated_period' in r and r['restated_period'] >= q:
            r = {**r, **r['as_booked']}
        out.append(r)
    return out


def snaps(view_rows):
    return {(r['dealer_id'], r['period']): r for r in view_rows if r.get('kind') == 'snapshot'}


def rec(q, booked, tau):
    return np.exp(-(q - 1 - np.asarray(booked, dtype=float)) / tau)


def mad(v, floor):
    v = np.asarray(v, dtype=float)
    return max(floor, float(np.median(np.abs(v - np.median(v)))))


def sig(x):
    x = np.asarray(x, dtype=float)
    return np.where(x > -700, 1 / (1 + np.exp(-np.clip(x, -700, 700))), 0.0)


def lo(p):
    return np.log(p / (1 - p))


def wquant(values, weights, count):
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    total = float(np.sum(weights))
    knots, cum, k = [], 0.0, 1
    for i in order:
        cum += weights[i]
        while k <= count and cum >= total * k / (count + 1):
            knots.append(values[i])
            k += 1
    return sorted(set(knots))


def onehot(value, count):
    return [float(value == c) for c in range(1, count)]


# lane 1: boosted stumps
def aging(queries):
    data = rows('aging'); S = snaps(data)
    keys = ('aged_share', 'days_supply', 'model_year_age', 'demand_index', 'incentive_intensity', 'price_volatility')

    def cols(x):
        return [x[k] for k in keys] + onehot(x['segment'], 4) + onehot(x['franchise'], 4)

    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        X = np.array([cols(r) for r in cl]); y = lo(np.array([r['haircut_ratio'] for r in cl])); w = rec(q, [r['booked_period'] for r in cl], 9.0)
        n, width = X.shape
        f0 = float(np.sum(w * y) / np.sum(w)); F = np.full(n, f0)
        orders = [sorted(range(n), key=lambda i: (X[i, j], i)) for j in range(width)]
        knots = [wquant(X[:, j].tolist(), w, 12) if j < len(keys) else [0.5] for j in range(width)]
        stumps = []
        for _ in range(80):
            r = y - F
            best = None
            for j in range(width):
                o = orders[j]; vals = X[o, j]
                pw = np.concatenate([[0.0], np.cumsum(w[o])]); pr = np.concatenate([[0.0], np.cumsum((w * r)[o])])
                for t in knots[j]:
                    left = bisect_right(vals.tolist(), t)
                    if left == 0 or left == n:
                        continue
                    wl, rl = pw[left], pr[left]; wr, rr = pw[-1] - wl, pr[-1] - rl
                    cl_, cr_ = rl / (wl + 1.0), rr / (wr + 1.0)
                    gain = 2 * cl_ * rl - cl_ * cl_ * wl + 2 * cr_ * rr - cr_ * cr_ * wr
                    if best is None or gain > best[0]:
                        best = (gain, j, t, cl_, cr_)
            if best is None:
                break
            _, j, t, cl_, cr_ = best
            stumps.append((j, t, cl_, cr_))
            F = F + 0.1 * np.where(X[:, j] <= t, cl_, cr_)
        for rq in queries:
            if rq['period'] != q:
                continue
            x = S[rq['dealer_id'], q]; c = cols(x)
            v = f0 + sum(0.1 * (a if c[j] <= t else b) for j, t, a, b in stumps)
            ratio = min(0.5, max(0.002, float(sig(v))))
            out[rq['record_id']] = round(x['floored_balance'] * x['aged_share'] * ratio, 2)
    return out


# lane 2: cloglog hazard
def turns(queries):
    data = rows('turns'); S = snaps(data)
    keys = ('lot_velocity', 'demand_index', 'pricing_discipline', 'marketing_spend_log', 'stock_age_mix')
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        centre = {k: float(np.median([r[k] for r in cl])) for k in keys}
        scale = {k: mad([r[k] for r in cl], 0.03) for k in keys}

        def cov(x):
            return [(x[k] - centre[k]) / scale[k] for k in keys] + onehot(x['region'], 4)

        def design(b, z, segment):
            base = [0.0] * 32; base[segment * 8 + b] = 1.0
            return base + z + [z[4] if b >= 4 else 0.0]

        D, E, Wt = [], [], []
        for r in cl:
            z = cov(r); w = math.exp(-(q - 1 - r['booked_period']) / 8.0)
            last = r['sold_bucket'] if r['sold_bucket'] >= 0 else r['last_observed_bucket']
            for b in range(last + 1):
                D.append(design(b, z, r['segment'])); E.append(1.0 if r['sold_bucket'] == b else 0.0); Wt.append(w)
        D, E, Wt = np.array(D), np.array(E), np.array(Wt)
        width = D.shape[1]
        beta = np.zeros(width)
        for b in range(32):
            mask = D[:, b] == 1.0
            rate = min(0.95, max(0.02, (float((Wt * E)[mask].sum()) + 1.0) / (float(Wt[mask].sum()) + 2.0)))
            beta[b] = math.log(-math.log(1 - rate))
        ridge = np.zeros(width); ridge[32:] = 0.5

        def hazard(eta):
            eta = np.clip(eta, -30.0, 3.0); mu = np.exp(eta); s = np.exp(-mu)
            return mu, s, np.clip(1.0 - s, 1e-12, 1 - 1e-12)

        def objective(bv):
            _, _, h = hazard(D @ bv)
            return float(np.sum(Wt * np.where(E > 0, np.log(h), np.log(1 - h)))) - 0.5 * float(np.sum(ridge * bv * bv))

        obj = objective(beta)
        for _ in range(18):
            mu, s, h = hazard(D @ beta); dh = mu * s
            info = Wt * dh * dh / (h * (1 - h)); score = Wt * (E - h) * dh / (h * (1 - h))
            H = (D * info[:, None]).T @ D + np.diag(ridge) + 1e-8 * np.eye(width)
            g = D.T @ score - ridge * beta
            step = np.linalg.solve(H, g)
            sf, improved = 1.0, False
            for _ in range(12):
                cand = beta + sf * step; val = objective(cand)
                if val >= obj - 1e-12:
                    beta, obj, improved = cand, val, True
                    break
                sf *= 0.5
            if not improved or float(np.abs(step).max()) * sf < 1e-9:
                break
        for rq in queries:
            if rq['period'] != q:
                continue
            x = S[rq['dealer_id'], q]; z = cov(x)
            surv, prof = 1.0, []
            for b in range(8):
                _, _, h = hazard(np.array([float(np.dot(beta, design(b, z, x['segment'])))]))
                h = float(h[0]); prof.append(math.floor(max(0.0, surv * h) * 1e8) / 1e8); surv *= 1 - h
            out[rq['record_id']] = prof
    return out


# lane 3: neighbour vote
def sot(queries):
    data = rows('audits'); S = snaps(data)
    keys = ('audit_variance_rate', 'late_payoff_count', 'days_since_audit', 'cash_strain', 'insurance_lapses', 'curtailment_misses')
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        scale = {k: mad([r[k] for r in cl], 0.05 if k in ('audit_variance_rate', 'cash_strain') else 0.5) for k in keys}
        Z = np.array([[r[k] / scale[k] for k in keys] for r in cl]); Fr = np.array([r['franchise'] for r in cl])
        Y = np.array([float(r['sot_event']) for r in cl]); Wt = rec(q, [r['booked_period'] for r in cl], 8.0)

        def vote(z0, fr, exclude=None):
            d = ((Z - z0) ** 2).sum(1) + (Fr != fr) * 1.0
            idx = np.arange(len(cl))
            if exclude is not None:
                keep = idx != exclude; d, idx = d[keep], idx[keep]
            order = np.lexsort((idx, d))[:35]
            radius = max(0.01, float(d[order[-1]]))
            k = Wt[idx[order]] * np.exp(-3.0 * d[order] / radius)
            return float(np.sum(k * Y[idx[order]]) / np.sum(k))

        recent = [i for i, r in enumerate(cl) if r['booked_period'] >= q - 6]
        post = [(vote(Z[i], Fr[i], exclude=i), Y[i], Wt[i]) for i in recent]
        best = None
        for tau in sorted({round(p, 6) for p, _, _ in post}):
            tp = sum(w for p, y, w in post if p >= tau and y == 1.0); fp = sum(w for p, y, w in post if p >= tau and y == 0.0); fn = sum(w for p, y, w in post if p < tau and y == 1.0)
            value = 1.25 * tp / (1.25 * tp + 0.25 * fn + fp) if tp > 0 else 0.0
            if best is None or value >= best[0] - 1e-12:
                best = (value, tau)
        for rq in queries:
            if rq['period'] != q:
                continue
            x = S[rq['dealer_id'], q]
            out[rq['record_id']] = int(round(vote(np.array([x[k] / scale[k] for k in keys]), x['franchise']), 6) >= best[1])
    return out


# lane 4: proportional odds
def variance(queries):
    data = rows('reconciliations'); S = snaps(data)
    keys = ('unit_count_log', 'reconciliation_lag', 'staff_turnover', 'prior_findings', 'location_count')
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        R = np.array([[r[k] for k in keys] for r in cl]); mu, sd = R.mean(0), np.maximum(1e-6, R.std(0))

        def vrow(z, stage):
            s = onehot(stage, 4)
            return list(z) + s + [z[2] * v for v in s] + [z[1] * z[1]]

        X = np.array([vrow((np.array([r[k] for k in keys]) - mu) / sd, r['audit_stage']) for r in cl])
        T = np.array([sum(r['variance_fraction'] > c for c in CUTS) for r in cl]); Wt = rec(q, [r['booked_period'] for r in cl], 8.0)
        n, width = X.shape
        theta, beta = np.array([-1.0, 0.0, 1.0]), np.zeros(width)

        def probs(th, eta):
            gamma = sig(th[None, :] - eta[:, None])
            cum = np.column_stack([np.zeros(len(eta)), gamma, np.ones(len(eta))])
            return np.maximum(1e-12, cum[:, 1:] - cum[:, :-1]), gamma

        def objective(th, bv):
            P, _ = probs(th, X @ bv)
            return float(np.sum(Wt * np.log(P[np.arange(n), T]))) - 0.25 * float(np.sum(bv * bv))

        obj = objective(theta, beta)
        for _ in range(40):
            P, gamma = probs(theta, X @ beta); pi = P[np.arange(n), T]; slope = gamma * (1 - gamma)
            upper = np.where(T < 3, slope[np.arange(n), np.minimum(T, 2)], 0.0)
            lower = np.where(T > 0, slope[np.arange(n), np.maximum(T - 1, 0)], 0.0)
            G = np.zeros((n, 3 + width))
            for i in range(n):
                if T[i] < 3:
                    G[i, T[i]] += upper[i] / pi[i]
                if T[i] > 0:
                    G[i, T[i] - 1] -= lower[i] / pi[i]
            G[:, 3:] = -X * ((upper - lower) / pi)[:, None]
            H = (G * Wt[:, None]).T @ G; g = G.T @ Wt
            H[np.arange(3, 3 + width), np.arange(3, 3 + width)] += 0.5; g[3:] -= 0.5 * beta
            H += 1e-6 * np.eye(3 + width)
            step = np.linalg.solve(H, g)
            sf, improved = 1.0, False
            for _ in range(12):
                nt, nb = theta + sf * step[:3], beta + sf * step[3:]
                if nt[0] < nt[1] < nt[2]:
                    val = objective(nt, nb)
                    if val >= obj - 1e-12:
                        theta, beta, obj, improved = nt, nb, val, True
                        break
                sf *= 0.5
            if not improved or float(np.abs(step).max()) * sf < 1e-9:
                break
        for rq in queries:
            if rq['period'] != q:
                continue
            x = S[rq['dealer_id'], q]
            xv = np.array(vrow((np.array([x[k] for k in keys]) - mu) / sd, x['audit_stage']))
            P, _ = probs(theta, np.array([float(xv @ beta)]))
            p = P[0]
            out[rq['record_id']] = int(max(range(4), key=lambda k: (p[k], -k)))
    return out


# lane 5: mixed-effects line model
def headroom(queries):
    data = rows('lines'); S = snaps(data)

    def basis(r):
        ph = 2 * math.pi * r['oem_incentive_phase']
        return [1.0, r['sales_momentum'], r['inventory_days'] / 100.0, r['curtailment_backlog'], r['payoff_lag'] / 20.0, math.cos(ph), math.sin(ph),
                r['sales_momentum'] * r['curtailment_backlog'], math.log(r['credit_line']) - 13.0] + onehot(r['franchise'], 4) + onehot(r['region'], 4)

    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        X = np.array([basis(r) for r in cl]); y = lo(np.array([r['available_fraction'] for r in cl])); w = rec(q, [r['booked_period'] for r in cl], 8.0)
        A = (X * w[:, None]).T @ X; A[np.arange(1, X.shape[1]), np.arange(1, X.shape[1])] += 0.3
        coef = np.linalg.solve(A, (X * w[:, None]).T @ y)
        res = y - X @ coef
        num, den = {}, {}
        for r, e, wi in zip(cl, res, w):
            num[r['dealer_id']] = num.get(r['dealer_id'], 0.0) + wi * e; den[r['dealer_id']] = den.get(r['dealer_id'], 0.0) + wi
        cohort = [r['dealer_id'] for r in queries if r['period'] == q]
        values = {}
        for a in cohort:
            x = S[a, q]
            u = num.get(a, 0.0) / (den.get(a, 0.0) + 5.0)
            values[a] = round(x['credit_line'] * float(sig(float(np.dot(basis(x), coef)) + u)) - x['outstanding'] - x['pending_payoffs'], 6)
        rank = {v: i + 1 for i, v in enumerate(sorted(set(values.values()), reverse=True))}
        for a in cohort:
            out[f'{a}:p{q}'] = rank[values[a]]
    return out


# lane 6: hierarchical credibility
def loss(queries):
    data = rows('repossessions'); S = snaps(data)
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        w = rec(q, [r['booked_period'] for r in cl], 8.0)
        cuts = {k: wquant([r[k] for r in cl], w, 2) for k in ('dealer_cash_score', 'market_stress')}
        terc = lambda v, c: sum(v > x for x in c)
        is_pos = np.array([r['loss_amount'] > 0 for r in cl])
        g_rate = (float(w[is_pos].sum()) + 1.0) / (float(w.sum()) + 2.0)
        lr = np.array([math.log(r['loss_amount'] / r['exposure']) if r['loss_amount'] > 0 else 0.0 for r in cl])
        g_log = float((w * lr)[is_pos].sum() / w[is_pos].sum())
        band_info, cell_info = {}, {}
        for b in range(4):
            m = np.array([r['rating_band'] == b for r in cl])
            n_ = float(w[m].sum()); ev = float(w[m & is_pos].sum())
            rate = (ev + 10.0 * g_rate) / (n_ + 10.0)
            pw = w[m & is_pos]; logs = lr[m & is_pos]
            centre = (float((pw * logs).sum()) + 10.0 * g_log) / (float(pw.sum()) + 10.0)
            var = float((pw * (logs - centre) ** 2).sum() / pw.sum()) if len(pw) else 0.0
            rates = np.sort(np.exp(logs))
            start = int(math.floor(0.85 * len(rates))); tail = rates[start:]; thr = rates[start - 1] if start > 0 else rates[0]
            lsum = float(np.log(tail / thr).sum()) if len(tail) and thr > 0 else 0.0
            alpha = max(1.5, len(tail) / lsum if lsum > 0 else 5.0)
            exc = float(pw[np.exp(logs) > thr].sum() / pw.sum()) if len(pw) else 0.0
            band_info[b] = (rate, centre, var, thr, alpha, exc)
            for c1 in range(3):
                for c2 in range(3):
                    mm = m & np.array([terc(r['dealer_cash_score'], cuts['dealer_cash_score']) == c1 and terc(r['market_stress'], cuts['market_stress']) == c2 for r in cl])
                    cn = float(w[mm].sum()); ce = float(w[mm & is_pos].sum())
                    cell_rate = (ce + 6.0 * rate) / (cn + 6.0)
                    cpw = w[mm & is_pos]; clog = lr[mm & is_pos]
                    cell_centre = (float((cpw * clog).sum()) + 4.0 * centre) / (float(cpw.sum()) + 4.0)
                    cell_info[b, c1, c2] = (cell_rate, cell_centre)
        for rq in queries:
            if rq['period'] != q:
                continue
            x = S[rq['dealer_id'], q]
            rate, centre, var, thr, alpha, exc = band_info[x['rating_band']]
            cell_rate, cell_centre = cell_info[x['rating_band'], terc(x['dealer_cash_score'], cuts['dealer_cash_score']), terc(x['market_stress'], cuts['market_stress'])]
            expected = cell_rate * (math.exp(cell_centre + 0.5 * var) + 0.1 * exc * thr * alpha / (alpha - 1))
            collateral = max(0.0, 1.0 - 0.6 * min(1.0, x['collateral_coverage']))
            out[rq['record_id']] = round(max(0.0, x['exposure'] * expected * collateral), 2)
    return out


def main():
    queries = [json.loads(l) for l in open(W / 'queries.jsonl')]
    truth = {r['record_id']: r for r in (json.loads(l) for l in open(ROOT / 'tests/hidden/truth.jsonl'))}
    tolerance = {'aging_reserve': 0.01, 'turn_profile': 1e-6, 'sot_flag': 0, 'variance_tier': 0, 'headroom_rank': 0, 'loss_reserve': 0.01}
    results = {}
    for lane, fn in (('aging_reserve', aging), ('turn_profile', turns), ('sot_flag', sot), ('variance_tier', variance), ('headroom_rank', headroom), ('loss_reserve', loss)):
        pred = fn(queries)
        if lane == 'turn_profile':
            diff = max(max(abs(a - b) for a, b in zip(pred[k], truth[k][lane])) for k in truth)
        else:
            diff = max(abs(pred[k] - truth[k][lane]) for k in truth)
        exact = sum(pred[k] == truth[k][lane] for k in truth)
        within = sum((max(abs(a - b) for a, b in zip(pred[k], truth[k][lane])) if lane == 'turn_profile' else abs(pred[k] - truth[k][lane])) <= tolerance[lane] for k in truth)
        results[lane] = {'exact_matches': int(exact), 'within_tolerance': int(within), 'tolerance': tolerance[lane], 'records': len(truth), 'max_abs_difference': float(diff)}
        print(lane, results[lane], flush=True)
    (ROOT / 'solution/measurements/numpy_validation.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
