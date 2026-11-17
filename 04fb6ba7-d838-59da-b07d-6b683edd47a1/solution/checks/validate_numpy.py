"""Independent certification of the oracle: a numpy re-implementation of the six desk methods that
shares no code with solution/estimators.py, run over the public workspace and compared with the
frozen truth lane by lane. Exact-match counts (after the published rounding) and the largest
absolute difference are recorded in solution/measurements/numpy_validation.json.

Run: PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python -B solution/checks/validate_numpy.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / 'environment/workspace'
FIT = (16, 20)
U = np.array([15, 30, 45, 60, 90, 120, 180, 270], dtype=float)


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
    return {(r['obligor_id'], r['period']): r for r in view_rows if r.get('kind') == 'snapshot'}


def rec(q, booked, tau):
    return np.exp(-(q - 1 - np.asarray(booked, dtype=float)) / tau)


def mad(v, floor):
    v = np.asarray(v, dtype=float)
    return max(floor, float(np.median(np.abs(v - np.median(v)))))


def sig(x):
    return 1 / (1 + np.exp(-x))


def lo(p):
    return np.log(p / (1 - p))


# lane 1
def dilution(queries):
    data = rows('dilution')
    S = snaps(data)
    keys = ('promo_intensity', 'return_propensity', 'pricing_dispute_index', 'invoice_size_log', 'terms_days')
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        for mix in range(4):
            g = [r for r in cl if r['product_mix'] == mix]
            centre = np.array([np.median([r[k] for r in g]) for k in keys])
            scale = np.array([mad([r[k] for r in g], 0.05 if k != 'terms_days' else 5.0) for k in keys])
            Z = (np.array([[r[k] for k in keys] for r in g]) - centre) / scale
            C = np.array([[r['channel'] == 1, r['channel'] == 2] for r in g], dtype=float)
            y = lo(np.array([r['dilution_ratio'] for r in g]))
            w = rec(q, [r['booked_period'] for r in g], 9.0)
            order = sorted(range(len(g)), key=lambda i: g[i]['case_id'])[:60]

            def fit_at(z0, h, exclude=None):
                d = np.sqrt(((Z - z0) ** 2).sum(1))
                k = w * np.where(d / h < 1, (1 - (d / h) ** 3) ** 3, 0.0)
                if exclude is not None:
                    k = k.copy(); k[exclude] = 0.0
                X = np.column_stack([np.ones(len(g)), Z - z0, C])
                A = (X * k[:, None]).T @ X
                A[np.arange(1, 8), np.arange(1, 8)] += 0.05
                if A[0, 0] < 1e-9:
                    return None
                return float(np.linalg.solve(A, (X * k[:, None]).T @ y)[0])

            best = min((sum((y[i] - (fit_at(Z[i], h, i) or 0.0)) ** 2 for i in order), h) for h in (0.9, 1.3, 1.8))
            h = best[1]
            for r in queries:
                if r['period'] != q:
                    continue
                x = S[r['obligor_id'], q]
                if x['product_mix'] != mix:
                    continue
                z0 = (np.array([x[k] for k in keys]) - centre) / scale
                f = fit_at(z0, h)
                if f is None:
                    f = fit_at(z0, 3 * h)
                ratio = min(0.6, max(0.001, float(sig(f if f is not None else -3.0))))
                out[r['record_id']] = round(x['open_balance'] * ratio, 2)
    return out


# lane 2
def km(rs, w):
    s, curve = 1.0, []
    for b in range(8):
        risk = sum(wi for r, wi in zip(rs, w) if r['last_observed_bucket'] >= b and (r['paid_bucket'] < 0 or r['paid_bucket'] >= b))
        ev = sum(wi for r, wi in zip(rs, w) if r['paid_bucket'] == b)
        s *= 1 - min(0.98, ev / risk if risk > 0 else 0.0)
        curve.append(s)
    return np.array(curve)


def rmean(curve):
    return float(np.sum(np.concatenate([[1.0], curve[:-1]]) * np.diff(np.concatenate([[0.0], U]))))


def surv_at(curve, t):
    knots = np.concatenate([[0.0], U]); vals = np.log(np.concatenate([[1.0], np.maximum(1e-9, curve)]))
    if t <= 0:
        return 1.0
    if t <= knots[-1]:
        return float(np.exp(np.interp(t, knots, vals)))
    slope = (vals[-1] - vals[-2]) / (knots[-1] - knots[-2])
    return float(np.exp(vals[-1] + slope * (t - knots[-1])))


def collection(queries):
    data = rows('collections'); S = snaps(data)
    keys = ('past_due_share', 'dispute_share', 'payment_regularity', 'remittance_lag')
    band = {30: 0, 45: 1, 60: 2, 90: 3}
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        w = rec(q, [r['booked_period'] for r in cl], 8.0)
        scale = {k: mad([r[k] for r in cl], 0.03) for k in keys}
        cells = {}
        for region in range(4):
            pool = [i for i, r in enumerate(cl) if r['region'] == region]
            pc = km([cl[i] for i in pool], [w[i] for i in pool])
            for b_ in range(4):
                idx = [i for i in pool if band[cl[i]['terms_days']] == b_]
                s, curve, prev = 1.0, [], 1.0
                for b in range(8):
                    risk = sum(w[i] for i in idx if cl[i]['last_observed_bucket'] >= b and (cl[i]['paid_bucket'] < 0 or cl[i]['paid_bucket'] >= b))
                    ev = sum(w[i] for i in idx if cl[i]['paid_bucket'] == b)
                    ph = 1 - pc[b] / prev if prev > 0 else 0.0
                    prev = pc[b]
                    s *= 1 - min(0.98, (ev + 4.0 * ph) / (risk + 4.0))
                    curve.append(s)
                cells[region, b_] = np.array(curve)
        F = np.array([[r[k] / scale[k] for k in keys] for r in cl]); R = np.array([r['region'] for r in cl]); B = np.array([band[r['terms_days']] for r in cl])
        for r in queries:
            if r['period'] != q:
                continue
            x = S[r['obligor_id'], q]
            d = ((F - np.array([x[k] / scale[k] for k in keys])) ** 2).sum(1) + 1.0 * (R != x['region']) + 0.5 * np.abs(B - band[x['terms_days']])
            order = sorted(range(len(cl)), key=lambda i: (d[i], cl[i]['case_id']))[:30]
            radius = max(0.01, d[order[-1]])
            k = np.array([math.exp(-4.0 * d[i] / radius) * w[i] for i in order])
            curve = km([cl[i] for i in order], k)
            n_eff = k.sum() ** 2 / (k ** 2).sum()
            base = cells[x['region'], band[x['terms_days']]]
            a = min(3.5, max(0.3, (rmean(base) / max(1.0, rmean(curve))) ** (n_eff / (n_eff + 2.0))))
            prev, prof = 1.0, []
            for u in U:
                s = surv_at(base, a * u); prof.append(math.floor(max(0.0, prev - s) * 1e8) / 1e8); prev = s
            out[r['record_id']] = prof
    return out


# lane 3
def dispute(queries):
    data = rows('disputes'); S = snaps(data)

    def raw(x):
        return [x['open_dispute_count'], x['invoice_error_rate'], x['po_mismatch_rate'], math.log1p(x['days_since_last_dispute']), x['contact_responsiveness'],
                x['invoice_error_rate'] * x['po_mismatch_rate'], x['open_dispute_count'] * (1 - x['contact_responsiveness'])]

    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        Rw = np.array([raw(r) for r in cl]); mu, sd = Rw.mean(0), np.maximum(1e-6, Rw.std(0))
        X = np.column_stack([np.ones(len(cl)), (Rw - mu) / sd, np.array([[r['contract_type'] == c for c in (1, 2, 3)] for r in cl], dtype=float)])
        y = np.array([r['escalated'] for r in cl], dtype=float); w = rec(q, [r['booked_period'] for r in cl], 8.0)
        beta = np.zeros(X.shape[1]); ridge = np.ones(X.shape[1]); ridge[0] = 0
        for _ in range(30):
            p = sig(X @ beta)
            grad = X.T @ (w * (y - p)) - ridge * beta
            H = (X * (w * p * (1 - p))[:, None]).T @ X + np.diag(ridge)
            step = np.linalg.solve(H, grad); beta = beta + step
            if np.abs(step).max() < 1e-8:
                break
        recent = np.array([r['booked_period'] >= q - 6 for r in cl])
        prev = float((y[recent] * w[recent]).sum() / w[recent].sum())
        pr = sig(X[recent] @ beta); wr = w[recent]
        order = np.argsort(-pr, kind='stable')
        # replicate the python sort on (p, w) descending tuples: sort by p desc then w desc
        order = sorted(range(len(pr)), key=lambda i: (-pr[i], -wr[i]))
        cum, thr = 0.0, pr[order[0]]
        for i in order:
            cum += wr[i]; thr = pr[i]
            if cum >= prev * wr.sum():
                break
        for r in queries:
            if r['period'] != q:
                continue
            x = S[r['obligor_id'], q]
            xv = np.concatenate([[1.0], (np.array(raw(x)) - mu) / sd, [float(x['contract_type'] == c) for c in (1, 2, 3)]])
            out[r['record_id']] = int(sig(xv @ beta) >= thr)
    return out


# lane 4
def recovery(queries):
    data = rows('delinquencies'); S = snaps(data)
    keys = ('days_past_due', 'secured_share', 'guarantor_strength', 'prior_cures', 'exposure_log')
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        scores = {}
        for stage in range(4):
            g = [r for r in cl if r['legal_stage'] == stage]
            scale = np.array([mad([r[k] for r in g], 0.02) for k in keys])
            Z = np.array([[r[k] for k in keys] for r in g]) / scale; y = np.array([r['recovered_fraction'] for r in g]); w = rec(q, [r['booked_period'] for r in g], 7.0)
            prior = float((y * w).sum() / w.sum())
            order = sorted(range(len(g)), key=lambda i: g[i]['case_id'])[:80]

            def nw(z0, h, exclude=None):
                k = w * np.exp(-((Z - z0) ** 2).sum(1) / (2 * h * h))
                if exclude is not None:
                    k = k.copy(); k[exclude] = 0.0
                return float((3.0 * prior + (k * y).sum()) / (3.0 + k.sum()))

            h = min((sum((y[i] - nw(Z[i], h, i)) ** 2 for i in order), h) for h in (0.6, 0.9, 1.3, 1.9))[1]
            cohort = sorted(a for (a, p), r in S.items() if p == q and r['legal_stage'] == stage)
            ordered = sorted(cohort, key=lambda a: (nw(np.array([S[a, q][k] for k in keys]) / scale, h), a))
            for pos, a in enumerate(ordered):
                scores[a] = min(3, 4 * pos // len(ordered))
        for r in queries:
            if r['period'] == q:
                out[r['record_id']] = scores[r['obligor_id']]
    return out


# lane 5
def availability(queries):
    data = rows('borrowing_base'); S = snaps(data)
    keys = ('ineligible_share', 'concentration_index', 'cross_aged_share', 'insurance_coverage', 'dilution_history', 'seasonality_phase')

    def basis(r):
        ph = 2 * math.pi * r['seasonality_phase']
        return [1.0, r['ineligible_share'], r['concentration_index'], r['cross_aged_share'], r['insurance_coverage'], math.cos(ph), math.sin(ph),
                r['ineligible_share'] * r['concentration_index'], r['dilution_history'], math.log(r['gross_receivables']) - 12.5,
                math.sin(3.0 * r['concentration_index'] + 4.0 * r['cross_aged_share'])]

    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        scale = {}
        for k in keys:
            v = sorted(r[k] for r in cl); scale[k] = max(0.02, v[3 * len(v) // 4] - v[len(v) // 4])
        bands = {}
        for b in range(4):
            g = [r for r in cl if r['advance_band'] == b]
            X = np.array([basis(r) for r in g]); y = lo(np.array([r['availability_ratio'] for r in g])); w = rec(q, [r['booked_period'] for r in g], 8.0)
            A = (X * w[:, None]).T @ X; A[np.arange(1, 11), np.arange(1, 11)] += 0.2
            coef = np.linalg.solve(A, (X * w[:, None]).T @ y)
            res = y - X @ coef; centre = float(np.median(res)); spread = max(0.01, float(np.median(np.abs(res - centre))))
            bands[b] = (g, coef, res, w, centre, spread, np.array([[r[k] / scale[k] for k in keys] for r in g]))
        cohort = [r['obligor_id'] for r in queries if r['period'] == q]
        nets = {}
        for a in cohort:
            x = S[a, q]; g, coef, res, w, centre, spread, F = bands[x['advance_band']]
            d = ((F - np.array([x[k] / scale[k] for k in keys])) ** 2).sum(1)
            order = sorted(range(len(g)), key=lambda i: (d[i], g[i]['case_id']))[:40]
            radius = max(0.01, d[order[-1]])
            num, den = 6.0 * centre, 6.0
            for i in order:
                k = math.exp(-2.0 * d[i] / radius) * w[i]
                num += k * min(centre + 3 * spread, max(centre - 3 * spread, res[i])); den += k
            nets[a] = round(x['gross_receivables'] * float(sig(np.array(basis(x)) @ coef + num / den)) - x['reserve_holdback'] - x['drawn_balance'], 6)
        rank = {v: i + 1 for i, v in enumerate(sorted(set(nets.values()), reverse=True))}
        for a in cohort:
            out[f'{a}:p{q}'] = rank[nets[a]]
    return out


# lane 6
def loss(queries):
    data = rows('writeoffs'); S = snaps(data)
    keys = ('payment_score', 'sector_stress', 'years_relationship', 'credit_limit_utilisation')
    out = {}
    for q in FIT:
        cl = closed_at(data, q)
        scale = {k: mad([r[k] for r in cl], 0.02) for k in keys}; scale['exposure_log'] = mad([math.log(r['exposure']) for r in cl], 0.05)
        for b in range(4):
            g = [r for r in cl if r['rating_band'] == b]
            pos = np.array([r['loss_amount'] / r['exposure'] for r in g if r['loss_amount'] > 0])
            logs = np.log(pos); centre, var = float(logs.mean()), float(((logs - logs.mean()) ** 2).mean())
            tail = float(np.sort(pos)[int(0.85 * (len(pos) - 1))]); exc = float((pos > tail).mean()); rate = (len(pos) + 1) / (len(g) + 2)
            w = rec(q, [r['booked_period'] for r in g], 8.0)
            F = np.array([[r[k] / scale[k] for k in keys] + [math.log(r['exposure']) / scale['exposure_log']] for r in g])
            for r in queries:
                if r['period'] != q:
                    continue
                x = S[r['obligor_id'], q]
                if x['rating_band'] != b:
                    continue
                xv = np.array([x[k] / scale[k] for k in keys] + [math.log(x['exposure']) / scale['exposure_log']])
                d = np.minimum(25.0, (F - xv) ** 2).sum(1)
                order = sorted(range(len(g)), key=lambda i: (d[i], g[i]['case_id']))[:48]
                radius = max(0.01, d[order[-1]])
                cnt, ev, ls, sn, ex = 5.0, 5.0 * rate, 4.0 * centre, 4.0, 4.0 * exc
                for i in order:
                    k = math.exp(-2.0 * d[i] / radius) * w[i]; cnt += k
                    if g[i]['loss_amount'] > 0:
                        rt = g[i]['loss_amount'] / g[i]['exposure']; ev += k; sn += k; ls += k * math.log(rt); ex += k * (rt > tail)
                expected = ev / cnt * math.exp(ls / sn + 0.3 * var) + 0.2 * tail * ex / sn
                out[r['record_id']] = round(max(0.0, x['exposure'] * expected * (1 - x['insured_share'])), 2)
    return out


def main():
    queries = [json.loads(l) for l in open(W / 'queries.jsonl')]
    truth = {r['record_id']: r for r in (json.loads(l) for l in open(ROOT / 'tests/hidden/truth.jsonl'))}
    results = {}
    for lane, fn in (('dilution_reserve', dilution), ('collection_profile', collection), ('dispute_flag', dispute),
                     ('recovery_tier', recovery), ('availability_rank', availability), ('loss_reserve', loss)):
        pred = fn(queries)
        exact = sum(pred[k] == truth[k][lane] for k in truth)
        if lane == 'collection_profile':
            diff = max(max(abs(a - b) for a, b in zip(pred[k], truth[k][lane])) for k in truth)
        else:
            diff = max(abs(pred[k] - truth[k][lane]) for k in truth)
        results[lane] = {'exact_matches': int(exact), 'records': len(truth), 'max_abs_difference': float(diff)}
        print(lane, results[lane], flush=True)
    (ROOT / 'solution/measurements/numpy_validation.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
