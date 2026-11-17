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


@criterion(description='Aging reserve: relative agreement above the competent floor')
def lane_aging_reserve(workspace: Path):
    return _lane('aging_reserve')


@criterion(description='Turn profile: distribution overlap above the competent floor')
def lane_turn_profile(workspace: Path):
    return _lane('turn_profile')


@criterion(description='Sold-out-of-trust flag: positive-class F1 above the competent floor')
def lane_sot_flag(workspace: Path):
    return _lane('sot_flag')


@criterion(description='Variance tier: macro F1 above the competent floor')
def lane_variance_tier(workspace: Path):
    return _lane('variance_tier')


@criterion(description='Headroom rank: cohort tolerance-band agreement above the competent floor')
def lane_headroom_rank(workspace: Path):
    return _lane('headroom_rank')


@criterion(description='Loss reserve: relative agreement above the competent floor')
def lane_loss_reserve(workspace: Path):
    return _lane('loss_reserve')
