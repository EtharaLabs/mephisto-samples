"""Degenerate controls; no hidden data or oracle imports."""
from public_reference import LANES, predictions, read_rows


def controls(workspace):
    base = predictions(workspace, 'constant')
    yield 'constant_history', base
    for label in (0, 1):
        yield f'flag_{label}', [dict(r, restatement_flag=label) for r in base]
    for label in range(4):
        yield f'tier_{label}', [dict(r, pricing_source_tier=label) for r in base]
    for bucket in range(9):
        yield f'point_mass_{bucket}', [dict(r, fee_accrual_profile=[float(j == bucket) for j in range(8)]) for r in base]
    yield 'uniform', [dict(r, fee_accrual_profile=[1/9]*8) for r in base]
    yield 'zero_amounts', [dict(r, nav_break_magnitude=0.0, expense_reserve=0.0) for r in base]
    for reverse in (False, True):
        ids = sorted({r['record_id'].split(':')[0] for r in base}, reverse=reverse)
        ranks = {fund: i+1 for i, fund in enumerate(ids)}
        yield f'identity_reverse_{reverse}', [dict(r, oversight_rank=ranks[r['record_id'].split(':')[0]]) for r in base]
