"""Frozen one-shot competent fits on the public workspace, under a strict file-access audit.

Two one-shot tiers, each a single default scikit-learn fit with no search and no refinement:
  * oneshot_<lane>         a RandomForest on the lane's snapshot view fitted to the published
                           surveillance history labels (the honest analogue of a competent opening
                           attempt that treats history as a labelled training set);
  * oneshot_closed_<lane>  a RandomForest on the lane's closed cases at their current ledger
                           values, mapped to the record quantity (the honest analogue of a
                           competent opening attempt that fits the closed cases naively).
Imports precede the audit; every later file open must be a read inside the public workspace.
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer

from cheap_portfolio import generate

LANES = ('dilution_reserve', 'collection_profile', 'dispute_flag', 'recovery_tier', 'availability_rank', 'loss_reserve')
VIEWS = dict(zip(LANES, ('dilution', 'collections', 'disputes', 'delinquencies', 'borrowing_base', 'writeoffs')))
CATEGORICAL = ('product_mix', 'channel', 'region', 'contract_type', 'legal_stage', 'advance_band', 'rating_band', 'terms_days')
OUTCOMES = {'dilution_reserve': 'dilution_ratio', 'collection_profile': 'paid_bucket', 'dispute_flag': 'escalated',
            'recovery_tier': 'recovered_fraction', 'availability_rank': 'availability_ratio', 'loss_reserve': 'loss_amount'}
LEDGER = ('event_period', 'booked_period', 'restated_period', 'as_booked', 'case_id', 'kind', 'period', 'obligor_id')


def read(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def features(row):
    out = {}
    for k, v in row.items():
        if k in LEDGER or k in OUTCOMES.values() or k == 'last_observed_bucket' or k == 'cohort':
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        out[k] = str(v) if k in CATEGORICAL else float(v)
    return out


def load(workspace):
    history = read(workspace / 'history/surveillance.jsonl')
    queries = read(workspace / 'queries.jsonl')
    assert max(r['period'] for r in history) < min(r['period'] for r in queries)
    views, closed = {}, {}
    for view in VIEWS.values():
        table, cases = {}, []
        for path in sorted((workspace / view).glob('*.jsonl')):
            for row in read(path):
                if row.get('kind') == 'snapshot':
                    table[row['obligor_id'], row['period']] = row
                elif row.get('kind') == 'closed':
                    cases.append(row)
        views[view], closed[view] = table, cases
    return history, queries, views, closed


def rank_within(queries, values):
    out = list(values)
    for period in sorted({r['period'] for r in queries}):
        idx = [i for i, r in enumerate(queries) if r['period'] == period]
        order = {v: j + 1 for j, v in enumerate(sorted({out[i] for i in idx}, reverse=True))}
        for i in idx:
            out[i] = order[out[i]]
    return out


def fit_history_tier(history, queries, views):
    predictions = {}
    records = history + queries
    for lane in LANES:
        vec = DictVectorizer(sparse=False)
        rows = [features(views[VIEWS[lane]][r['obligor_id'], r['period']]) for r in records]
        x_train, x_query = vec.fit_transform(rows[:len(history)]), vec.transform(rows[len(history):])
        if lane == 'collection_profile':
            y = np.asarray([r[lane] for r in history])
            est = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, y)
            values = np.maximum(est.predict(x_query), 0.0)
            values /= np.maximum(1.0, values.sum(axis=1))[:, None]
            values = values.tolist()
        else:
            cls = lane in ('dispute_flag', 'recovery_tier')
            est = (RandomForestClassifier if cls else RandomForestRegressor)(random_state=0, n_jobs=1)
            est.fit(x_train, np.asarray([r[lane] for r in history]))
            values = est.predict(x_query).tolist()
            if lane == 'availability_rank':
                values = rank_within(queries, [-v for v in values])
        predictions['oneshot_' + lane] = [dict(record_id=r['record_id'], **{lane: v}) for r, v in zip(queries, values)]
        if lane in ('dilution_reserve', 'loss_reserve'):
            # the same default fit on a scale-free target, the other natural opening move for a currency lane
            def scale(view_row):
                return view_row['open_balance'] if lane == 'dilution_reserve' else view_row['exposure'] * max(1e-6, 1 - view_row['insured_share'])
            est = RandomForestRegressor(random_state=0, n_jobs=1)
            est.fit(x_train, np.asarray([r[lane] / scale(views[VIEWS[lane]][r['obligor_id'], r['period']]) for r in history]))
            scaled = [round(float(v) * scale(views[VIEWS[lane]][r['obligor_id'], r['period']]), 2) for v, r in zip(est.predict(x_query), queries)]
            predictions['oneshot_' + lane + '_normalised'] = [dict(record_id=r['record_id'], **{lane: v}) for r, v in zip(queries, scaled)]
    return predictions


def fit_closed_tier(queries, views, closed):
    predictions = {}
    for lane in LANES:
        view = VIEWS[lane]
        values = [None] * len(queries)
        for period in sorted({r['period'] for r in queries}):
            cases = [c for c in closed[view] if c['booked_period'] < period]
            idx = [i for i, r in enumerate(queries) if r['period'] == period]
            snaps = [views[view][queries[i]['obligor_id'], period] for i in idx]
            vec = DictVectorizer(sparse=False)
            x_train = vec.fit_transform([features(c) for c in cases])
            x_query = vec.transform([features(s) for s in snaps])
            if lane == 'dilution_reserve':
                est = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['dilution_ratio'] for c in cases])
                out = [round(float(p) * s['open_balance'], 2) for p, s in zip(est.predict(x_query), snaps)]
            elif lane == 'collection_profile':
                survival = np.ones(len(idx))
                profile = np.zeros((len(idx), 8))
                for b in range(8):
                    risk = [c for c in cases if c['last_observed_bucket'] >= b and (c['paid_bucket'] < 0 or c['paid_bucket'] >= b)]
                    xr = vec.transform([features(c) for c in risk])
                    event = np.asarray([int(c['paid_bucket'] == b) for c in risk])
                    est = RandomForestClassifier(random_state=0, n_jobs=1).fit(xr, event)
                    hazard = est.predict_proba(x_query)[:, list(est.classes_).index(1)] if 1 in est.classes_ else np.zeros(len(idx))
                    profile[:, b] = survival * hazard
                    survival *= 1 - hazard
                out = profile.tolist()
            elif lane == 'dispute_flag':
                est = RandomForestClassifier(random_state=0, n_jobs=1).fit(x_train, [c['escalated'] for c in cases])
                out = [int(v) for v in est.predict(x_query)]
                proba = est.predict_proba(x_query)[:, list(est.classes_).index(1)]
                prevalence = sum(c['escalated'] for c in cases) / len(cases)
                cut = sorted(proba, reverse=True)[max(0, int(round(prevalence * len(proba))) - 1)]
                predictions.setdefault('oneshot_closed_dispute_prevalence', [None] * len(queries))
                for i, v in zip(idx, proba):
                    predictions['oneshot_closed_dispute_prevalence'][i] = dict(record_id=queries[i]['record_id'], dispute_flag=int(v >= cut))
            elif lane == 'recovery_tier':
                reg = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['recovered_fraction'] for c in cases])
                out = [min(3, int(round(3 * float(v)))) for v in reg.predict(x_query)]
                scores = reg.predict(x_query)
                quart = [0] * len(idx)
                for stage in range(4):
                    members = [j for j, s in enumerate(snaps) if s['legal_stage'] == stage]
                    ordered = sorted(members, key=lambda j: (scores[j], snaps[j]['obligor_id']))
                    for pos, j in enumerate(ordered):
                        quart[j] = min(3, 4 * pos // len(ordered))
                predictions.setdefault('oneshot_closed_recovery_quartile', [None] * len(queries))
                for i, v in zip(idx, quart):
                    predictions['oneshot_closed_recovery_quartile'][i] = dict(record_id=queries[i]['record_id'], recovery_tier=v)
            elif lane == 'availability_rank':
                est = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['availability_ratio'] for c in cases])
                nets = [float(p) * s['gross_receivables'] - s['reserve_holdback'] - s['drawn_balance'] for p, s in zip(est.predict(x_query), snaps)]
                order = {v: j + 1 for j, v in enumerate(sorted(set(nets), reverse=True))}
                out = [order[v] for v in nets]
            else:
                clf = RandomForestClassifier(random_state=0, n_jobs=1).fit(x_train, [int(c['loss_amount'] > 0) for c in cases])
                p = clf.predict_proba(x_query)[:, list(clf.classes_).index(1)]
                pos = [c for c in cases if c['loss_amount'] > 0]
                reg = RandomForestRegressor(random_state=0, n_jobs=1).fit(vec.transform([features(c) for c in pos]),
                                                                          [math.log(c['loss_amount'] / c['exposure']) for c in pos])
                rate = np.exp(reg.predict(x_query))
                out = [round(float(pi * ri) * s['exposure'] * (1 - s['insured_share']), 2) for pi, ri, s in zip(p, rate, snaps)]
                direct = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['loss_amount'] / c['exposure'] for c in cases])
                predictions.setdefault('oneshot_closed_loss_direct', [None] * len(queries))
                for i, v, s in zip(idx, direct.predict(x_query), snaps):
                    predictions['oneshot_closed_loss_direct'][i] = dict(record_id=queries[i]['record_id'], loss_reserve=round(max(0.0, float(v)) * s['exposure'] * (1 - s['insured_share']), 2))
            for i, v in zip(idx, out):
                values[i] = v
        predictions['oneshot_closed_' + lane] = [dict(record_id=r['record_id'], **{lane: v}) for r, v in zip(queries, values)]
    return predictions


def main():
    workspace = Path(sys.argv[1]).resolve(strict=True)
    audit = {'permitted_reads': 0, 'violations': 0, 'paths': {}}

    def hook(event, args):
        if event != 'open':
            return
        path, mode, flags = args
        resolved = None if isinstance(path, int) else Path(os.fsdecode(path)).resolve()
        allowed = (resolved is not None and resolved.is_relative_to(workspace)
                   and not (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)))
        if not allowed:
            audit['violations'] += 1
            raise PermissionError(f'one-shot file access denied: {path}')
        audit['permitted_reads'] += 1
        key = str(resolved.relative_to(workspace))
        audit['paths'][key] = audit['paths'].get(key, 0) + 1

    sys.addaudithook(hook)
    mode = sys.argv[2] if len(sys.argv) > 2 else 'oneshot'
    if mode == 'cheap':
        methods, controls = generate(workspace)
        output = {'methods': methods, 'controls': controls}
    else:
        history, queries, views, closed = load(workspace)
        methods = fit_history_tier(history, queries, views)
        methods.update(fit_closed_tier(queries, views, closed))
        output = {'methods': methods, 'views': VIEWS}
    print(json.dumps(dict(output, audit=audit), allow_nan=False))


if __name__ == '__main__':
    main()
