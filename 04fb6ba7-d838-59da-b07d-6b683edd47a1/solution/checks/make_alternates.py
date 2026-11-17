"""Build three light-variant alternate oracles from solution/estimators.py.

Each alternate differs from the oracle in identifier names, error text and file layout, and each
must reach full reward. They are mechanical transformations of the same arithmetic, so the floats
agree byte for byte; solution/checks/validate_numpy.py is the independent cross-check.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / 'solution' / 'estimators.py').read_text(encoding='utf-8')
ALT = ROOT / 'solution' / 'alternates'

RENAMES_A = {'read_rows': 'load_jsonl', 'read_tree': 'load_view', 'asof': 'ledger_at', 'recency': 'age_weight', 'expit': 'sigmoid',
             'logit': 'log_odds', 'mad_scale': 'robust_scale', 'solve': 'gauss_jordan', 'dense_ranks_descending': 'dense_rank_desc',
             '_dilution_design': 'dilution_row', '_local_linear': 'weighted_local_fit', '_weighted_km': 'product_limit',
             '_restricted_mean': 'area_under_survival', '_survival_at': 'interpolate_survival', '_dispute_features': 'dispute_raw',
             '_dispute_design': 'dispute_row', '_recovery_point': 'recovery_point', '_nadaraya_watson': 'kernel_average',
             'availability_basis': 'seasonal_basis', 'availability_net': 'net_availability', 'recovery_score': 'recovery_estimate',
             'fitted_object': 'model', 'workspace_dir': 'root', 'obligor_id': 'obligor', 'period': 'month'}


def rename(text, mapping):
    for old, new in mapping.items():
        text = re.sub(r'\b' + re.escape(old) + r'\b', new, text)
    return text


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def alternate_a():
    text = rename(SOURCE, RENAMES_A)
    text = text.replace('"""Judge-private, independent fitted methods for the receivables finance surveillance desk.',
                        '"""Alternate oracle A: the desk methods with renamed identifiers in one module.')
    text = text.replace("'obligor_id'", "'obligor_id'").replace("r['month']", "r['period']").replace("['month']", "['period']")
    text = text.replace("q == month", "q == month").replace("obligor_id=r['obligor']", "obligor_id=r['obligor_id']")
    # restore the data field names that the rename must not touch
    text = text.replace("r['obligor']", "r['obligor_id']").replace("row['obligor']", "row['obligor_id']")
    text = text.replace("'month'", "'period'")
    text = text.replace("ZeroDivisionError", "ZeroDivisionError")
    write(ALT / 'renamed_single_module' / 'desk_methods.py', text)
    write(ALT / 'renamed_single_module' / 'solve.sh', '#!/bin/sh\n# Alternate oracle A: one renamed module.\nset -eu\nhere="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nout="${1:-${WORKSPACE:-/workspace}}"\nPYTHONDONTWRITEBYTECODE=1 python3 -I -B "$here/desk_methods.py" --workspace "$out" --output "$out/predictions.jsonl" || { echo "alternate A failed to fit the desk methods" >&2; exit 1; }\ncp "$here/desk_methods.py" "$out/receivables_surveillance.py"\n: > "$out/requirements.txt"\n')


