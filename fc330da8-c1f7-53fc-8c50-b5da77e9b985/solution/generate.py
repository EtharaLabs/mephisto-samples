"""Private data construction for the dealer floorplan finance surveillance task.

Run with ``python3 -B solution/generate.py``; never copy this file into the agent image.
Every published input is a keyed draw under PUBLIC_KEY; the private key feeds audit
sentinels only. No graded value is a random draw: every graded value is the private
estimator in estimators.py applied to the published inputs.
"""
import hashlib
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimators  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / 'environment' / 'workspace'
HIDDEN = ROOT / 'tests' / 'hidden'
PUBLIC_KEY = 'floorplan-surveillance-public-v1-2026'
PRIVATE_KEY = 'private-audit-only-9e4b2c7d1a6f4e8b9c3d7a1f5e2b8c64'
LANES = estimators.LANES
BREAK = 14
DEALER_COUNT = 360
REFERENCE_COUNT = 80
EXTERNAL_COUNT = 90
PERIODS = list(range(1, 21))
HISTORY_PERIODS = (8, 10, 12)
QUERY_PERIODS = (16, 20)
TURN_UPPER_DAYS = [30, 60, 90, 120, 150, 180, 240, 365]
RESTATED_SHARE = 0.22


def keyed_rng(key, label):
    return random.Random(int.from_bytes(hashlib.sha256(f'{key}|{label}'.encode()).digest(), 'big'))


def expit(x):
    return 1.0 / (1.0 + math.exp(-x))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n' for r in rows))


def blend(base, draw, share=0.55):
    """Dealer-level persistence: a keyed dealer centre blended with a keyed period draw."""
    return share * base + (1 - share) * draw


# --- feature samplers (one per view) -------------------------------------------------------

def aging_features(rng, base=None):
    x = {'aged_share': rng.random() ** 1.2 * 0.6, 'days_supply': rng.uniform(20, 140), 'model_year_age': rng.uniform(0, 3),
         'demand_index': rng.random(), 'incentive_intensity': rng.random(), 'price_volatility': rng.uniform(0, 0.4),
         'segment': rng.randrange(4), 'franchise': rng.randrange(4)}
    if base is not None:
        for k in ('aged_share', 'days_supply', 'model_year_age', 'demand_index', 'incentive_intensity', 'price_volatility'):
            x[k] = blend(base[k], x[k])
        x['segment'], x['franchise'] = base['segment'], base['franchise']
    return x


def turn_features(rng, base=None):
    x = {'lot_velocity': rng.random(), 'demand_index': rng.random(), 'pricing_discipline': rng.random() ** 0.7,
         'marketing_spend_log': rng.uniform(6, 10), 'stock_age_mix': rng.random(), 'segment': rng.randrange(4), 'region': rng.randrange(4)}
    if base is not None:
        for k in ('lot_velocity', 'demand_index', 'pricing_discipline', 'marketing_spend_log', 'stock_age_mix'):
            x[k] = blend(base[k], x[k])
        x['segment'], x['region'] = base['segment'], base['region']
    return x


def audit_features(rng, base=None):
    x = {'audit_variance_rate': rng.uniform(0, 0.25), 'late_payoff_count': rng.randrange(7), 'days_since_audit': rng.uniform(0, 200),
         'cash_strain': rng.random(), 'insurance_lapses': rng.randrange(4), 'curtailment_misses': rng.randrange(5), 'franchise': rng.randrange(4)}
    if base is not None:
        for k in ('audit_variance_rate', 'days_since_audit', 'cash_strain'):
            x[k] = blend(base[k], x[k])
        x['franchise'] = base['franchise']
    return x


def reconciliation_features(rng, base=None):
    x = {'unit_count_log': rng.uniform(3, 6.5), 'reconciliation_lag': rng.uniform(0, 30), 'staff_turnover': rng.random(),
         'prior_findings': rng.randrange(6), 'location_count': 1 + rng.randrange(6), 'audit_stage': rng.randrange(4)}
    if base is not None:
        for k in ('unit_count_log', 'reconciliation_lag', 'staff_turnover'):
            x[k] = blend(base[k], x[k])
        x['location_count'], x['audit_stage'] = base['location_count'], base['audit_stage']
    return x


