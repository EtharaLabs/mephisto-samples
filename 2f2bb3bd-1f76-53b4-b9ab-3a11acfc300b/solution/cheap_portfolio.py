"""Public historical constants and degenerate controls; never reads private truth."""
from pathlib import Path

from portfolio import constant, read_rows


def generate(workspace):
    root = Path(workspace)
    history = read_rows(root / 'history/examination.jsonl')
    queries = read_rows(root / 'queries.jsonl')
    anchor = constant(history, queries)
    methods = {'constant': anchor, 'empty': []}
    for label in range(4):
        methods[f'tier_{label}'] = [dict(r, tenor_tier=label) for r in anchor]
    for flag in (0, 1):
        methods[f'flag_{flag}'] = [dict(r, refusal_flag=flag) for r in anchor]
    for category in range(9):
        methods[f'point_mass_{category}'] = [dict(r, discrepancy_class_profile=[float(j == category) for j in range(8)]) for r in anchor]
    methods['uniform'] = [dict(r, discrepancy_class_profile=[1 / 9] * 8) for r in anchor]
    return methods