def alternate_b():
    """Split layout: transport helpers in one module, lane methods in another, driver in a third."""
    text = SOURCE
    head, _, rest = text.partition('# --- lane 1')
    helpers = head.replace('"""Judge-private, independent fitted methods for the receivables finance surveillance desk.',
                           '"""Alternate oracle B, transport layer: file reading, ledger view and numeric helpers.')
    helpers = helpers[:helpers.rfind('# --- transport')] + helpers[helpers.rfind('# --- transport'):]
    lanes = '"""Alternate oracle B, lane methods: six fitted estimators over six views."""\nimport json\nimport math\nfrom pathlib import Path\nfrom statistics import median\n\nfrom transport import *  # noqa: F401,F403\nfrom transport import FIT_PERIODS, BUCKET_UPPER_DAYS, read_rows, asof, recency, expit, logit, mad_scale, solve, dense_ranks_descending, read_tree\n\n# --- lane 1' + rest
    lanes = lanes[:lanes.find('# --- oracle entry point')]
    driver = ('"""Alternate oracle B, driver: fit every lane, then emit the records grouped by period."""\n'
              'import json\nimport sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n'
              'import lanes  # noqa: E402\nfrom transport import LANES, read_rows  # noqa: E402\n\n\n'
              'def run(workspace, output):\n    workspace = Path(workspace)\n    queries = read_rows(workspace / "queries.jsonl")\n'
              '    fitted = {lane: getattr(lanes, "fit_" + lane)(workspace) for lane in LANES}\n    records = {}\n'
              '    for period in sorted({r["period"] for r in queries}):\n        for r in (q for q in queries if q["period"] == period):\n'
              '            records[r["record_id"]] = dict(record_id=r["record_id"], **{lane: getattr(lanes, "predict_" + lane)(fitted[lane], r["obligor_id"], period, workspace) for lane in LANES})\n'
              '    with open(output, "w") as handle:\n        for r in queries:\n            handle.write(json.dumps(records[r["record_id"]], sort_keys=True, separators=(",", ":"), allow_nan=False) + "\\n")\n\n\n'
              'if __name__ == "__main__":\n    if len(sys.argv) != 3:\n        raise SystemExit("usage: driver.py <workspace> <output>")\n    run(sys.argv[1], sys.argv[2])\n')
    write(ALT / 'split_modules' / 'transport.py', helpers)
    write(ALT / 'split_modules' / 'lanes.py', lanes)
    write(ALT / 'split_modules' / 'driver.py', driver)
    write(ALT / 'split_modules' / 'solve.sh', '#!/bin/sh\n# Alternate oracle B: split module layout.\nset -eu\nhere="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nout="${1:-${WORKSPACE:-/workspace}}"\nPYTHONDONTWRITEBYTECODE=1 python3 -I -B "$here/driver.py" "$out" "$out/predictions.jsonl" || { echo "alternate B: lane fitting aborted" >&2; exit 2; }\ncat "$here/transport.py" "$here/lanes.py" "$here/driver.py" > "$out/receivables_surveillance.py"\n: > "$out/requirements.txt"\n')


def alternate_c():
    """Class-based facade over the same arithmetic, emitting records in reverse query order into a dict."""
    text = SOURCE
    body = text[:text.find('# --- oracle entry point')]
    body = body.replace('"""Judge-private, independent fitted methods for the receivables finance surveillance desk.',
                        '"""Alternate oracle C: the desk methods behind a Surveillance class facade.')
    facade = ('\n\nclass Surveillance:\n    """Fits every lane once and answers records on demand."""\n\n'
              '    def __init__(self, workspace):\n        self.workspace = Path(workspace)\n'
              '        self.models = {lane: globals()["fit_" + lane](self.workspace) for lane in LANES}\n\n'
              '    def record(self, obligor_id, period):\n        out = {"record_id": f"{obligor_id}:p{period}"}\n'
              '        for lane in LANES:\n            out[lane] = globals()["predict_" + lane](self.models[lane], obligor_id, period, self.workspace)\n        return out\n\n\n'
              'def main(argv):\n    if len(argv) != 2:\n        raise SystemExit("surveillance facade needs <workspace> <output>")\n'
              '    desk = Surveillance(argv[0])\n    queries = read_rows(desk.workspace / "queries.jsonl")\n    answers = {}\n'
              '    for r in reversed(queries):\n        answers[r["record_id"]] = desk.record(r["obligor_id"], r["period"])\n'
              '    with open(argv[1], "w") as handle:\n        for r in queries:\n            handle.write(json.dumps(answers[r["record_id"]], sort_keys=True, separators=(",", ":"), allow_nan=False) + "\\n")\n\n\n'
              'if __name__ == "__main__":\n    main(sys.argv[1:])\n')
    write(ALT / 'class_facade' / 'surveillance.py', body + facade)
    write(ALT / 'class_facade' / 'solve.sh', '#!/bin/sh\n# Alternate oracle C: class facade, reverse evaluation order.\nset -eu\nhere="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nout="${1:-${WORKSPACE:-/workspace}}"\nPYTHONDONTWRITEBYTECODE=1 python3 -I -B "$here/surveillance.py" "$out" "$out/predictions.jsonl" || { echo "alternate C: facade could not answer every record" >&2; exit 3; }\ncp "$here/surveillance.py" "$out/receivables_surveillance.py"\n: > "$out/requirements.txt"\n')


if __name__ == '__main__':
    alternate_a()
    alternate_b()
    alternate_c()
    for script in ALT.rglob('solve.sh'):
        script.chmod(0o755)
    print('alternates written:', sorted(p.name for p in ALT.iterdir()))