def line_features(rng, base=None):
    x = {'credit_line': round(math.exp(rng.uniform(12, 14.5)), 2), 'oem_incentive_phase': rng.random(), 'sales_momentum': rng.random(),
         'inventory_days': rng.uniform(20, 140), 'curtailment_backlog': rng.uniform(0, 0.3), 'payoff_lag': rng.uniform(0, 20),
         'franchise': rng.randrange(4), 'region': rng.randrange(4)}
    x['outstanding'] = round(x['credit_line'] * rng.uniform(0.45, 1.05), 2)
    x['pending_payoffs'] = round(x['credit_line'] * rng.uniform(0, 0.15), 2)
    if base is not None:
        for k in ('sales_momentum', 'inventory_days', 'curtailment_backlog', 'payoff_lag'):
            x[k] = blend(base[k], x[k])
        x['credit_line'] = base['credit_line']
        x['franchise'], x['region'] = base['franchise'], base['region']
        x['outstanding'] = round(x['credit_line'] * rng.uniform(0.45, 1.05), 2)
        x['pending_payoffs'] = round(x['credit_line'] * rng.uniform(0, 0.15), 2)
    return x


def repossession_features(rng, base=None):
    x = {'exposure': round(math.exp(rng.uniform(10, 13.5)), 2), 'collateral_coverage': rng.uniform(0.5, 1.3), 'dealer_cash_score': rng.random(),
         'market_stress': rng.random(), 'years_in_program': rng.uniform(0, 15), 'curtailment_compliance': rng.random(),
         'rating_band': rng.randrange(4), 'segment': rng.randrange(4)}
    if base is not None:
        for k in ('collateral_coverage', 'dealer_cash_score', 'market_stress', 'curtailment_compliance'):
            x[k] = blend(base[k], x[k])
        x['exposure'] = round(math.exp(blend(math.log(base['exposure']), math.log(x['exposure']))), 2)
        x['years_in_program'] = base['years_in_program']
        x['rating_band'], x['segment'] = base['rating_band'], base['segment']
    return x


# --- closed-case outcome processes (public, noisy realizations) -----------------------------

def haircut_outcome(rng, x, event):
    z = (-2.9 + 1.6 * x['aged_share'] + 0.012 * (x['days_supply'] - 80) + 0.35 * x['model_year_age'] - 1.3 * x['demand_index']
         + 0.6 * x['incentive_intensity'] + 2.0 * x['price_volatility'] + 0.25 * x['segment'] + 0.15 * (x['franchise'] == 2)
         + 0.5 * math.sin(2.0 * x['model_year_age'] + x['segment']) + 0.35 * (event >= BREAK) + 0.1 * math.sin(event / 2.5 + x['franchise'])
         + rng.gauss(0, 0.35))
    return round(min(0.5, max(0.002, expit(z))), 6)


def turn_outcome(rng, x, event):
    censor = rng.choices([3, 4, 5, 6, 7], [1, 1, 1, 1, 10])[0]
    sold = -1
    for b in range(censor + 1):
        z = (0.4 + 0.25 * b + 2.4 * x['lot_velocity'] + 1.8 * x['demand_index'] + 1.2 * x['pricing_discipline']
             + 0.25 * (x['marketing_spend_log'] - 8) - 2.0 * x['stock_age_mix'] + 0.3 * math.sin(x['region'] + b / 2) - 0.4 * x['segment']
             - 0.5 * (event >= BREAK) + 0.7 * (x['stock_age_mix'] > 0.6 and b > 3) - 1.0 * (x['lot_velocity'] < 0.25 and b < 2))
        if rng.random() < expit(z - 2.0):
            sold = b
            break
    return sold, (sold if sold >= 0 else censor)


def sot_outcome(rng, x, event):
    z = (-7.6 + 7.0 * x['audit_variance_rate'] + 0.45 * x['late_payoff_count'] + 0.005 * x['days_since_audit'] + 2.2 * x['cash_strain']
         + 0.5 * x['insurance_lapses'] + 0.35 * x['curtailment_misses'] + 0.3 * (x['franchise'] == 3)
         + 1.3 * (x['cash_strain'] > 0.6 and x['curtailment_misses'] >= 2) + 0.3 * (event >= BREAK))
    return int(rng.random() < expit(z))


def variance_outcome(rng, x, event):
    z = (-6.4 + 0.35 * (x['unit_count_log'] - 4.5) + 0.04 * x['reconciliation_lag'] + 1.6 * x['staff_turnover'] + 0.3 * x['prior_findings']
         + 0.15 * x['location_count'] + 0.4 * x['audit_stage'] + 0.5 * math.sin(x['staff_turnover'] * 4 + x['audit_stage'])
         + 0.3 * (event >= BREAK) + rng.gauss(0, 0.6))
    return round(min(1.0, max(0.0, expit(z))), 6)


