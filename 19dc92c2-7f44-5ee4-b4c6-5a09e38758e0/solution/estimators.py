"""Judge-private, independent fitted methods for the NAV oversight desk.

Each lane fits its own ledger. Shared helpers implement transport, linear algebra
and ordering only; no lane consumes another lane's labels or fitted state.
Closed rows enter strictly before the review period, at their then-booked values.
"""
import argparse
import json
from pathlib import Path

import numpy as np

LANES = ('nav_break_magnitude', 'fee_accrual_profile', 'restatement_flag',
         'pricing_source_tier', 'oversight_rank', 'expense_reserve')
VIEWS = ('positions', 'accruals', 'corporate_actions', 'prices', 'flows', 'expenses')
KEYS = (
    ('unreconciled_share', 'fx_gap_bps', 'stale_position_share', 'turnover', 'cash_gap_bps', 'class_count'),
    ('management_rate_bps', 'performance_rate', 'positive_return', 'nav_log', 'invoice_age_days', 'share_class_count'),
    ('unprocessed_count', 'late_notice_share', 'tax_mismatch_share', 'days_since_review', 'control_completion', 'complexity'),
    ('stale_days', 'source_dispersion_bps', 'exchange_coverage', 'independent_sources', 'illiquid_share', 'quote_age_hours'),
    ('subscription_share', 'redemption_share', 'unmatched_cash_share', 'settlement_delay_days', 'cycle_phase', 'leverage'),
    ('invoice_error_share', 'vendor_stress', 'relationship_years', 'budget_utilisation', 'nav_log', 'waiver_share'))
TARGETS = ('break_bps', 'component_amounts', 'reissued', 'reliability', 'review_hours', 'overrun_amount')
FIT_PERIODS = (8, 10, 12, 16, 20)


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def read_tree(workspace, name):
    return [r for p in sorted((Path(workspace) / name).glob('*.jsonl')) for r in read_rows(p)]


def asof(rows, q):
    return [dict(r, **r.get('as_booked', {})) if r.get('restated_period', -1) >= q else r
            for r in rows if r['kind'] == 'closed' and r['booked_period'] < q]


def expit(x):
    return 1 / (1 + np.exp(-np.clip(x, -40, 40)))


def ridge(x, y, w, penalty=1.0):
    regularizer = np.eye(x.shape[1]) * penalty
    regularizer[0, 0] = 1e-8
    return np.linalg.solve(x.T @ (w[:, None] * x) + regularizer, x.T @ (w[:, None] * y) if y.ndim == 2 else x.T @ (w * y))


def logistic(x, y, w):
    beta = np.zeros(x.shape[1])
    penalty = np.eye(len(beta))
    penalty[0, 0] = 1e-8
    for _ in range(40):
        p = expit(x @ beta)
        h = x.T @ ((w * p * (1 - p))[:, None] * x) + penalty
        step = np.linalg.solve(h, x.T @ (w * (y - p)) - penalty @ beta)
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            break
    return beta


