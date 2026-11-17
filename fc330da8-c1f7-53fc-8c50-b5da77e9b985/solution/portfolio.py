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

LANES = ('aging_reserve', 'turn_profile', 'sot_flag', 'variance_tier', 'headroom_rank', 'loss_reserve')
VIEWS = dict(zip(LANES, ('aging', 'turns', 'audits', 'reconciliations', 'lines', 'repossessions')))
CATEGORICAL = ('segment', 'franchise', 'region', 'audit_stage', 'rating_band')
OUTCOMES = {'aging_reserve': 'haircut_ratio', 'turn_profile': 'sold_bucket', 'sot_flag': 'sot_event',
            'variance_tier': 'variance_fraction', 'headroom_rank': 'available_fraction', 'loss_reserve': 'loss_amount'}
LEDGER = ('event_period', 'booked_period', 'restated_period', 'as_booked', 'case_id', 'kind', 'period', 'dealer_id',
          'last_observed_bucket', 'cohort', 'aged_balance', 'floored_balance')
VARIANCE_CUTS = (0.02, 0.05, 0.10)


def tier_of(value):
    return sum(value > c for c in VARIANCE_CUTS)


def read(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def features(row):
    out = {}
    for k, v in row.items():
        if k in LEDGER or k in OUTCOMES.values():
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
                    table[row['dealer_id'], row['period']] = row
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


def aging_scale(view_row):
    return view_row['floored_balance'] * view_row['aged_share']


def fit_history_tier(history, queries, views):
    predictions = {}
    records = history + queries
    for lane in LANES:
        vec = DictVectorizer(sparse=False)
        rows = [features(views[VIEWS[lane]][r['dealer_id'], r['period']]) for r in records]
        x_train, x_query = vec.fit_transform(rows[:len(history)]), vec.transform(rows[len(history):])
        if lane == 'turn_profile':
            y = np.asarray([r[lane] for r in history])
            est = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, y)
            values = np.maximum(est.predict(x_query), 0.0)
            values /= np.maximum(1.0, values.sum(axis=1))[:, None]
            values = values.tolist()
        else:
            cls = lane in ('sot_flag', 'variance_tier')
            est = (RandomForestClassifier if cls else RandomForestRegressor)(random_state=0, n_jobs=1)
            est.fit(x_train, np.asarray([r[lane] for r in history]))
            values = est.predict(x_query).tolist()
            if lane == 'headroom_rank':
                values = rank_within(queries, [-v for v in values])
        predictions['oneshot_' + lane] = [dict(record_id=r['record_id'], **{lane: v}) for r, v in zip(queries, values)]
        if lane in ('aging_reserve', 'loss_reserve'):
            # the same default fit on a scale-free target, the other natural opening move for a currency lane
            def scale(view_row):
                return aging_scale(view_row) if lane == 'aging_reserve' else view_row['exposure']
            est = RandomForestRegressor(random_state=0, n_jobs=1)
            est.fit(x_train, np.asarray([r[lane] / scale(views[VIEWS[lane]][r['dealer_id'], r['period']]) for r in history]))
            scaled = [round(float(v) * scale(views[VIEWS[lane]][r['dealer_id'], r['period']]), 2) for v, r in zip(est.predict(x_query), queries)]
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
            snaps = [views[view][queries[i]['dealer_id'], period] for i in idx]
            vec = DictVectorizer(sparse=False)
            x_train = vec.fit_transform([features(c) for c in cases])
            x_query = vec.transform([features(s) for s in snaps])
            if lane == 'aging_reserve':
                est = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['haircut_ratio'] for c in cases])
                out = [round(float(p) * aging_scale(s), 2) for p, s in zip(est.predict(x_query), snaps)]
            elif lane == 'turn_profile':
                survival = np.ones(len(idx))
                profile = np.zeros((len(idx), 8))
                for b in range(8):
                    risk = [c for c in cases if c['last_observed_bucket'] >= b and (c['sold_bucket'] < 0 or c['sold_bucket'] >= b)]
                    xr = vec.transform([features(c) for c in risk])
                    event = np.asarray([int(c['sold_bucket'] == b) for c in risk])
                    est = RandomForestClassifier(random_state=0, n_jobs=1).fit(xr, event)
                    hazard = est.predict_proba(x_query)[:, list(est.classes_).index(1)] if 1 in est.classes_ else np.zeros(len(idx))
                    profile[:, b] = survival * hazard
                    survival *= 1 - hazard
                out = profile.tolist()
            elif lane == 'sot_flag':
                est = RandomForestClassifier(random_state=0, n_jobs=1).fit(x_train, [c['sot_event'] for c in cases])
                out = [int(v) for v in est.predict(x_query)]
                proba = est.predict_proba(x_query)[:, list(est.classes_).index(1)]
                prevalence = sum(c['sot_event'] for c in cases) / len(cases)
                cut = sorted(proba, reverse=True)[max(0, int(round(prevalence * len(proba))) - 1)]
                predictions.setdefault('oneshot_closed_sot_prevalence', [None] * len(queries))
                for i, v in zip(idx, proba):
                    predictions['oneshot_closed_sot_prevalence'][i] = dict(record_id=queries[i]['record_id'], sot_flag=int(v >= cut))
            elif lane == 'variance_tier':
                reg = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['variance_fraction'] for c in cases])
                out = [tier_of(float(v)) for v in reg.predict(x_query)]
                clf = RandomForestClassifier(random_state=0, n_jobs=1).fit(x_train, [tier_of(c['variance_fraction']) for c in cases])
                predictions.setdefault('oneshot_closed_variance_classifier', [None] * len(queries))
                for i, v in zip(idx, clf.predict(x_query)):
                    predictions['oneshot_closed_variance_classifier'][i] = dict(record_id=queries[i]['record_id'], variance_tier=int(v))
            elif lane == 'headroom_rank':
                est = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['available_fraction'] for c in cases])
                headroom = [float(p) * s['credit_line'] - s['outstanding'] - s['pending_payoffs'] for p, s in zip(est.predict(x_query), snaps)]
                order = {v: j + 1 for j, v in enumerate(sorted(set(headroom), reverse=True))}
                out = [order[v] for v in headroom]
            else:
                clf = RandomForestClassifier(random_state=0, n_jobs=1).fit(x_train, [int(c['loss_amount'] > 0) for c in cases])
                p = clf.predict_proba(x_query)[:, list(clf.classes_).index(1)]
                pos = [c for c in cases if c['loss_amount'] > 0]
                reg = RandomForestRegressor(random_state=0, n_jobs=1).fit(vec.transform([features(c) for c in pos]),
                                                                          [math.log(c['loss_amount'] / c['exposure']) for c in pos])
                rate = np.exp(reg.predict(x_query))
                out = [round(float(pi * ri) * s['exposure'], 2) for pi, ri, s in zip(p, rate, snaps)]
                direct = RandomForestRegressor(random_state=0, n_jobs=1).fit(x_train, [c['loss_amount'] / c['exposure'] for c in cases])
                predictions.setdefault('oneshot_closed_loss_direct', [None] * len(queries))
                for i, v, s in zip(idx, direct.predict(x_query), snaps):
                    predictions['oneshot_closed_loss_direct'][i] = dict(record_id=queries[i]['record_id'], loss_reserve=round(max(0.0, float(v)) * s['exposure'], 2))
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