def line_outcome(rng, x, event, latent=0.0):
    """A dealer carries a persistent latent line effect that no snapshot field reports; it is visible only through that dealer's own completed facility periods."""
    z = (1.4 + latent + 1.8 * x['sales_momentum'] - 0.012 * (x['inventory_days'] - 80) - 2.4 * x['curtailment_backlog'] - 0.05 * x['payoff_lag']
         + 0.6 * math.cos(2 * math.pi * x['oem_incentive_phase'] + x['franchise']) + 0.8 * x['sales_momentum'] * x['curtailment_backlog']
         - 0.15 * (x['region'] == 2) - 0.25 * (event >= BREAK) + rng.gauss(0, 0.25))
    return round(min(0.98, max(0.05, expit(z))), 6)


def loss_outcome(rng, x, event):
    p = expit(-2.6 - 2.2 * x['dealer_cash_score'] + 2.0 * x['market_stress'] - 0.06 * x['years_in_program'] - 1.0 * x['curtailment_compliance']
              + 0.45 * x['rating_band'] + 0.5 * (event >= BREAK))
    if rng.random() >= p:
        return 0.0
    rate = expit(-1.0 + 1.1 * x['market_stress'] - 0.8 * x['dealer_cash_score'] + 0.3 * x['rating_band'] - 0.6 * (x['collateral_coverage'] - 0.9) + rng.gauss(0, 0.6))
    return round(x['exposure'] * rate, 2)


# --- as-of ledger mechanics -----------------------------------------------------------------

def book(rng, row, event, outcome_fields):
    """Attach the ledger timing. A restated row carries its original values under as_booked."""
    row['event_period'] = event
    row['booked_period'] = min(20, event + rng.choices([0, 1, 2], [6, 3, 1])[0])
    if rng.random() < RESTATED_SHARE:
        restated = row['booked_period'] + 1 + rng.randrange(6)
        if restated <= 20:
            original = {}
            for field in outcome_fields:
                value = row[field]
                if field in ('haircut_ratio', 'variance_fraction', 'available_fraction'):
                    factor = math.exp(rng.gauss(0, 0.7))
                    cap, floor = {'haircut_ratio': (0.5, 0.002), 'variance_fraction': (1.0, 0.0), 'available_fraction': (0.98, 0.05)}[field]
                    original[field] = round(min(cap, max(floor, value * factor)), 6)
                elif field == 'loss_amount':
                    original[field] = 0.0 if (value > 0 and rng.random() < 0.5) else round(value * math.exp(rng.gauss(0, 0.5)) if value > 0 else row['exposure'] * rng.uniform(0.05, 0.4), 2)
                elif field == 'sot_event':
                    original[field] = 1 - value
                elif field == 'sold_bucket':
                    shift = rng.choice([-3, -2, -1, 1, 2, 3])
                    original[field] = -1 if value < 0 else max(0, min(7, value + shift))
                elif field == 'last_observed_bucket':
                    original[field] = original.get('sold_bucket', row['last_observed_bucket'])
                    if original[field] < 0:
                        original[field] = row['last_observed_bucket']
            row['restated_period'] = restated
            row['as_booked'] = original
    return row


# --- generation -----------------------------------------------------------------------------