def prepare(workspace, lane, transform):
    """Load only the selected view; build point-in-time, recency-weighted fits."""
    i = LANES.index(lane)
    rows = read_tree(workspace, VIEWS[i])
    observations = {(r['fund_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for q in FIT_PERIODS:
        closed = asof(rows, q)
        x = np.array([[r[k] for k in KEYS[i]] for r in closed])
        centre = np.median(x, axis=0)
        scale = np.maximum(np.std(x, axis=0), 0.01)
        models[q] = {'rows': closed, 'x': (x - centre) / scale, 'centre': centre, 'scale': scale,
                     'y': transform(closed), 'w': np.exp(-np.array([q - 1 - r['booked_period'] for r in closed]) / (6 + i)),
                     'group': np.array([r['group'] for r in closed])}
    return {'models': models, 'observations': observations, 'keys': KEYS[i]}


def point(fitted, fund, period):
    m, row = fitted['models'][period], fitted['observations'][fund, period]
    z = (np.array([row[k] for k in fitted['keys']]) - m['centre']) / m['scale']
    return m, row, z


def kernel(m, z, group, bandwidth=1.0, neighbours=80):
    d = np.sum((m['x'] - z) ** 2, axis=1) + 3 * (m['group'] != group)
    idx = np.argsort(d, kind='stable')[:neighbours]
    weights = np.exp(-d[idx] / (2 * bandwidth ** 2)) * m['w'][idx]
    return idx, weights


def basis(x, groups):
    return np.column_stack([np.ones(len(x)), x, x[:, 0] * x[:, 1],
                            np.sin(x[:, 4]), np.cos(x[:, 4]), *(groups == i for i in (1, 2, 3))])


# --- lane 1: NAV break, local linear fit in log basis points --------------------

def fit_nav_break_magnitude(workspace):
    return prepare(workspace, LANES[0], lambda rows: np.log1p([r['break_bps'] for r in rows]))


def predict_nav_break_magnitude(fitted, fund, period, workspace):
    m, row, z = point(fitted, fund, period)
    idx, w = kernel(m, z, row['group'], 1.15, 110)
    design = np.column_stack([np.ones(len(idx)), m['x'][idx] - z])
    beta = ridge(design, m['y'][idx], w, 0.18)
    return round(float(max(0, np.expm1(beta[0]))), 2)


# --- lane 2: fee composition, exposure-normalised Dirichlet kernel pooling ------

def fit_fee_accrual_profile(workspace):
    def target(rows):
        a = np.array([r['component_amounts'] for r in rows])
        return a / a.sum(axis=1)[:, None]
    return prepare(workspace, LANES[1], target)


def predict_fee_accrual_profile(fitted, fund, period, workspace):
    m, row, z = point(fitted, fund, period)
    idx, w = kernel(m, z, row['group'], 0.95, 55)
    mask = m['group'] == row['group']
    prior = np.average(m['y'][mask], axis=0, weights=m['w'][mask])
    profile = (w @ m['y'][idx] + 1.5 * prior) / (w.sum() + 1.5)
    return (np.floor(profile[:8] * 1e8) / 1e8).tolist()


# --- lane 3: reissue detection, interaction logistic with prevalence threshold -

def fit_restatement_flag(workspace):
    fitted = prepare(workspace, LANES[2], lambda rows: np.array([r['reissued'] for r in rows]))
    for m in fitted['models'].values():
        x = basis(m['x'], m['group'])
        m['beta'] = logistic(x, m['y'], m['w'])
        p = expit(x @ m['beta'])
        order = np.argsort(-p, kind='stable')
        prevalence = np.average(m['y'], weights=m['w'])
        j = min(len(order) - 1, np.searchsorted(np.cumsum(m['w'][order]), prevalence * m['w'].sum()))
        m['threshold'] = p[order[j]]
    return fitted


def predict_restatement_flag(fitted, fund, period, workspace):
    m, row, z = point(fitted, fund, period)
    return int(expit(basis(z[None, :], np.array([row['group']])) @ m['beta'])[0] >= m['threshold'])


# --- lane 4: dominant-source reliability, shrunk kernel and fixed tier bands ---

def fit_pricing_source_tier(workspace):
    return prepare(workspace, LANES[3], lambda rows: np.array([r['reliability'] for r in rows]))


def predict_pricing_source_tier(fitted, fund, period, workspace):
    m, row, z = point(fitted, fund, period)
    idx, w = kernel(m, z, row['group'], 0.85, 65)
    prior = np.average(m['y'], weights=m['w'])
    value = (w @ m['y'][idx] + 0.7 * prior) / (w.sum() + 0.7)
    return int(np.searchsorted([0.38, 0.50, 0.62], value))


# --- lane 5: oversight priority, nonlinear ridge plus robust residual kernel ----

def fit_oversight_rank(workspace):
    fitted = prepare(workspace, LANES[4], lambda rows: np.log1p([r['review_hours'] for r in rows]))
    for m in fitted['models'].values():
        x = basis(m['x'], m['group'])
        m['beta'] = ridge(x, m['y'], m['w'], 0.4)
        residual = m['y'] - x @ m['beta']
        centre = np.median(residual)
        spread = max(0.01, np.median(np.abs(residual - centre)))
        m['residual'] = np.clip(residual, centre - 3 * spread, centre + 3 * spread)
    fitted['cohorts'] = {r['fund_id']: r['cohort'] for p in sorted((Path(workspace) / 'register').glob('*.json'))
                         for r in [json.loads(p.read_text())]}
    return fitted


def oversight_score(fitted, fund, period):
    m, row, z = point(fitted, fund, period)
    idx, w = kernel(m, z, row['group'], 1.0, 45)
    value = (basis(z[None, :], np.array([row['group']])) @ m['beta'])[0]
    value += (w @ m['residual'][idx]) / (w.sum() + 2)
    return round(float(value), 8)


def predict_oversight_rank(fitted, fund, period, workspace):
    cohort = fitted['cohorts'][fund]
    key = (period, cohort)
    cache = fitted.setdefault('rank_cache', {})
    if key not in cache:
        ids = sorted(a for a, c in fitted['cohorts'].items() if c == cohort)
        scores = {a: oversight_score(fitted, a, period) for a in ids}
        ranks = {v: i + 1 for i, v in enumerate(sorted(set(scores.values()), reverse=True))}
        cache[key] = {a: ranks[s] for a, s in scores.items()}
    return cache[key][fund]


# --- lane 6: expense reserve, two-part empirical-Bayes overrun severity ---------

def fit_expense_reserve(workspace):
    return prepare(workspace, LANES[5], lambda rows: np.array([r['overrun_amount'] / r['annual_budget'] for r in rows]))


def predict_expense_reserve(fitted, fund, period, workspace):
    m, row, z = point(fitted, fund, period)
    idx, w = kernel(m, z, row['group'], 1.1, 70)
    mask = m['group'] == row['group']
    pool = m['y'][mask]
    positive = pool[pool > 0]
    prior_p = (np.sum(pool > 0) + 1) / (len(pool) + 2)
    prior_log = np.mean(np.log(positive))
    local = m['y'][idx]
    hit = local > 0
    probability = (w @ hit + 4 * prior_p) / (w.sum() + 4)
    severity = np.exp((w[hit] @ np.log(local[hit]) + 3 * prior_log) / (w[hit].sum() + 3)
                      + 0.25 * np.var(np.log(positive)))
    return round(float(row['annual_budget'] * (1 - row['waiver_share']) * probability * severity), 2)


def predict_all(workspace, queries=None):
    queries = read_rows(Path(workspace) / 'queries.jsonl') if queries is None else queries
    models = {lane: globals()['fit_' + lane](workspace) for lane in LANES}
    return [dict(record_id=r['record_id'], **{lane: globals()['predict_' + lane](models[lane], r['fund_id'], r['period'], workspace)
                                            for lane in LANES}) for r in queries]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows = predict_all(args.workspace)
    Path(args.output).write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':')) + '\n' for r in rows))


if __name__ == '__main__':
    main()
