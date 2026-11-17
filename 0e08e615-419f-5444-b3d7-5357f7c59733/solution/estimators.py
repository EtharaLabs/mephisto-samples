"""Private, independently fitted methods for the intercompany settlement desk.

Only published ledgers enter these fits. Closed outcomes are observations, never
graded draws. No lane consumes another lane's labels, fitted state or predictions.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from threadpoolctl import threadpool_limits

LANES = ('adjustment_magnitude', 'allocation_key_profile', 'challenge_flag',
         'method_tier', 'review_rank', 'uncertain_tax_reserve')
VIEWS = ('invoices', 'allocation_drivers', 'tax_audits', 'comparables', 'settlements', 'tax_positions')
FIELDS = (
    ('margin_gap', 'functional_complexity', 'royalty_intensity', 'documentation_gap', 'fx_volatility', 'service_mix'),
    ('headcount_share', 'revenue_share', 'asset_share', 'transaction_share', 'compute_share', 'benefit_evidence'),
    ('prior_challenges', 'documentation_gap', 'jurisdiction_risk', 'apa_coverage', 'margin_outlier', 'audit_age'),
    ('product_similarity', 'cost_traceability', 'resale_observability', 'unique_intangibles', 'integration', 'comparability'),
    ('unsettled_share', 'due_age', 'fx_volatility', 'dispute_intensity', 'materiality', 'seasonality'),
    ('tax_rate', 'treaty_relief', 'documentation_gap', 'jurisdiction_risk', 'interest_age', 'provision_coverage'),
)
PERIODS = (8, 10, 12, 16, 20)


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n' for r in rows))


def load_view(workspace, index):
    rows = [r for p in sorted((Path(workspace) / VIEWS[index]).glob('*.jsonl')) for r in read_rows(p)]
    register = {p.stem: json.loads(p.read_text()) for p in sorted((Path(workspace) / 'register').glob('*.json'))}
    for row in rows:
        row['jurisdiction_band'] = register[row['pair_id']]['jurisdiction_band']
    return rows


def asof(rows, period):
    return [dict(r, **r.get('as_booked', {})) if r.get('restated_period', -1) >= period else r
            for r in rows if r['kind'] == 'closed' and r['booked_period'] < period]


def design(rows, index):
    return np.array([[r[k] for k in FIELDS[index]] +
                     [float(r['jurisdiction_band'] == j) for j in range(4)] for r in rows])


def basis(x, index):
    """Lane-specific desk basis; no fitted state is shared across lanes."""
    if index == 0:
        return np.column_stack((x, x[:, 0] * x[:, 1], np.sin(4 * x[:, 2]), x[:, 3] ** 2))
    if index == 2:
        return np.column_stack((x, x[:, 0] * x[:, 4], x[:, 1] * (1 - x[:, 3])))
    if index == 4:
        return np.column_stack((x, np.sin(2 * np.pi * x[:, 5]), np.cos(2 * np.pi * x[:, 5]), x[:, 0] * x[:, 3]))
    return np.column_stack((x, x[:, 0] * x[:, 3], x[:, 2] ** 2))


def kernel(x, y, z, weights, neighbors, scale=2.0):
    out = []
    for point in z:
        d = np.sum((x - point) ** 2, axis=1)
        ix = np.argsort(d, kind='stable')[:neighbors]
        w = np.exp(-scale * d[ix] / max(d[ix[-1]], 0.001)) * weights[ix]
        out.append(np.average(y[ix], axis=0, weights=w))
    return np.asarray(out)


def fit_lane(workspace, index):
    """Transport dispatch; each invocation fits one independent lane on one view."""
    rows = load_view(workspace, index)
    snaps = {(r['pair_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
    models = {}
    for period in PERIODS:
        cases = asof(rows, period)
        x = design(cases, index)
        y = np.array([r['outcome'] for r in cases])
        w = np.exp(-np.array([period - r['booked_period'] for r in cases]) / (5 + index))
        m = {'x': x, 'y': y, 'w': w}
        if index in (0, 4):
            reg = Ridge(alpha=0.8 if index == 0 else 1.5).fit(basis(x, index), y, sample_weight=w)
            m.update(reg=reg, residual=y - reg.predict(basis(x, index)))
        elif index == 2:
            reg = LogisticRegression(C=1.4, max_iter=500, random_state=71).fit(basis(x, index), y, sample_weight=w)
            p = reg.predict_proba(basis(x, index))[:, 1]
            m.update(reg=reg, threshold=float(np.quantile(p, 1 - np.average(y, weights=w))))
        elif index == 5:
            flag = (y > 0).astype(int)
            assert len(set(flag.tolist())) == 2, 'reserve incidence requires observed zero and positive cases'
            reg = LogisticRegression(C=0.7, max_iter=500, random_state=73).fit(basis(x, index), flag, sample_weight=w)
            m.update(reg=reg, positive=flag.astype(bool))
        models[period] = m
    return {'models': models, 'observations': snaps, 'index': index}


def predict_batch(fitted, records):
    index = fitted['index']
    values: list[float | int | list[float] | None] = [None] * len(records)
    for period in sorted({r['period'] for r in records}):
        ix = [i for i, r in enumerate(records) if r['period'] == period]
        snaps = [fitted['observations'][records[i]['pair_id'], period] for i in ix]
        z = design(snaps, index)
        m = fitted['models'][period]
        if index == 0:
            pred = m['reg'].predict(basis(z, index)) + kernel(m['x'], m['residual'], z, m['w'], 28)
            pred = np.clip(pred, 0.002, 0.8) * np.array([r['charge_base'] for r in snaps])
        elif index == 1:
            # Local compositional centre shrunk toward a jurisdiction-specific mean.
            pred = kernel(m['x'], m['y'], z, m['w'], 32, 3.2)
            for j, row in enumerate(snaps):
                mask = m['x'][:, 6 + row['jurisdiction_band']] == 1
                pred[j] = 0.86 * pred[j] + 0.14 * np.average(m['y'][mask], axis=0, weights=m['w'][mask])
        elif index == 2:
            pred = (m['reg'].predict_proba(basis(z, index))[:, 1] >= m['threshold']).astype(int)
        elif index == 3:
            # Ordered expected suitability, not a mandated hierarchy of OECD methods.
            suitability = kernel(m['x'], m['y'], z, m['w'], 42, 2.7)
            pred = np.clip(np.floor(suitability + 0.5), 0, 3).astype(int)
        elif index == 4:
            pred = m['reg'].predict(basis(z, index)) + kernel(m['x'], m['residual'], z, m['w'], 36, 2.4)
            pred = pred * np.array([r['settlement_base'] for r in snaps]) - np.array([r['paid_on_account'] for r in snaps])
            rounded = np.round(pred, 6)
            order = {v: i + 1 for i, v in enumerate(sorted(set(rounded), reverse=True))}
            pred = np.array([order[v] for v in rounded])
        else:
            pos = m['positive']
            severity = np.exp(kernel(m['x'][pos], np.log(m['y'][pos]), z, m['w'][pos], 35, 2.6))
            probability = m['reg'].predict_proba(basis(z, index))[:, 1]
            pred = severity * probability * np.array([r['tax_exposure'] for r in snaps])
        for i, value in zip(ix, pred):
            if index == 1:
                value = np.maximum(value, 0)
                value /= max(1.0, value.sum())
                values[i] = (np.floor(value * 1e8) / 1e8).tolist()
            elif index in (2, 3, 4):
                values[i] = int(value)
            else:
                values[i] = round(max(0.0, float(value)), 2)
    return values


def fit_adjustment_magnitude(workspace):
    return fit_lane(workspace, 0)


def fit_allocation_key_profile(workspace):
    return fit_lane(workspace, 1)


def fit_challenge_flag(workspace):
    return fit_lane(workspace, 2)


def fit_method_tier(workspace):
    return fit_lane(workspace, 3)


def fit_review_rank(workspace):
    return fit_lane(workspace, 4)


def fit_uncertain_tax_reserve(workspace):
    return fit_lane(workspace, 5)


def records_for(workspace, queries):
    output = [dict(record_id=r['record_id']) for r in queries]
    with threadpool_limits(limits=1):
        for lane in LANES:
            model = globals()['fit_' + lane](workspace)
            for row, value in zip(output, predict_batch(model, queries)):
                row[lane] = value
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write_rows(args.output, records_for(args.workspace, read_rows(args.workspace / 'queries.jsonl')))


if __name__ == '__main__':
    main()