def generate_inputs():
    ids = [f'DL{i:04d}' for i in range(DEALER_COUNT)]
    refs = ids[:REFERENCE_COUNT]
    queries = [{'record_id': f'{a}:p{q}', 'dealer_id': a, 'period': q} for q in QUERY_PERIODS for a in ids[REFERENCE_COUNT:]]
    write_rows(WORKSPACE / 'queries.jsonl', queries)
    write_json(WORKSPACE / 'dataset_metadata.json', {
        'public_generation_key': PUBLIC_KEY, 'periods': PERIODS, 'reference_dealers': refs, 'currency': 'USD',
        'turn_bucket_upper_days': TURN_UPPER_DAYS, 'history_periods': list(HISTORY_PERIODS),
        'query_periods': list(QUERY_PERIODS), 'period_unit': 'month',
        'variance_tiers': ['clean', 'minor', 'material', 'severe'], 'variance_tier_cuts': list(estimators.VARIANCE_CUTS),
        'snapshots': 'Month-end observations; a closed row completed before the snapshot it is filed beside.',
        'ledger': 'Closed rows carry booked_period, and a corrected row carries restated_period with as_booked.'})
    bases = {}
    for a in ids:
        rng = keyed_rng(PUBLIC_KEY, f'register|{a}')
        bases[a] = {
            'aging': aging_features(keyed_rng(PUBLIC_KEY, f'base|aging|{a}')),
            'turns': turn_features(keyed_rng(PUBLIC_KEY, f'base|turns|{a}')),
            'audits': audit_features(keyed_rng(PUBLIC_KEY, f'base|audits|{a}')),
            'reconciliations': reconciliation_features(keyed_rng(PUBLIC_KEY, f'base|reconciliations|{a}')),
            'lines': line_features(keyed_rng(PUBLIC_KEY, f'base|lines|{a}')),
            'line_latent': keyed_rng(PUBLIC_KEY, f'latent|lines|{a}').gauss(0, 0.6),
            'repossessions': repossession_features(keyed_rng(PUBLIC_KEY, f'base|repossessions|{a}'))}
        # one franchise, region and segment per dealer across the views that carry them
        franchise, region, segment = bases[a]['lines']['franchise'], bases[a]['lines']['region'], bases[a]['aging']['segment']
        bases[a]['aging']['franchise'] = franchise
        bases[a]['turns']['segment'], bases[a]['turns']['region'] = segment, region
        bases[a]['audits']['franchise'] = franchise
        bases[a]['repossessions']['segment'] = segment
        write_json(WORKSPACE / 'register' / f'{a}.json', {
            'dealer_id': a, 'franchise': franchise, 'region': region, 'segment': segment,
            'rating_band': bases[a]['repossessions']['rating_band'], 'audit_stage': bases[a]['reconciliations']['audit_stage'],
            'program_entry_period': -rng.randrange(48), 'credit_line': bases[a]['lines']['credit_line'],
            'location_count': bases[a]['reconciliations']['location_count'], 'cohort': 'reference' if a in refs else 'query'})
    # dealer-keyed views: audits and repossessions
    for a in ids:
        audits, repossessions = [], []
        for q in PERIODS:
            x = audit_features(keyed_rng(PUBLIC_KEY, f'audits|snapshot|{a}|{q}'), bases[a]['audits'])
            audits.append(dict(x, dealer_id=a, period=q, kind='snapshot'))
            x = repossession_features(keyed_rng(PUBLIC_KEY, f'repossessions|snapshot|{a}|{q}'), bases[a]['repossessions'])
            x['years_in_program'] = round(min(15.0, bases[a]['repossessions']['years_in_program'] + q / 12), 4)
            repossessions.append(dict(x, dealer_id=a, period=q, kind='snapshot'))
            if int(a[2:]) < EXTERNAL_COUNT:
                rng = keyed_rng(PUBLIC_KEY, f'audits|closed|{a}|{q}')
                x = audit_features(rng)
                row = dict(x, case_id=f'AU{a[2:]}-{q}', kind='closed', sot_event=sot_outcome(rng, x, q))
                audits.append(book(rng, row, q, ['sot_event']))
                rng = keyed_rng(PUBLIC_KEY, f'repossessions|closed|{a}|{q}')
                x = repossession_features(rng)
                row = dict(x, case_id=f'RP{a[2:]}-{q}', kind='closed', loss_amount=loss_outcome(rng, x, q))
                repossessions.append(book(rng, row, q, ['loss_amount']))
        write_rows(WORKSPACE / 'audits' / f'{a}.jsonl', audits)
        write_rows(WORKSPACE / 'repossessions' / f'{a}.jsonl', repossessions)
    # period-keyed views: aging, turns, reconciliations, lines
    filed = {name: {q: [] for q in PERIODS} for name in ('aging', 'turns', 'reconciliations', 'lines')}
    for q in PERIODS:
        for i in range(100):
            rng = keyed_rng(PUBLIC_KEY, f'aging|closed|{q}|{i}')
            x = aging_features(rng)
            row = dict(x, case_id=f'AG{q}-{i}', kind='closed', aged_balance=round(math.exp(rng.uniform(9.5, 13.0)), 2),
                       haircut_ratio=haircut_outcome(rng, x, q))
            book(rng, row, q, ['haircut_ratio'])
            filed['aging'][row['booked_period']].append(row)
            rng = keyed_rng(PUBLIC_KEY, f'turns|closed|{q}|{i}')
            x = turn_features(rng)
            sold, last = turn_outcome(rng, x, q)
            row = dict(x, case_id=f'TN{q}-{i}', kind='closed', sold_bucket=sold, last_observed_bucket=last)
            book(rng, row, q, ['sold_bucket', 'last_observed_bucket'])
            filed['turns'][row['booked_period']].append(row)
            rng = keyed_rng(PUBLIC_KEY, f'reconciliations|closed|{q}|{i}')
            x = reconciliation_features(rng)
            row = dict(x, case_id=f'RC{q}-{i}', kind='closed', variance_fraction=variance_outcome(rng, x, q))
            book(rng, row, q, ['variance_fraction'])
            filed['reconciliations'][row['booked_period']].append(row)
        # the line view's closed rows are each dealer's own completed facility periods
        for a in ids:
            rng = keyed_rng(PUBLIC_KEY, f'lines|closed|{a}|{q}')
            x = line_features(rng, bases[a]['lines'])
            row = dict(x, dealer_id=a, case_id=f'LN{a[2:]}-{q}', kind='closed', available_fraction=line_outcome(rng, x, q, bases[a]['line_latent']))
            book(rng, row, q, ['available_fraction'])
            filed['lines'][row['booked_period']].append(row)
    for q in PERIODS:
        for name, sampler in (('aging', aging_features), ('turns', turn_features),
                              ('reconciliations', reconciliation_features), ('lines', line_features)):
            rows = list(filed[name][q])
            for a in ids:
                x = sampler(keyed_rng(PUBLIC_KEY, f'{name}|snapshot|{a}|{q}'), bases[a][name])
                if name == 'aging':
                    x['floored_balance'] = round(math.exp(blend(12.3, keyed_rng(PUBLIC_KEY, f'aging|balance|{a}|{q}').uniform(11.0, 14.0), 0.5)), 2)
                if name == 'lines':
                    x['cohort'] = 'reference' if a in refs else 'query'
                rows.append(dict(x, dealer_id=a, period=q, kind='snapshot'))
            write_rows(WORKSPACE / name / f'{q}.jsonl', rows)
    return refs, queries


