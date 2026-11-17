"""Lane report adapters. The standalone verifier has no third-party dependencies.

Reward Kit installations may import the same six criteria; direct test.sh writes both
reward carriers without requiring Reward Kit or executing the submitted producer.
"""
import json
import importlib
from pathlib import Path

try:
    criterion = importlib.import_module('rewardkit').criterion
except ImportError:
    def criterion(**metadata):
        return lambda function: function

REPORT = Path('/logs/verifier/report.json')


def _lane(name):
    try:
        value = json.loads(REPORT.read_text())['lanes'][name]['fraction']
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError('fraction outside range')
        return {'score': float(value), 'reasoning': f'lane {name} floored fraction'}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {'score': 0.0, 'reasoning': f'lane {name} unavailable: {type(exc).__name__}'}


@criterion(description='Discrepancy count: relative agreement above the competent floor')
def lane_discrepancy_count(workspace: Path):
    return _lane('discrepancy_count')


@criterion(description='Discrepancy class profile: overlap including pending classification')
def lane_discrepancy_class_profile(workspace: Path):
    return _lane('discrepancy_class_profile')


@criterion(description='Refusal flag: positive-class F1 above the competent floor')
def lane_refusal_flag(workspace: Path):
    return _lane('refusal_flag')


@criterion(description='Tenor tier: unweighted macro F1 above the competent floor')
def lane_tenor_tier(workspace: Path):
    return _lane('tenor_tier')


@criterion(description='Priority rank: within-ten cohort agreement above the competent floor')
def lane_examiner_priority_rank(workspace: Path):
    return _lane('examiner_priority_rank')


@criterion(description='Charge reserve: relative agreement above the competent floor')
def lane_charge_reserve(workspace: Path):
    return _lane('charge_reserve')
