"""Reward Kit criteria, one per lane. Each returns the floored lane fraction that
tests/scoring/eval.py wrote to /logs/verifier/report.json, already in [0, 1]. A missing or broken
report scores 0.0 with a reason instead of raising, so the reward file is always written."""
import json
from pathlib import Path

from rewardkit import criterion

REPORT = Path('/logs/verifier/report.json')


def _lane(name):
    try:
        value = json.loads(REPORT.read_text(encoding='utf-8'))['lanes'][name]['fraction']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'score': 0.0, 'reasoning': f'lane {name} unavailable: {type(exc).__name__}'}
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= value <= 1.0:
        return {'score': 0.0, 'reasoning': f'lane {name} fraction out of range'}
    return {'score': float(value), 'reasoning': f'lane {name} floored fraction'}


@criterion(description='Dilution reserve: relative agreement above the competent floor')
def lane_dilution_reserve(workspace: Path):
    return _lane('dilution_reserve')


@criterion(description='Collection profile: distribution overlap above the competent floor')
def lane_collection_profile(workspace: Path):
    return _lane('collection_profile')


@criterion(description='Dispute flag: positive-class F1 above the competent floor')
def lane_dispute_flag(workspace: Path):
    return _lane('dispute_flag')


@criterion(description='Recovery tier: macro F1 above the competent floor')
def lane_recovery_tier(workspace: Path):
    return _lane('recovery_tier')


@criterion(description='Availability rank: cohort Spearman agreement above the competent floor')
def lane_availability_rank(workspace: Path):
    return _lane('availability_rank')


@criterion(description='Loss reserve: relative agreement above the competent floor')
def lane_loss_reserve(workspace: Path):
    return _lane('loss_reserve')
