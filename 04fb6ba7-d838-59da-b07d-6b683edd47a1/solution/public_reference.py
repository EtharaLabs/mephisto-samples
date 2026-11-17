"""Independent public-only fit: a competent, informed attempt that shares no code with the reference.

Closed-case boosted trees and extra trees give lane-specific predictions; published surveillance
history selects between those and history-augmented regressions on period 12, trained on 8 and 10.
No score feedback is used. By default closed rows enter at their current ledger values, as a
first-time analyst would use them; --asof applies the point-in-time ledger discipline instead,
which is kept private and measured only to quantify what that discipline is worth.
Dependencies are imported before the strict data-access audit boundary.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import f1_score
from threadpoolctl import threadpool_limits

LANES = ('dilution_reserve', 'collection_profile', 'dispute_flag', 'recovery_tier', 'availability_rank', 'loss_reserve')
VIEWS = dict(zip(LANES, ('dilution', 'collections', 'disputes', 'delinquencies', 'borrowing_base', 'writeoffs')))
FIELDS = {
    'dilution_reserve': ['promo_intensity', 'return_propensity', 'pricing_dispute_index', 'invoice_size_log', 'terms_days'],
    'collection_profile': ['past_due_share', 'dispute_share', 'payment_regularity', 'remittance_lag', 'terms_days'],
    'dispute_flag': ['open_dispute_count', 'invoice_error_rate', 'po_mismatch_rate', 'days_since_last_dispute', 'contact_responsiveness'],
    'recovery_tier': ['days_past_due', 'secured_share', 'guarantor_strength', 'prior_cures', 'exposure_log'],
    'availability_rank': ['ineligible_share', 'concentration_index', 'cross_aged_share', 'insurance_coverage', 'seasonality_phase', 'dilution_history', 'gross_receivables', 'reserve_holdback', 'drawn_balance'],
    'loss_reserve': ['insured_share', 'payment_score', 'sector_stress', 'years_relationship', 'credit_limit_utilisation', 'exposure'],
}
CATEGORIES = {'dilution_reserve': [('product_mix', 4), ('channel', 3)], 'collection_profile': [('region', 4)],
              'dispute_flag': [('contract_type', 4)], 'recovery_tier': [('legal_stage', 4)],
              'availability_rank': [('advance_band', 4)], 'loss_reserve': [('rating_band', 4)]}


def features(lane, row):
    values = [float(row.get(k, 0)) for k in FIELDS[lane]]
    for cat, count in CATEGORIES[lane]:
        values += [float(row.get(cat, 0) == i) for i in range(count)]
    if lane == 'availability_rank':
        values += [math.log(max(1.0, row['gross_receivables'])), row['reserve_holdback'] / max(1.0, row['gross_receivables']), row['drawn_balance'] / max(1.0, row['gross_receivables'])]
    if lane == 'loss_reserve':
        values += [math.log(max(1.0, row['exposure']))]
    return values


def new_model(kind, classification=False):
    if kind == 'extra':
        cls = ExtraTreesClassifier if classification else ExtraTreesRegressor
        return cls(n_estimators=160, min_samples_leaf=4, max_features=1.0, random_state=191, n_jobs=1)
    cls = HistGradientBoostingClassifier if classification else HistGradientBoostingRegressor
    return cls(max_iter=180, max_leaf_nodes=15, l2_regularization=2.0, learning_rate=0.07, min_samples_leaf=15, random_state=191)


def fit_predict(kind, x, y, q, classification=False):
    if not classification and np.asarray(y).ndim == 2 and kind == 'boost':
        return np.column_stack([new_model(kind).fit(x, y[:, i]).predict(q) for i in range(y.shape[1])])
    model = new_model(kind, classification).fit(x, y)
    if not classification:
        return model.predict(q)
    count = 2 if set(np.unique(y)) <= {0, 1} else 4
    pred = np.zeros((len(q), count))
    pred[:, model.classes_.astype(int)] = model.predict_proba(q)
    return pred


def asof_view(row, period, enabled):
    if enabled and 'restated_period' in row and row['restated_period'] >= period:
        return dict(row, **row['as_booked'])
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--asof', action='store_true', help='private diagnostic: apply the point-in-time ledger discipline')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    output, audit_path = args.output.resolve(), args.audit.resolve()
    for path in (output, audit_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    threadpool_limits(limits=1)
    xx = np.arange(160).reshape(80, 2)
    for classification in (False, True):
        for kind in ('extra', 'boost'):
            fit_predict(kind, xx, np.arange(80) % 2 if classification else np.arange(80), xx, classification)
    spearmanr(np.arange(4), np.arange(4))
    audit = {'reads': 0, 'violations': 0, 'read_paths': {}, 'asof': args.asof, 'workspace': str(workspace)}

    def hook(event, values):
        if event != 'open':
            return
        path, mode, flags = values
        if isinstance(path, int):
            audit['violations'] += 1
            raise PermissionError('file-descriptor opens are not permitted')
        resolved = Path(os.fsdecode(path)).resolve()
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        allowed = resolved in (output, audit_path) if writing else resolved.is_relative_to(workspace)
        if not allowed:
            audit['violations'] += 1
            raise PermissionError('audit denied: ' + str(resolved))
        if not writing:
            audit['reads'] += 1
            name = str(resolved.relative_to(workspace))
            audit['read_paths'][name] = audit['read_paths'].get(name, 0) + 1

    sys.addaudithook(hook)

    def jsonl(path):
        with path.open() as handle:
            return [json.loads(line) for line in handle if line.strip()]

    try:
        queries = jsonl(workspace / 'queries.jsonl')
        history = jsonl(workspace / 'history/surveillance.jsonl')
        data, snapshots = {}, {}
        for lane, view in VIEWS.items():
            rows = [r for path in sorted((workspace / view).glob('*.jsonl')) for r in jsonl(path)]
            data[lane] = [r for r in rows if r.get('kind') == 'closed']
            snapshots[lane] = {(r['obligor_id'], r['period']): r for r in rows if r.get('kind') == 'snapshot'}
        allrows = history + queries
        final = [dict(record_id=q['record_id']) for q in queries]
        train_mask = np.array([r['period'] < 12 for r in history])
        val_mask = ~train_mask
        diagnostics = {}
        for lane in LANES:
            query_views = [snapshots[lane][r['obligor_id'], r['period']] for r in allrows]
            x = np.array([features(lane, r) for r in query_views])
            classification = lane == 'dispute_flag'
            bases = {kind: [None] * len(allrows) for kind in ('extra', 'boost')}
            for period in sorted({r['period'] for r in allrows}):
                closed = [asof_view(r, period, args.asof) for r in data[lane] if r['booked_period'] < period]
                cx = np.array([features(lane, r) for r in closed])
                if lane == 'dilution_reserve':
                    cy = np.array([r['dilution_ratio'] for r in closed])
                elif lane == 'dispute_flag':
                    cy = np.array([r['escalated'] for r in closed])
                elif lane == 'recovery_tier':
                    cy = np.array([r['recovered_fraction'] for r in closed])
                elif lane == 'availability_rank':
                    cy = np.array([r['availability_ratio'] for r in closed])
                elif lane == 'loss_reserve':
                    cy = np.array([r['loss_amount'] / r['exposure'] for r in closed])
                else:
                    cy = None
                indices = [i for i, r in enumerate(allrows) if r['period'] == period]
                for kind in bases:
                    if lane == 'collection_profile':
                        survival = np.ones(len(indices))
                        pp = np.zeros((len(indices), 8))
                        for bucket in range(8):
                            risk = np.array([r['last_observed_bucket'] >= bucket and (r['paid_bucket'] < 0 or r['paid_bucket'] >= bucket) for r in closed])
                            event = np.array([int(r['paid_bucket'] == bucket) for r in closed])
                            model = new_model(kind, True).fit(cx[risk], event[risk])
                            hazard = model.predict_proba(x[indices])[:, list(model.classes_).index(1)] if 1 in model.classes_ else np.zeros(len(indices))
                            pp[:, bucket] = survival * hazard
                            survival *= 1 - hazard
                    else:
                        pp = fit_predict(kind, cx, cy, x[indices], classification)
                    if lane == 'availability_rank':
                        pp = pp * np.array([query_views[i]['gross_receivables'] for i in indices]) - np.array([query_views[i]['reserve_holdback'] for i in indices]) - np.array([query_views[i]['drawn_balance'] for i in indices])
                        pp = rankdata(pp) / len(pp)
                    if lane == 'recovery_tier':
                        # expected recovery becomes a within-cohort quartile per legal stage, the desk's published tier convention
                        stage = np.array([query_views[i]['legal_stage'] for i in indices])
                        tiers = np.zeros(len(indices))
                        for s in range(4):
                            members = np.where(stage == s)[0]
                            if len(members):
                                order = members[np.argsort(pp[members], kind='stable')]
                                tiers[order] = np.minimum(3, 4 * np.arange(len(order)) // len(order))
                        pp = tiers
                    for i, pred in zip(indices, pp):
                        bases[kind][i] = pred
            bases = {k: np.asarray(v) for k, v in bases.items()}
            y = np.array([r[lane] for r in history])
            if lane == 'dilution_reserve':
                y = y / np.array([r['open_balance'] for r in query_views[:len(history)]])
            if lane == 'loss_reserve':
                y = y / np.array([r['exposure'] * max(1e-6, 1 - r['insured_share']) for r in query_views[:len(history)]])
            if lane == 'availability_rank':
                y = y.astype(float)
                for p in sorted({r['period'] for r in history}):
                    ix = [i for i, r in enumerate(history) if r['period'] == p]
                    y[ix] = 1.0 - rankdata(y[ix]) / len(ix)
            if lane == 'recovery_tier':
                y = y.astype(float)
            base_mean = (bases['extra'] + bases['boost']) / 2
            augmented = np.column_stack([x, base_mean])
            candidates = {k: v[:len(history)][val_mask] for k, v in bases.items()}
            candidates['blend'] = base_mean[:len(history)][val_mask]
            if lane == 'availability_rank':
                for name in ('extra', 'boost', 'blend'):
                    candidates[name + '_descending'] = 1.0 - candidates[name]
            for kind in ('extra', 'boost'):
                candidates['history_' + kind] = fit_predict(kind, augmented[:len(history)][train_mask], y[train_mask], augmented[:len(history)][val_mask], classification)
            chosen_threshold = 0.5

            def loss(pred, target):
                if lane == 'dispute_flag':
                    return -f1_score(target, pred[:, 1] >= 0.5, zero_division=0)
                if lane == 'recovery_tier':
                    return -f1_score(target.astype(int), np.clip(np.rint(pred), 0, 3).astype(int), average='macro', zero_division=0)
                if lane == 'availability_rank':
                    return -float(spearmanr(target, pred).statistic)
                if lane == 'collection_profile':
                    return float(np.mean(np.abs(pred - target)))
                return float(np.mean(np.abs(pred - target) / np.maximum(np.abs(target), 0.01)))

            losses = {k: loss(v, y[val_mask]) for k, v in candidates.items()}
            chosen = min(losses, key=lambda k: losses[k])
            if lane == 'dispute_flag':
                chosen, chosen_threshold = min(((k, t) for k in candidates for t in np.linspace(0.1, 0.9, 17)),
                                               key=lambda kt: -f1_score(y[val_mask], candidates[kt[0]][:, 1] >= kt[1], zero_division=0))
            if chosen.startswith('history_'):
                prediction = fit_predict(chosen.split('_', 1)[1], augmented[:len(history)], y, augmented[len(history):], classification)
            else:
                source = chosen.removesuffix('_descending')
                prediction = (base_mean if source == 'blend' else bases[source])[len(history):].copy()
                if chosen.endswith('_descending'):
                    prediction = 1.0 - prediction
            qv = query_views[len(history):]
            if lane == 'dispute_flag':
                prediction = (prediction[:, 1] >= chosen_threshold).astype(int)
            elif lane == 'recovery_tier':
                prediction = np.clip(np.rint(prediction), 0, 3).astype(int)
            elif lane == 'dilution_reserve':
                prediction = np.maximum(0.0, prediction) * np.array([r['open_balance'] for r in qv])
            elif lane == 'loss_reserve':
                prediction = np.maximum(0.0, prediction) * np.array([r['exposure'] * (1 - r['insured_share']) for r in qv])
            elif lane == 'collection_profile':
                prediction = np.maximum(prediction, 0)
                prediction /= np.maximum(1.0, prediction.sum(axis=1))[:, None]
            elif lane == 'availability_rank':
                for period in sorted({r['period'] for r in queries}):
                    ix = [i for i, r in enumerate(queries) if r['period'] == period]
                    prediction[ix] = len(ix) + 1 - rankdata(prediction[ix], method='min')  # higher expected headroom ranks first
            for row, value in zip(final, prediction):
                row[lane] = value.tolist() if hasattr(value, 'tolist') else value
            diagnostics[lane] = {'selected': chosen, 'history_validation_losses': losses, 'threshold': float(chosen_threshold) if lane == 'dispute_flag' else None}
            print(lane, diagnostics[lane]['selected'], flush=True)
        with output.open('w') as handle:
            for row in final:
                handle.write(json.dumps(row, allow_nan=False) + '\n')
        audit['selection'] = diagnostics
        audit['records'] = len(final)
    finally:
        with audit_path.open('w') as handle:
            json.dump(audit, handle, indent=2, allow_nan=False)
        print(json.dumps({k: v for k, v in audit.items() if k not in ('read_paths', 'selection')}), flush=True)


if __name__ == '__main__':
    main()
