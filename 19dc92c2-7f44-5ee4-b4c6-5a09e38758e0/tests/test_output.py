"""One criterion per lane, consuming only the verifier's already-floored report.

No third-party runtime is required. These helpers also support unittest discovery.
"""
import json
from pathlib import Path

REPORT = Path('/logs/verifier/report.json')


def _lane(name):
    try:
        value = json.loads(REPORT.read_text())['lanes'][name]['fraction']
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError('invalid fraction')
        return {'score': value, 'reasoning': f'{name}: independent payable fraction'}
    except (OSError, ValueError, KeyError, TypeError):
        return {'score': 0.0, 'reasoning': f'{name}: report unavailable'}


def lane_nav_break_magnitude(workspace=None):
    return _lane('nav_break_magnitude')


def lane_fee_accrual_profile(workspace=None):
    return _lane('fee_accrual_profile')


def lane_restatement_flag(workspace=None):
    return _lane('restatement_flag')


def lane_pricing_source_tier(workspace=None):
    return _lane('pricing_source_tier')


def lane_oversight_rank(workspace=None):
    return _lane('oversight_rank')


def lane_expense_reserve(workspace=None):
    return _lane('expense_reserve')
