"""Judge-private, independent fitted methods for the documentary credit examination desk.

Every target is a fitted functional of published closed cases, not an unobserved outcome.
Each lane fits only its own view plus the credit register. No lane consumes another lane's
predictions. Shared helpers perform transport, ledger selection and numerical operations.
"""
import argparse
import json
from pathlib import Path

import numpy as np

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
FIT_PERIODS = (8, 10, 12, 16, 20)


# --- transport and numerical helpers (no cross-lane fitted state) ---------------------------

def read_rows(path):
    with open(path, encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'
                            for r in rows), encoding='utf-8')


def load_view(workspace, index):
    root = Path(workspace)
    register = {p.stem: json.loads(p.read_text()) for p in sorted((root / 'credit_register').glob('*.json'))}
    rows = [r for p in sorted((root / VIEWS[index]).glob('*.jsonl')) for r in read_rows(p)]
    snapshots, closed = {}, []
    for row in rows:
        row = dict(row)
        if row['kind'] == 'snapshot':
            row[GROUPS[index]] = register[row['beneficiary_id']][GROUPS[index]]
            snapshots[row['beneficiary_id'], row['period']] = row
        else:
            closed.append(row)
    return snapshots, closed


def asof(rows, period):
    """Use only prior bookings and the outcome version known strictly before the review period."""
    return [dict(r, **r.get('as_booked', {})) if r.get('restated_period', -1) >= period else r
            for r in rows if r['booked_period'] < period]


def matrix(rows, index):
    values = np.array([[r[k] for k in FIELDS[index]] for r in rows], dtype=float)
    if index == 5:
        values[:, 0] = np.log(values[:, 0])
    return values


def scale_fit(x):
    centre = np.median(x, axis=0)
    scale = np.maximum(np.median(np.abs(x - centre), axis=0), 0.05)
    return centre, scale


def ridge(x, y, weights, penalty):
    regularizer = np.eye(x.shape[1]) * penalty
    regularizer[0, 0] = 0.0
    return np.linalg.solve(x.T @ (weights[:, None] * x) + regularizer,
                           x.T @ (weights[:, None] * y) if y.ndim == 2 else x.T @ (weights * y))


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -40, 40)))


def neighbours(z, point, weights, count, decay):
    distance = np.sum((z - point) ** 2, axis=1)
    near = np.argsort(distance, kind='stable')[:count]
    kernel = weights[near] * np.exp(-decay * distance[near] / max(0.01, distance[near[-1]]))
    return near, kernel


def prepare(workspace, index):
    snapshots, closed = load_view(workspace, index)
    return {'observations': snapshots, 'closed': closed, 'models': {}}