def main():
    refs, queries = generate_inputs()
    fitted = {lane: getattr(estimators, 'fit_' + lane)(WORKSPACE) for lane in LANES}

    def predict(a, q):
        return dict(record_id=f'{a}:p{q}', **{lane: getattr(estimators, 'predict_' + lane)(fitted[lane], a, q, WORKSPACE) for lane in LANES})

    history = [dict(predict(a, q), dealer_id=a, period=q) for q in HISTORY_PERIODS for a in refs]
    truth = [predict(r['dealer_id'], r['period']) for r in queries]
    write_rows(WORKSPACE / 'history' / 'surveillance.jsonl', history)
    write_rows(HIDDEN / 'truth.jsonl', truth)
    headroom = [{'record_id': r['record_id'], 'undrawn_headroom': estimators.headroom_value(fitted['headroom_rank'], r['dealer_id'], r['period'])} for r in queries]
    write_rows(ROOT / 'solution' / 'measurements' / 'headroom_values.jsonl', headroom)
    sentinel = keyed_rng(PRIVATE_KEY, 'audit|sentinel').random()
    report = {'generated': True, 'dealers': DEALER_COUNT, 'periods': len(PERIODS), 'reference_dealers': len(refs),
              'history_rows': len(history), 'graded_rows': len(truth), 'private_sentinel_sha256': hashlib.sha256(repr(sentinel).encode()).hexdigest(),
              'label_balance': {
                  'sot_flag': sum(r['sot_flag'] for r in truth) / len(truth),
                  'variance_tier': [sum(r['variance_tier'] == c for r in truth) for c in range(4)],
                  'unsold_mass_mean': sum(1 - sum(r['turn_profile']) for r in truth) / len(truth)},
              'fit_diagnostics': {
                  'aging_rounds': {str(q): len(fitted['aging_reserve']['models'][q]['stumps']) for q in estimators.FIT_PERIODS},
                  'turn_expanded_rows': {str(q): fitted['turn_profile']['models'][q]['expanded_rows'] for q in estimators.FIT_PERIODS},
                  'sot_threshold': {str(q): fitted['sot_flag']['models'][q]['threshold'] for q in estimators.FIT_PERIODS},
                  'variance_theta': {str(q): fitted['variance_tier']['models'][q]['theta'] for q in estimators.FIT_PERIODS}}}
    write_json(ROOT / 'solution' / 'measurements' / 'generator_report.json', report)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
