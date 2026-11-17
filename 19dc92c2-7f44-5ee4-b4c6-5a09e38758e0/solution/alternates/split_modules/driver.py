"""Alternate lane-by-lane oracle driver, distinct evaluation order."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import estimators
from transport import queries


def run(workspace, output):
    requested = queries(workspace)
    rows = {q['record_id']: {'record_id': q['record_id']} for q in requested}
    for lane in reversed(estimators.LANES):
        model = getattr(estimators, 'fit_' + lane)(workspace)
        for q in requested:
            rows[q['record_id']][lane] = getattr(estimators, 'predict_' + lane)(model, q['fund_id'], q['period'], workspace)
    Path(output).write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':')) + '\n' for r in rows.values()))


if __name__ == '__main__':
    run(*sys.argv[1:])
