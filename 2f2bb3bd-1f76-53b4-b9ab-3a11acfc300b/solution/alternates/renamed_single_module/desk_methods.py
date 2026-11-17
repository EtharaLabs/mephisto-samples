"""Judge-private, independent fitted methods for the documentary credit examination desk.

Every target is a fitted functional of published closed cases, not an unobserved outcome.
Each lane fits only its own view plus the credit register. No lane consumes another lane's
predictions. Shared helpers perform transport, ledger selection and numerical operations.
"""
import argparse
import json
from pathlib import Path
import numpy as np
LANES = ('discrepancy_count', 'discrepancy_class_profile', 'refusal_flag', 'tenor_tier', 'examiner_priority_rank', 'charge_reserve')
VIEWS = ('presentation_documents', 'discrepancy_logs', 'refusal_notices', 'amendment_histories', 'correspondent_banks', 'settlement_payments')
GROUPS = ('document_route', 'trade_corridor', 'credit_form', 'tenor_basis', 'service_band', 'charge_schedule')
FIELDS = (('document_count', 'data_conflict_share', 'missing_original_share', 'presentation_lag_days', 'expiry_margin_days'), ('late_share', 'inconsistency_share', 'missing_share', 'insurance_gap', 'transport_complexity'), ('unwaived_items', 'applicant_response_days', 'material_conflict_share', 'notice_time_left', 'waiver_reliability'), ('draft_tenor_days', 'acceptance_delay_days', 'amendment_count', 'maturity_extension_days', 'deferred_share'), ('bank_queue_hours', 'cutoff_margin_hours', 'document_complexity', 'corridor_delay_days', 'cycle_phase'), ('face_amount_usd', 'unpaid_fee_share', 'message_count', 'claim_complexity', 'relationship_years'))
OUTCOMES = ('observed_discrepancies', 'class_counts', 'notice_refused', 'settled_tenor_days', 'handling_urgency', 'charges_usd')
FIT_PERIODS = (8, 10, 12, 16, 20)

def read_rows(path):
    with open(path, encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]

def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join((json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n' for r in rows)), encoding='utf-8')

def load_view(workspace, index):
    root = Path(workspace)
    register = {p.stem: json.loads(p.read_text()) for p in sorted((root / 'credit_register').glob('*.json'))}
    rows = [r for p in sorted((root / VIEWS[index]).glob('*.jsonl')) for r in read_rows(p)]
    snapshots, closed = ({}, [])
    for row in rows:
        row = dict(row)
        if row['kind'] == 'snapshot':
            row[GROUPS[index]] = register[row['beneficiary_id']][GROUPS[index]]
            snapshots[row['beneficiary_id'], row['period']] = row
        else:
            closed.append(row)
    return (snapshots, closed)

def asof(rows, period):
    """Use only prior bookings and the outcome version known strictly before the review period."""
    return [dict(r, **r.get('as_booked', {})) if r.get('restated_period', -1) >= period else r for r in rows if r['booked_period'] < period]

def matrix(rows, index):
    values = np.array([[r[k] for k in FIELDS[index]] for r in rows], dtype=float)
    if index == 5:
        values[:, 0] = np.log(values[:, 0])
    return values

def scale_fit(x):
    centre = np.median(x, axis=0)
    scale = np.maximum(np.median(np.abs(x - centre), axis=0), 0.05)
    return (centre, scale)

def ridge(x, y, weights, penalty):
    regularizer = np.eye(x.shape[1]) * penalty
    regularizer[0, 0] = 0.0
    return np.linalg.solve(x.T @ (weights[:, None] * x) + regularizer, x.T @ (weights[:, None] * y) if y.ndim == 2 else x.T @ (weights * y))

def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -40, 40)))

def neighbours(z, point, weights, count, decay):
    distance = np.sum((z - point) ** 2, axis=1)
    near = np.argsort(distance, kind='stable')[:count]
    kernel = weights[near] * np.exp(-decay * distance[near] / max(0.01, distance[near[-1]]))
    return (near, kernel)

def prepare(workspace, index):
    snapshots, closed = load_view(workspace, index)
    return {'observations': snapshots, 'closed': closed, 'models': {}}

def fit_discrepancy_count(directory):
    fitted = prepare(directory, 0)
    for q in FIT_PERIODS:
        cases = asof(fitted['closed'], q)
        groups = {}
        for group in range(4):
            rows = [r for r in cases if r['document_route'] == group]
            x = matrix(rows, 0)
            centre, scale = scale_fit(x)
            z = (x - centre) / scale
            y = np.log1p([r['observed_discrepancies'] for r in rows])
            weights = np.exp(-(q - 1 - np.array([r['booked_period'] for r in rows])) / 6.5)
            groups[group] = (z, y, weights, centre, scale)
        fitted['models'][q] = groups
    return fitted

