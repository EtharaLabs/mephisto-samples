"""Six report criteria for integrations; native test.sh needs no external kit."""
import json
from pathlib import Path


def _lane(name, report=Path('/logs/verifier/report.json')):
    try:
        value = json.loads(report.read_text())['lanes'][name]['fraction']
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0 <= value <= 1:
            raise ValueError('invalid fraction')
        return {'score':float(value),'reasoning':name+' floored fraction'}
    except (OSError,ValueError,KeyError,TypeError):
        return {'score':0.0,'reasoning':name+' unavailable'}


def lane_adjustment_magnitude(workspace=None):
    return _lane('adjustment_magnitude')


def lane_allocation_key_profile(workspace=None):
    return _lane('allocation_key_profile')


def lane_challenge_flag(workspace=None):
    return _lane('challenge_flag')


def lane_method_tier(workspace=None):
    return _lane('method_tier')


def lane_review_rank(workspace=None):
    return _lane('review_rank')


def lane_uncertain_tax_reserve(workspace=None):
    return _lane('uncertain_tax_reserve')
