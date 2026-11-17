"""Independent analyst portfolio using public ledgers and historical oversight only.

No import from the oracle, no truth reads and no floor reads. Candidate settings
are fixed before the ladder is measured. Each lane is fitted separately.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge

LANES = ('nav_break_magnitude', 'fee_accrual_profile', 'restatement_flag',
         'pricing_source_tier', 'oversight_rank', 'expense_reserve')
VIEWS = ('positions', 'accruals', 'corporate_actions', 'prices', 'flows', 'expenses')
TARGETS = ('break_bps', 'component_amounts', 'reissued', 'reliability', 'review_hours', 'overrun_amount')
METHODS = ('constant', 'ridge_closed', 'rf_closed', 'rf_asof', 'extra_trees', 'hgb',
           'kernel_wide', 'kernel_local', 'local_linear', 'structured')


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_rows(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n' for r in rows))


def nonlinear(x):
    return np.column_stack([x, x[:, 0]*x[:, 1], np.sin(x[:, 4]), np.cos(x[:, 4])])


def candidate(train, targets, test, weights, method, i):
    """Fit one lane; return pre-schema predictions, never hidden graded values."""
    mean, scale = np.mean(train[:, :6], axis=0), np.maximum(np.std(train[:, :6], axis=0), .01)
    x = (train[:, :6] - mean) / scale
    z = (test[:, :6] - mean) / scale
    groups, test_groups = train[:, 6], test[:, 6]
    design = np.column_stack([x, *(groups == j for j in range(4))])
    points = np.column_stack([z, *(test_groups == j for j in range(4))])
    if method == 'ridge_closed':
        return Ridge(alpha=5).fit(design, targets).predict(points)
    if method.startswith('rf'):
        model = RandomForestRegressor(n_estimators=120, min_samples_leaf=12, random_state=418, n_jobs=1)
        return model.fit(design, targets, sample_weight=weights).predict(points)
    if method == 'extra_trees':
        model = ExtraTreesRegressor(n_estimators=180, min_samples_leaf=8, random_state=418, n_jobs=1)
        return model.fit(design, targets, sample_weight=weights).predict(points)
    if method == 'hgb':
        def fit(y):
            return HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=12, l2_regularization=4,
                                                random_state=418, early_stopping=False).fit(design, y, sample_weight=weights).predict(points)
        return np.column_stack([fit(targets[:, j]) for j in range(targets.shape[1])]) if targets.ndim == 2 else fit(targets)
    if method == 'structured' and i == 2:
        design = np.column_stack([nonlinear(x), *(groups == j for j in range(4))])
        points = np.column_stack([nonlinear(z), *(test_groups == j for j in range(4))])
        return LogisticRegression(C=.5, max_iter=300, random_state=418).fit(design, targets, sample_weight=weights).predict_proba(points)[:, 1]
    if method == 'structured' and i == 4:
        design = np.column_stack([nonlinear(x), *(groups == j for j in range(4))])
        points = np.column_stack([nonlinear(z), *(test_groups == j for j in range(4))])
        model = Ridge(alpha=2).fit(design, targets, sample_weight=weights)
        base = model.predict(points)
        targets = targets - model.predict(design)
    else:
        base = np.zeros(len(z))
    bandwidth, neighbours = {'kernel_wide': (1.8, 180), 'kernel_local': (1.0, 80),
                              'local_linear': (1.25, 100), 'structured': (1.2, 90)}[method]
    results = []
    prior = np.average(targets, axis=0, weights=weights)
    for j, point in enumerate(z):
        d = np.sum((x - point)**2, axis=1) + 2 * (groups != test_groups[j])
        idx = np.argsort(d, kind='stable')[:neighbours]
        w = np.exp(-d[idx] / (2*bandwidth**2)) * weights[idx]
        y = targets[idx]
        if method in ('local_linear', 'structured') and i == 0:
            model = Ridge(alpha=.6).fit(x[idx] - point, y, sample_weight=w)
            value = model.predict(np.zeros((1, 6)))[0]
        elif method == 'structured' and i == 5:
            hit = y > 0
            positive = targets[targets > 0]
            p = (w @ hit + 5 * np.mean(targets > 0)) / (w.sum() + 5)
            logmean = (w[hit] @ np.log(y[hit]) + 5*np.log(positive).mean()) / (w[hit].sum() + 5)
            value = p * np.exp(logmean + .25*np.var(np.log(positive)))
        else:
            value = (w @ y + 2 * prior) / (w.sum() + 2)
        results.append(value + base[j])
    return np.array(results)


def predictions(workspace, method):
    workspace = Path(workspace)
    queries = read_rows(workspace / 'queries.jsonl')
    history = read_rows(workspace / 'history' / 'oversight.jsonl')
    metadata = json.loads((workspace / 'dataset_metadata.json').read_text())
    output = {q['record_id']: {'record_id': q['record_id']} for q in queries}
    if method == 'constant':
        for i, lane in enumerate(LANES):
            values = np.array([h[lane] for h in history])
            value = np.mean(values, axis=0)
            if i in (0, 5):
                value = round(float(value), 2)
            elif i == 1:
                value = (np.floor(value*1e8)/1e8).tolist()
            else:
                value = int(round(float(value)))
            for row in output.values():
                row[lane] = value
        return list(output.values())
    for i, (lane, view, target) in enumerate(zip(LANES, VIEWS, TARGETS)):
        rows = [r for p in sorted((workspace / view).glob('*.jsonl')) for r in read_rows(p)]
        snapshots = {(r['fund_id'], r['period']): r for r in rows if r['kind'] == 'snapshot'}
        keys = metadata['views'][view]
        for q in sorted(set(r['period'] for r in queries)):
            selected = [r for r in queries if r['period'] == q]
            closed = [r for r in rows if r['kind'] == 'closed' and r['booked_period'] < q]
            if method not in ('ridge_closed', 'rf_closed'):
                closed = [dict(r, **r.get('as_booked', {})) if r.get('restated_period', -1) >= q else r for r in closed]
            snapshots_q = [snapshots[r['fund_id'], q] for r in selected]
            x = np.array([[r[k] for k in keys] + [r['group']] for r in closed])
            z = np.array([[r[k] for k in keys] + [r['group']] for r in snapshots_q])
            y = np.array([r[target] for r in closed], dtype=float)
            if i in (0, 4):
                y = np.log1p(y)
            elif i == 1:
                y = y / y.sum(axis=1)[:, None]
            elif i == 5:
                y /= np.array([r['annual_budget'] for r in closed])
            weights = np.ones(len(closed)) if method in ('ridge_closed', 'rf_closed') else np.exp(-np.array([q-1-r['booked_period'] for r in closed])/8)
            raw = candidate(x, y, z, weights, method, i)
            if i in (0, 4):
                raw = np.expm1(raw)
            if i == 2:
                # Prevalence-matching is based on public completed cases, not truth.
                train_score = candidate(x, y, x, weights, method, i)
                threshold = np.quantile(train_score, 1 - np.average(y, weights=weights))
                raw = (raw >= threshold).astype(int)
            elif i == 3:
                # Public-history proportions locate tier cutpoints in predicted reliability.
                proportions = [np.mean([h[lane] <= c for h in history]) for c in (0, 1, 2)]
                bounds = np.quantile(raw, proportions)
                raw = np.searchsorted(bounds, raw)
            elif i == 4:
                ranks = {v: j+1 for j, v in enumerate(sorted(set(raw), reverse=True))}
                raw = np.array([ranks[v] for v in raw])
            for row, snapshot, value in zip(selected, snapshots_q, raw):
                if i == 0:
                    value = round(float(max(0, value)), 2)
                elif i == 1:
                    value = np.maximum(0, value)
                    value /= max(value.sum(), 1e-12)
                    value = (np.floor(value[:8]*1e8)/1e8).tolist()
                elif i == 5:
                    value = round(float(max(0, value) * snapshot['annual_budget'] * (1-snapshot['waiver_share'])), 2)
                else:
                    value = int(value)
                output[row['record_id']][lane] = value
    return list(output.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--method', choices=METHODS, default='structured')
    args = parser.parse_args()
    write_rows(args.output, predictions(args.workspace, args.method))


if __name__ == '__main__':
    main()