def predict_discrepancy_count(model, beneficiary, period, directory):
    row = model['observations'][beneficiary, period]
    z, y, weights, centre, scale = model['models'][period][row['document_route']]
    point = (matrix([row], 0)[0] - centre) / scale
    near, kernel = neighbours(z, point, weights, 54, 2.8)
    design = np.column_stack([np.ones(len(near)), z[near] - point])
    beta = ridge(design, y[near], kernel, 0.65)
    return round(float(max(0, np.expm1(beta[0]))), 2)

def fit_discrepancy_class_profile(directory):
    fitted = prepare(directory, 1)
    for q in FIT_PERIODS:
        rows = asof(fitted['closed'], q)
        x = matrix(rows, 1)
        centre, scale = scale_fit(x)
        counts = np.array([r['class_counts'] for r in rows], dtype=float)
        shares = counts / counts.sum(axis=1)[:, None]
        weights = np.exp(-(q - 1 - np.array([r['booked_period'] for r in rows])) / 5.0)
        groups = np.array([r['trade_corridor'] for r in rows])
        priors = {g: np.average(shares[groups == g], axis=0, weights=weights[groups == g]) for g in range(4)}
        fitted['models'][q] = ((x - centre) / scale, shares, weights, groups, priors, centre, scale)
    return fitted

def predict_discrepancy_class_profile(model, beneficiary, period, directory):
    row = model['observations'][beneficiary, period]
    z, shares, weights, groups, priors, centre, scale = model['models'][period]
    point = (matrix([row], 1)[0] - centre) / scale
    group = row['trade_corridor']
    distance = np.sum((z - point) ** 2, axis=1) + 2.5 * (groups != group)
    near = np.argsort(distance, kind='stable')[:38]
    kernel = weights[near] * np.exp(-3.2 * distance[near] / max(0.01, distance[near[-1]]))
    profile = (kernel @ shares[near] + 2.5 * priors[group]) / (kernel.sum() + 2.5)
    return (np.floor(profile[:8] * 100000000.0) / 100000000.0).tolist()

def refusal_design(x, groups):
    return np.column_stack([np.ones(len(x)), x, x[:, 0] * x[:, 2], x[:, 1] * x[:, 4], *[(groups == g).astype(float) for g in (1, 2, 3)]])

def fit_refusal_flag(directory):
    fitted = prepare(directory, 2)
    for q in FIT_PERIODS:
        rows = asof(fitted['closed'], q)
        x = matrix(rows, 2)
        centre, scale = scale_fit(x)
        design = refusal_design((x - centre) / scale, np.array([r['credit_form'] for r in rows]))
        y = np.array([r['notice_refused'] for r in rows])
        weights = np.exp(-(q - 1 - np.array([r['booked_period'] for r in rows])) / 7)
        beta = np.zeros(design.shape[1])
        penalty = np.eye(len(beta)) * 1.8
        penalty[0, 0] = 0
        for _ in range(35):
            p = sigmoid(design @ beta)
            hessian = design.T @ ((weights * p * (1 - p))[:, None] * design) + penalty
            step = np.linalg.solve(hessian, design.T @ (weights * (y - p)) - penalty @ beta)
            beta += step
            if max(abs(step)) < 1e-10:
                break
        recent = np.array([r['booked_period'] >= q - 5 for r in rows])
        prevalence = np.average(y[recent], weights=weights[recent])
        probabilities = sigmoid(design[recent] @ beta)
        order = np.argsort(-probabilities, kind='stable')
        cumulative = np.cumsum(weights[recent][order])
        position = min(len(order) - 1, int(np.searchsorted(cumulative, prevalence * cumulative[-1])))
        fitted['models'][q] = (beta, centre, scale, float(probabilities[order[position]]))
    return fitted

def predict_refusal_flag(model, beneficiary, period, directory):
    row = model['observations'][beneficiary, period]
    beta, centre, scale, threshold = model['models'][period]
    design = refusal_design((matrix([row], 2) - centre) / scale, np.array([row['credit_form']]))
    return int(sigmoid(design @ beta)[0] >= threshold)

def fit_tenor_tier(directory):
    fitted = prepare(directory, 3)
    for q in FIT_PERIODS:
        groups = {}
        for group in range(4):
            rows = [r for r in asof(fitted['closed'], q) if r['tenor_basis'] == group]
            x = matrix(rows, 3)
            centre, scale = scale_fit(x)
            weights = np.exp(-(q - 1 - np.array([r['booked_period'] for r in rows])) / 8)
            groups[group] = ((x - centre) / scale, np.array([r['settled_tenor_days'] for r in rows]), weights, centre, scale)
        fitted['models'][q] = groups
    return fitted

