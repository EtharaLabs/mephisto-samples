"""Private data construction for the receivables finance surveillance task.

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
PUBLIC_KEY = 'receivables-surveillance-public-v1-2026'
PRIVATE_KEY = 'private-audit-only-5c1d9e0a7b3f4e2d8a6c1b9f0e3d7a52'
LANES = estimators.LANES
BREAK = 14
OBLIGOR_COUNT = 360
REFERENCE_COUNT = 80
EXTERNAL_COUNT = 90
PERIODS = list(range(1, 21))
HISTORY_PERIODS = (8, 10, 12)
QUERY_PERIODS = (16, 20)
BUCKET_UPPER_DAYS = [15, 30, 45, 60, 90, 120, 180, 270]
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
    """Obligor-level persistence: a keyed obligor centre blended with a keyed period draw."""
    return share * base + (1 - share) * draw


# --- feature samplers (one per view) -------------------------------------------------------

def dilution_features(rng, base=None):
    x = {'promo_intensity': rng.random(), 'return_propensity': rng.random(),
         'pricing_dispute_index': rng.uniform(0, 2), 'invoice_size_log': rng.uniform(7, 11),
         'terms_days': rng.choice([30, 45, 60, 90]), 'product_mix': rng.randrange(4), 'channel': rng.randrange(3)}
    if base is not None:
        for k in ('promo_intensity', 'return_propensity', 'pricing_dispute_index', 'invoice_size_log'):
            x[k] = blend(base[k], x[k])
        x['product_mix'], x['channel'], x['terms_days'] = base['product_mix'], base['channel'], base['terms_days']
    return x


def collection_features(rng, base=None):
    x = {'terms_days': rng.choice([30, 45, 60, 90]), 'past_due_share': rng.random() ** 1.5,
         'dispute_share': rng.random() ** 2, 'payment_regularity': rng.random(),
         'remittance_lag': rng.uniform(0, 20), 'region': rng.randrange(4)}
    if base is not None:
        for k in ('past_due_share', 'dispute_share', 'payment_regularity', 'remittance_lag'):
            x[k] = blend(base[k], x[k])
        x['terms_days'], x['region'] = base['terms_days'], base['region']
    return x


def dispute_features(rng, base=None):
    x = {'open_dispute_count': rng.randrange(7), 'invoice_error_rate': rng.uniform(0, 0.3),
         'po_mismatch_rate': rng.uniform(0, 0.4), 'days_since_last_dispute': rng.uniform(0, 400),
         'contact_responsiveness': rng.random(), 'contract_type': rng.randrange(4)}
    if base is not None:
        for k in ('invoice_error_rate', 'po_mismatch_rate', 'days_since_last_dispute', 'contact_responsiveness'):
            x[k] = blend(base[k], x[k])
        x['contract_type'] = base['contract_type']
    return x


def delinquency_features(rng, base=None):
    x = {'days_past_due': rng.uniform(0, 180), 'secured_share': rng.random(), 'guarantor_strength': rng.random(),
         'prior_cures': rng.randrange(5), 'legal_stage': rng.randrange(4), 'exposure_log': rng.uniform(9, 13)}
    if base is not None:
        for k in ('days_past_due', 'secured_share', 'guarantor_strength', 'exposure_log'):
            x[k] = blend(base[k], x[k])
        x['legal_stage'] = base['legal_stage']
    return x


def borrowing_features(rng, base=None):
    x = {'gross_receivables': round(math.exp(rng.uniform(11.5, 13.5)), 2), 'ineligible_share': rng.uniform(0, 0.5),
         'concentration_index': rng.random(), 'cross_aged_share': rng.uniform(0, 0.3),
         'insurance_coverage': rng.random(), 'advance_band': rng.randrange(4), 'seasonality_phase': rng.random(),
         'dilution_history': rng.uniform(0, 0.15), 'reserve_holdback': round(rng.uniform(0, 40000), 2)}
    x['drawn_balance'] = round(x['gross_receivables'] * (0.60 + 0.05 * x['advance_band']) * rng.uniform(0.65, 1.15), 2)
    if base is not None:
        for k in ('ineligible_share', 'concentration_index', 'cross_aged_share', 'insurance_coverage', 'dilution_history'):
            x[k] = blend(base[k], x[k])
        x['gross_receivables'] = round(math.exp(blend(math.log(base['gross_receivables']), math.log(x['gross_receivables']))), 2)
        x['advance_band'] = base['advance_band']
        x['drawn_balance'] = round(x['gross_receivables'] * (0.60 + 0.05 * x['advance_band']) * rng.uniform(0.65, 1.15), 2)
    return x


def writeoff_features(rng, base=None):
    x = {'exposure': round(math.exp(rng.uniform(9.5, 13)), 2), 'insured_share': rng.uniform(0, 0.9),
         'payment_score': rng.random(), 'sector_stress': rng.random(), 'years_relationship': rng.uniform(0, 15),
         'credit_limit_utilisation': rng.uniform(0, 1.3), 'rating_band': rng.randrange(4)}
    if base is not None:
        for k in ('insured_share', 'payment_score', 'sector_stress', 'credit_limit_utilisation'):
            x[k] = blend(base[k], x[k])
        x['exposure'] = round(math.exp(blend(math.log(base['exposure']), math.log(x['exposure']))), 2)
        x['years_relationship'] = min(15.0, base['years_relationship'] + 0.0)
        x['rating_band'] = base['rating_band']
    return x


# --- closed-case outcome processes (public, noisy realizations) -----------------------------

def dilution_outcome(rng, x, event):
    z = (-3.0 + 1.4 * x['promo_intensity'] + 1.1 * x['return_propensity'] - 0.25 * (x['invoice_size_log'] - 9)
         + 0.5 * math.sin(2.5 * x['pricing_dispute_index']) + 0.3 * x['product_mix'] + 0.15 * (x['terms_days'] > 45)
         + 0.35 * (event >= BREAK) + 0.12 * math.sin(event / 2.5 + x['channel']) + rng.gauss(0, 0.35))
    return round(min(0.6, max(0.001, expit(z))), 6)


def collection_outcome(rng, x, event):
    censor = rng.choices([3, 4, 5, 6, 7], [1, 1, 1, 1, 10])[0]
    paid = -1
    for b in range(censor + 1):
        z = (0.6 + 0.3 * b - 2.8 * x['past_due_share'] - 2.2 * x['dispute_share'] + 2.6 * x['payment_regularity']
             - 0.07 * x['remittance_lag'] + 0.35 * math.sin(x['region'] + b / 2) - 0.8 * (x['terms_days'] / 30 - 1)
             - 0.5 * (event >= BREAK) + 0.6 * (x['dispute_share'] > 0.5 and b > 3) - 1.2 * (x['payment_regularity'] < 0.25 and b < 2))
        if rng.random() < expit(z):
            paid = b
            break
    return paid, (paid if paid >= 0 else censor)


def dispute_outcome(rng, x, event):
    z = (-3.2 + 0.45 * x['open_dispute_count'] + 6.0 * x['invoice_error_rate'] + 3.0 * x['po_mismatch_rate']
         - 0.004 * x['days_since_last_dispute'] - 1.5 * x['contact_responsiveness'] + 0.4 * x['contract_type']
         + 1.2 * (x['invoice_error_rate'] > 0.18 and x['po_mismatch_rate'] > 0.2) + 0.3 * (event >= BREAK))
    return int(rng.random() < expit(z))


def recovery_outcome(rng, x, event):
    z = (0.2 - 0.012 * x['days_past_due'] + 1.8 * x['secured_share'] + 1.0 * x['guarantor_strength']
         - 0.25 * x['prior_cures'] + 0.5 * math.sin(x['legal_stage'] + x['exposure_log'] / 3)
         - 0.35 * (event >= BREAK) + rng.gauss(0, 0.5))
    return round(min(1.0, max(0.0, expit(z))), 6)


def availability_outcome(rng, x, event):
    z = (1.6 - 2.5 * x['ineligible_share'] - 1.2 * x['concentration_index'] - 2.0 * x['cross_aged_share']
         + 0.6 * x['insurance_coverage'] + 0.9 * math.cos(2 * math.pi * x['seasonality_phase'] + x['advance_band'])
         + 0.7 * math.sin(3.0 * x['concentration_index'] + x['cross_aged_share'] * 4) - 3.0 * x['dilution_history']
         + 0.2 * x['advance_band'] - 0.2 * (event >= BREAK) + rng.gauss(0, 0.25))
    return round(min(0.98, max(0.05, expit(z))), 6)


def loss_outcome(rng, x, event):
    p = expit(-2.4 - 2.0 * x['payment_score'] + 1.8 * x['sector_stress'] - 0.08 * x['years_relationship']
              + 1.2 * max(0.0, x['credit_limit_utilisation'] - 1) + 0.4 * x['rating_band'] + 0.5 * (event >= BREAK))
    if rng.random() >= p:
        return 0.0
    rate = expit(-0.8 + 1.0 * x['sector_stress'] - 0.7 * x['payment_score'] + 0.3 * x['rating_band'] + rng.gauss(0, 0.6))
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
                if field in ('dilution_ratio', 'recovered_fraction', 'availability_ratio'):
                    factor = math.exp(rng.gauss(0, 0.7))
                    cap = {'dilution_ratio': 0.6, 'recovered_fraction': 1.0, 'availability_ratio': 0.98}[field]
                    original[field] = round(min(cap, max(0.001, value * factor)), 6)
                elif field == 'loss_amount':
                    original[field] = 0.0 if (value > 0 and rng.random() < 0.5) else round(value * math.exp(rng.gauss(0, 0.5)) if value > 0 else row['exposure'] * rng.uniform(0.05, 0.4), 2)
                elif field == 'escalated':
                    original[field] = 1 - value
                elif field == 'paid_bucket':
                    shift = rng.choice([-3, -2, -1, 1, 2, 3])
                    original[field] = -1 if value < 0 else max(0, min(7, value + shift))
                elif field == 'last_observed_bucket':
                    original[field] = original.get('paid_bucket', row['last_observed_bucket'])
                    if original[field] < 0:
                        original[field] = row['last_observed_bucket']
            row['restated_period'] = restated
            row['as_booked'] = original
    return row


# --- generation -----------------------------------------------------------------------------

def generate_inputs():
    ids = [f'OB{i:04d}' for i in range(OBLIGOR_COUNT)]
    refs = ids[:REFERENCE_COUNT]
    queries = [{'record_id': f'{a}:p{q}', 'obligor_id': a, 'period': q} for q in QUERY_PERIODS for a in ids[REFERENCE_COUNT:]]
    write_rows(WORKSPACE / 'queries.jsonl', queries)
    write_json(WORKSPACE / 'dataset_metadata.json', {
        'public_generation_key': PUBLIC_KEY, 'periods': PERIODS, 'reference_obligors': refs, 'currency': 'USD',
        'collection_bucket_upper_days': BUCKET_UPPER_DAYS, 'history_periods': list(HISTORY_PERIODS),
        'query_periods': list(QUERY_PERIODS), 'period_unit': 'month',
        'recovery_tiers': ['weak', 'below average', 'above average', 'strong'],
        'snapshots': 'Month-end observations; a closed row completed before the snapshot it is filed beside.',
        'ledger': 'Closed rows carry booked_period, and a corrected row carries restated_period with as_booked.'})
    bases = {}
    for a in ids:
        rng = keyed_rng(PUBLIC_KEY, f'register|{a}')
        bases[a] = {
            'dilution': dilution_features(keyed_rng(PUBLIC_KEY, f'base|dilution|{a}')),
            'collections': collection_features(keyed_rng(PUBLIC_KEY, f'base|collections|{a}')),
            'disputes': dispute_features(keyed_rng(PUBLIC_KEY, f'base|disputes|{a}')),
            'delinquencies': delinquency_features(keyed_rng(PUBLIC_KEY, f'base|delinquencies|{a}')),
            'borrowing_base': borrowing_features(keyed_rng(PUBLIC_KEY, f'base|borrowing_base|{a}')),
            'writeoffs': writeoff_features(keyed_rng(PUBLIC_KEY, f'base|writeoffs|{a}'))}
        write_json(WORKSPACE / 'register' / f'{a}.json', {
            'obligor_id': a, 'sector': rng.randrange(5), 'region': bases[a]['collections']['region'],
            'contract_type': bases[a]['disputes']['contract_type'], 'rating_band': bases[a]['writeoffs']['rating_band'],
            'onboarding_period': -rng.randrange(36), 'credit_limit': round(math.exp(rng.uniform(11, 14)), 2),
            'cohort': 'reference' if a in refs else 'query'})
    # obligor-keyed views: disputes and writeoffs
    for a in ids:
        disputes, writeoffs = [], []
        for q in PERIODS:
            x = dispute_features(keyed_rng(PUBLIC_KEY, f'disputes|snapshot|{a}|{q}'), bases[a]['disputes'])
            disputes.append(dict(x, obligor_id=a, period=q, kind='snapshot'))
            x = writeoff_features(keyed_rng(PUBLIC_KEY, f'writeoffs|snapshot|{a}|{q}'), bases[a]['writeoffs'])
            x['years_relationship'] = round(min(15.0, bases[a]['writeoffs']['years_relationship'] + q / 12), 4)
            writeoffs.append(dict(x, obligor_id=a, period=q, kind='snapshot'))
            if int(a[2:]) < EXTERNAL_COUNT:
                rng = keyed_rng(PUBLIC_KEY, f'disputes|closed|{a}|{q}')
                x = dispute_features(rng)
                row = dict(x, case_id=f'DS{a[2:]}-{q}', kind='closed', escalated=dispute_outcome(rng, x, q))
                disputes.append(book(rng, row, q, ['escalated']))
                rng = keyed_rng(PUBLIC_KEY, f'writeoffs|closed|{a}|{q}')
                x = writeoff_features(rng)
                row = dict(x, case_id=f'WO{a[2:]}-{q}', kind='closed', loss_amount=loss_outcome(rng, x, q))
                writeoffs.append(book(rng, row, q, ['loss_amount']))
        write_rows(WORKSPACE / 'disputes' / f'{a}.jsonl', disputes)
        write_rows(WORKSPACE / 'writeoffs' / f'{a}.jsonl', writeoffs)
    # period-keyed views: dilution, collections, delinquencies, borrowing_base
    filed = {name: {q: [] for q in PERIODS} for name in ('dilution', 'collections', 'delinquencies', 'borrowing_base')}
    for q in PERIODS:
        for i in range(100):
            rng = keyed_rng(PUBLIC_KEY, f'dilution|closed|{q}|{i}')
            x = dilution_features(rng)
            row = dict(x, case_id=f'DL{q}-{i}', kind='closed', open_balance=round(math.exp(rng.uniform(10.5, 14.5)), 2),
                       dilution_ratio=dilution_outcome(rng, x, q))
            book(rng, row, q, ['dilution_ratio'])
            filed['dilution'][row['booked_period']].append(row)
            rng = keyed_rng(PUBLIC_KEY, f'collections|closed|{q}|{i}')
            x = collection_features(rng)
            paid, last = collection_outcome(rng, x, q)
            row = dict(x, case_id=f'CL{q}-{i}', kind='closed', paid_bucket=paid, last_observed_bucket=last)
            book(rng, row, q, ['paid_bucket', 'last_observed_bucket'])
            filed['collections'][row['booked_period']].append(row)
            rng = keyed_rng(PUBLIC_KEY, f'delinquencies|closed|{q}|{i}')
            x = delinquency_features(rng)
            row = dict(x, case_id=f'DQ{q}-{i}', kind='closed', recovered_fraction=recovery_outcome(rng, x, q))
            book(rng, row, q, ['recovered_fraction'])
            filed['delinquencies'][row['booked_period']].append(row)
            rng = keyed_rng(PUBLIC_KEY, f'borrowing_base|closed|{q}|{i}')
            x = borrowing_features(rng)
            row = dict(x, case_id=f'BB{q}-{i}', kind='closed', availability_ratio=availability_outcome(rng, x, q))
            book(rng, row, q, ['availability_ratio'])
            filed['borrowing_base'][row['booked_period']].append(row)
    for q in PERIODS:
        for name, sampler in (('dilution', dilution_features), ('collections', collection_features),
                              ('delinquencies', delinquency_features), ('borrowing_base', borrowing_features)):
            rows = list(filed[name][q])
            for a in ids:
                x = sampler(keyed_rng(PUBLIC_KEY, f'{name}|snapshot|{a}|{q}'), bases[a][name])
                if name == 'dilution':
                    x['open_balance'] = round(math.exp(blend(math.log(1.0) + 12.2, keyed_rng(PUBLIC_KEY, f'dilution|balance|{a}|{q}').uniform(10.5, 14.5), 0.5)), 2)
                if name == 'borrowing_base':
                    x['cohort'] = 'reference' if a in refs else 'query'
                rows.append(dict(x, obligor_id=a, period=q, kind='snapshot'))
            write_rows(WORKSPACE / name / f'{q}.jsonl', rows)
    return refs, queries


def main():
    refs, queries = generate_inputs()
    fitted = {lane: getattr(estimators, 'fit_' + lane)(WORKSPACE) for lane in LANES}

    def predict(a, q):
        return dict(record_id=f'{a}:p{q}', **{lane: getattr(estimators, 'predict_' + lane)(fitted[lane], a, q, WORKSPACE) for lane in LANES})

    history = [dict(predict(a, q), obligor_id=a, period=q) for q in HISTORY_PERIODS for a in refs]
    truth = [predict(r['obligor_id'], r['period']) for r in queries]
    write_rows(WORKSPACE / 'history' / 'surveillance.jsonl', history)
    write_rows(HIDDEN / 'truth.jsonl', truth)
    nets = [{'record_id': r['record_id'], 'undrawn_headroom': estimators.availability_net(fitted['availability_rank'], r['obligor_id'], r['period'])} for r in queries]
    write_rows(ROOT / 'solution' / 'measurements' / 'net_availability.jsonl', nets)
    sentinel = keyed_rng(PRIVATE_KEY, 'audit|sentinel').random()
    report = {'generated': True, 'obligors': OBLIGOR_COUNT, 'periods': len(PERIODS), 'reference_obligors': len(refs),
              'history_rows': len(history), 'graded_rows': len(truth), 'private_sentinel_sha256': hashlib.sha256(repr(sentinel).encode()).hexdigest(),
              'label_balance': {
                  'dispute_flag': sum(r['dispute_flag'] for r in truth) / len(truth),
                  'recovery_tier': [sum(r['recovery_tier'] == c for r in truth) for c in range(4)],
                  'unallocated_mass_mean': sum(1 - sum(r['collection_profile']) for r in truth) / len(truth)}}
    write_json(ROOT / 'solution' / 'measurements' / 'generator_report.json', report)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
