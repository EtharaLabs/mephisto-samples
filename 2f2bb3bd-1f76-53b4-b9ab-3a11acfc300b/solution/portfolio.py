"""Frozen public-only estimator ladder, with no import of the private desk methods.

The one-shot forest uses current closed-case ledger values without tuning. Later rungs
test model family, ledger version, recency, group locality and log-response fitting.
All predictions are fitted from public observations; no rung reads graded truth or floors.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from threadpoolctl import threadpool_limits

LANES = ('discrepancy_count', 'discrepancy_class_profile', 'refusal_flag', 'tenor_tier',
         'examiner_priority_rank', 'charge_reserve')
VIEWS = ('presentation_documents', 'discrepancy_logs', 'refusal_notices', 'amendment_histories',
         'correspondent_banks', 'settlement_payments')
GROUPS = ('document_route', 'trade_corridor', 'credit_form', 'tenor_basis', 'service_band', 'charge_schedule')
FIELDS = (
    ('document_count', 'data_conflict_share', 'missing_original_share', 'presentation_lag_days', 'expiry_margin_days'),
    ('late_share', 'inconsistency_share', 'missing_share', 'insurance_gap', 'transport_complexity'),
    ('unwaived_items', 'applicant_response_days', 'material_conflict_share', 'notice_time_left', 'waiver_reliability'),
    ('draft_tenor_days', 'acceptance_delay_days', 'amendment_count', 'maturity_extension_days', 'deferred_share'),
    ('bank_queue_hours', 'cutoff_margin_hours', 'document_complexity', 'corridor_delay_days', 'cycle_phase'),
    ('face_amount_usd', 'unpaid_fee_share', 'message_count', 'claim_complexity', 'relationship_years'))
OUTCOMES = ('observed_discrepancies', 'class_counts', 'notice_refused', 'settled_tenor_days',
            'handling_urgency', 'charges_usd')
METHODS = ('constant', 'history_forest', 'oneshot_forest', 'linear', 'hgb_plain', 'extra_trees',
           'kernel_plain', 'kernel_asof', 'kernel_recent', 'kernel_grouped', 'local_log', 'hybrid')


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n' for r in rows))


def load(workspace, index):
    root = Path(workspace)
    registers = {p.stem: json.loads(p.read_text()) for p in sorted((root / 'credit_register').glob('*.json'))}
    closed, snapshots = [], {}
    for path in sorted((root / VIEWS[index]).glob('*.jsonl')):
        for row in read_rows(path):
            if row['kind'] == 'closed':
                closed.append(row)
            else:
                row = dict(row, **{GROUPS[index]: registers[row['beneficiary_id']][GROUPS[index]]})
                snapshots[row['beneficiary_id'], row['period']] = row
    return closed, snapshots


def features(rows, index):
    x = np.array([[r[k] for k in FIELDS[index]] for r in rows])
    if index == 5:
        x[:, 0] = np.log(x[:, 0])
    group = np.array([r[GROUPS[index]] for r in rows])
    return np.column_stack([x, *[(group == g).astype(float) for g in range(4)]])


def response(rows, index):
    y = np.array([r[OUTCOMES[index]] for r in rows], dtype=float)
    if index == 1:
        y = y / y.sum(axis=1)[:, None]
    if index == 5:
        y = y / np.array([r['face_amount_usd'] for r in rows])
    return y


def tree_predict(kind, x, y, target, weights):
    def model():
        if kind == 'hgb_plain':
            return HistGradientBoostingRegressor(max_iter=160, max_leaf_nodes=12, l2_regularization=2,
                                                 random_state=71, early_stopping=False)
        cls = ExtraTreesRegressor if kind == 'extra_trees' else RandomForestRegressor
        return cls(n_estimators=100, random_state=71, n_jobs=1)
    if y.ndim == 2 and kind == 'hgb_plain':
        return np.column_stack([model().fit(x, y[:, j], sample_weight=weights).predict(target) for j in range(y.shape[1])])
    return model().fit(x, y, sample_weight=weights).predict(target)


def kernel_predict(x, y, target, weights, grouped=False, local=False):
    centre = np.median(x[:, :5], axis=0)
    scale = np.maximum(np.median(abs(x[:, :5] - centre), axis=0), 0.05)
    z, zz = (x[:, :5] - centre) / scale, (target[:, :5] - centre) / scale
    output = []
    for point, raw in zip(zz, target):
        distance = ((z - point) ** 2).sum(axis=1)
        same = (x[:, 5:] == raw[5:]).all(axis=1)
        distance += (1e6 if grouped else 2.0) * ~same
        near = np.argsort(distance, kind='stable')[:40]
        w = weights[near] * np.exp(-2.5 * distance[near] / max(0.01, distance[near[-1]]))
        if local:
            design = np.column_stack([np.ones(len(near)), z[near] - point])
            penalty = np.eye(design.shape[1]) * 0.8
            penalty[0, 0] = 0
            rhs = design.T @ (w[:, None] * y[near]) if y.ndim == 2 else design.T @ (w * y[near])
            output.append(np.linalg.solve(design.T @ (w[:, None] * design) + penalty, rhs)[0])
        else:
            output.append(np.average(y[near], axis=0, weights=w))
    return np.array(output)


def fit_predict(method, index, rows, snapshots, period):
    x, target = features(rows, index), features(snapshots, index)
    y = response(rows, index)
    recent = method in ('kernel_recent', 'kernel_grouped', 'local_log', 'hybrid')
    weights = np.exp(-(period - 1 - np.array([r['booked_period'] for r in rows])) / 7) if recent else np.ones(len(rows))
    if method in ('oneshot_forest', 'hgb_plain', 'extra_trees'):
        result = tree_predict(method, x, y, target, weights)
    elif method == 'linear':
        scaler = StandardScaler().fit(x)
        result = Ridge(alpha=2).fit(scaler.transform(x), y).predict(scaler.transform(target))
    elif method == 'hybrid' and index == 2:
        scaler = StandardScaler().fit(x[:, :5])
        z, zz = scaler.transform(x[:, :5]), scaler.transform(target[:, :5])
        poly = PolynomialFeatures(degree=2, include_bias=False)
        design = np.column_stack([poly.fit_transform(z), x[:, 5:]])
        query = np.column_stack([poly.transform(zz), target[:, 5:]])
        model = LogisticRegression(C=0.8, max_iter=500, random_state=71).fit(design, y, sample_weight=weights)
        return model.predict_proba(query)[:, 1], float(np.quantile(model.predict_proba(design)[:, 1], 1 - np.average(y, weights=weights)))
    elif method == 'hybrid' and index == 4:
        def design(a):
            return np.column_stack([a[:, :4], np.sin(2 * np.pi * a[:, 4]), np.cos(2 * np.pi * a[:, 4]),
                                    a[:, 0] * a[:, 2], np.sin(a[:, 3] / 4 + 3 * a[:, 2])])
        result = np.empty(len(target))
        for group in range(4):
            train, query = x[:, 5 + group] == 1, target[:, 5 + group] == 1
            model = Ridge(alpha=0.7).fit(design(x[train]), y[train], sample_weight=weights[train])
            result[query] = model.predict(design(target[query]))
    elif method == 'hybrid' and index == 5:
        positive = y > 0
        probability = kernel_predict(x, positive.astype(float), target, weights, grouped=True)
        severity = kernel_predict(x[positive], np.log(y[positive]), target, weights[positive], grouped=True)
        result = probability * np.exp(severity + 0.15 * np.var(np.log(y[positive])))
    else:
        log_response = method in ('local_log', 'hybrid') and index == 0
        yy = np.log1p(y) if log_response else y
        result = kernel_predict(x, yy, target, weights,
                                grouped=method in ('kernel_grouped', 'local_log', 'hybrid'),
                                local=log_response)
        if log_response:
            result = np.expm1(result)
    threshold = float(np.average(y, weights=weights)) if index == 2 else 0.0
    return result, threshold


def constant(history, queries):
    anchor = {}
    for index, lane in enumerate(LANES):
        if index == 1:
            anchor[lane] = np.mean([r[lane] for r in history], axis=0).tolist()
        elif index in (2, 3):
            anchor[lane] = max(range(2 if index == 2 else 4), key=lambda c: sum(r[lane] == c for r in history))
        elif index == 4:
            anchor[lane] = 140
        else:
            anchor[lane] = round(float(np.median([r[lane] for r in history])), 2)
    return [dict(record_id=r['record_id'], **anchor) for r in queries]


def predict(workspace, method):
    threadpool_limits(limits=1)
    root = Path(workspace)
    history = read_rows(root / 'history/examination.jsonl')
    queries = read_rows(root / 'queries.jsonl')
    if method == 'constant':
        return constant(history, queries)
    answers = [dict(record_id=r['record_id']) for r in queries]
    for index, lane in enumerate(LANES):
        closed, snapshots = load(root, index)
        if method == 'history_forest':
            train = features([snapshots[r['beneficiary_id'], r['period']] for r in history], index)
            query = features([snapshots[r['beneficiary_id'], r['period']] for r in queries], index)
            y = np.array([r[lane] for r in history], dtype=float)
            values = tree_predict('oneshot_forest', train, y, query, np.ones(len(train)))
            if index == 4:
                for period in sorted({r['period'] for r in queries}):
                    ix = [i for i, r in enumerate(queries) if r['period'] == period]
                    order = {v: j + 1 for j, v in enumerate(sorted(set(values[ix])))}
                    values[ix] = [order[v] for v in values[ix]]
        else:
            values = [0.0] * len(queries)
            for period in sorted({r['period'] for r in queries}):
                rows = [r for r in closed if r['booked_period'] < period]
                if method in ('kernel_asof', 'kernel_recent', 'kernel_grouped', 'local_log', 'hybrid'):
                    rows = [dict(r, **r.get('as_booked', {})) if r.get('restated_period', -1) >= period else r for r in rows]
                ix = [i for i, r in enumerate(queries) if r['period'] == period]
                snaps = [snapshots[queries[i]['beneficiary_id'], period] for i in ix]
                pp, threshold = fit_predict(method, index, rows, snaps, period)
                if index == 2:
                    pp = (pp >= threshold).astype(int)
                if index == 3:
                    pp = np.searchsorted([45, 95, 160], pp, side='left')
                if index == 4:
                    order = {v: j + 1 for j, v in enumerate(sorted(set(pp), reverse=True))}
                    pp = [order[v] for v in pp]
                if index == 5:
                    pp = pp * np.array([r['face_amount_usd'] for r in snaps])
                for i, value in zip(ix, pp):
                    values[i] = value
        for row, value in zip(answers, values):
            if index == 1:
                value = np.maximum(0, np.asarray(value)[:8])
                value /= max(1, value.sum())
                row[lane] = (np.floor(value * 1e8) / 1e8).tolist()
            elif index in (2, 3, 4):
                row[lane] = int(round(float(value)))
            else:
                row[lane] = round(max(0, float(value)), 2)
    return answers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--method', choices=METHODS, default='hybrid')
    args = parser.parse_args()
    write_rows(args.output, predict(args.workspace, args.method))


if __name__ == '__main__':
    main()