def predict_tenor_tier(model, beneficiary, period, directory):
    row = model['observations'][beneficiary, period]
    z, y, weights, centre, scale = model['models'][period][row['tenor_basis']]
    point = (matrix([row], 3)[0] - centre) / scale
    near, kernel = neighbours(z, point, weights, 27, 4.0)
    days = (kernel @ y[near] + 0.4 * np.average(y, weights=weights)) / (kernel.sum() + 0.4)
    return int(np.searchsorted([45, 95, 160], days, side='left'))

def priority_basis(x):
    return np.column_stack([np.ones(len(x)), x[:, :4], np.sin(2 * np.pi * x[:, 4]), np.cos(2 * np.pi * x[:, 4]), x[:, 0] * x[:, 2], np.sin(x[:, 3] / 4 + x[:, 2] * 3)])

def fit_examiner_priority_rank(directory):
    fitted = prepare(directory, 4)
    for q in FIT_PERIODS:
        groups = {}
        for group in range(4):
            rows = [r for r in asof(fitted['closed'], q) if r['service_band'] == group]
            x = matrix(rows, 4)
            centre, scale = scale_fit(x)
            y = np.array([r['handling_urgency'] for r in rows])
            weights = np.exp(-(q - 1 - np.array([r['booked_period'] for r in rows])) / 6)
            design = priority_basis(x)
            beta = ridge(design, y, weights, 0.4)
            residual = y - design @ beta
            spread = max(0.1, float(np.median(abs(residual - np.median(residual)))))
            groups[group] = (beta, (x - centre) / scale, np.clip(residual, -3 * spread, 3 * spread), weights, centre, scale)
        fitted['models'][q] = groups
    return fitted

def priority_score(model, beneficiary, period):
    row = model['observations'][beneficiary, period]
    beta, z, residual, weights, centre, scale = model['models'][period][row['service_band']]
    x = matrix([row], 4)
    near, kernel = neighbours(z, (x[0] - centre) / scale, weights, 43, 2.0)
    return round(float((priority_basis(x) @ beta)[0] + kernel @ residual[near] / (kernel.sum() + 3)), 7)

def predict_examiner_priority_rank(model, beneficiary, period, directory):
    cache = model.setdefault('rank_cache', {})
    if period not in cache:
        cohort = [r['beneficiary_id'] for r in read_rows(Path(directory) / 'queries.jsonl') if r['period'] == period]
        if not cohort:
            register = Path(directory) / 'credit_register'
            cohort = [p.stem for p in sorted(register.glob('*.json')) if json.loads(p.read_text())['cohort'] == 'reference']
        values = {a: priority_score(model, a, period) for a in cohort}
        ranks = {v: i + 1 for i, v in enumerate(sorted(set(values.values()), reverse=True))}
        cache[period] = {a: ranks[v] for a, v in values.items()}
    return cache[period][beneficiary]

def fit_charge_reserve(directory):
    fitted = prepare(directory, 5)
    for q in FIT_PERIODS:
        groups = {}
        for group in range(4):
            rows = [r for r in asof(fitted['closed'], q) if r['charge_schedule'] == group]
            x = matrix(rows, 5)
            centre, scale = scale_fit(x)
            rates = np.array([r['charges_usd'] / r['face_amount_usd'] for r in rows])
            positive = rates > 0
            logs = np.log(rates[positive])
            weights = np.exp(-(q - 1 - np.array([r['booked_period'] for r in rows])) / 5.5)
            groups[group] = ((x - centre) / scale, rates, weights, centre, scale, float((positive.sum() + 1) / (len(rows) + 2)), float(logs.mean()), float(logs.var()))
        fitted['models'][q] = groups
    return fitted

def predict_charge_reserve(model, beneficiary, period, directory):
    row = model['observations'][beneficiary, period]
    z, rates, weights, centre, scale, prior, logmean, variance = model['models'][period][row['charge_schedule']]
    near, kernel = neighbours(z, (matrix([row], 5)[0] - centre) / scale, weights, 49, 2.4)
    positive = rates[near] > 0
    probability = (kernel[positive].sum() + 4 * prior) / (kernel.sum() + 4)
    severity = (kernel[positive] @ np.log(rates[near][positive]) + 3 * logmean) / (kernel[positive].sum() + 3)
    return round(float(row['face_amount_usd'] * probability * np.exp(severity + 0.25 * variance)), 2)

def records(workspace, queries=None):
    queries = read_rows(Path(workspace) / 'queries.jsonl') if queries is None else queries
    fitted = {lane: globals()['fit_' + lane](workspace) for lane in LANES}
    return [dict(record_id=r['record_id'], **{lane: globals()['predict_' + lane](fitted[lane], r['beneficiary_id'], r['period'], workspace) for lane in LANES}) for r in queries]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    write_rows(args.output, records(args.workspace))
if __name__ == '__main__':
    main()
