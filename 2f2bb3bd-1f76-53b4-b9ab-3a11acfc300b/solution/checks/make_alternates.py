"""Build mechanical alternate oracle layouts for interface and naming invariance checks.

These are not independent statistical estimates or difficulty evidence. Source changes
are AST-preserving identifier changes or module splits; every variant recomputes inputs.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'solution/estimators.py'
ALT = ROOT / 'solution/alternates'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class Rename(ast.NodeTransformer):
    mapping = {'fitted_object': 'model', 'workspace_dir': 'directory', 'beneficiary_id': 'beneficiary'}

    def visit_Name(self, node):
        node.id = self.mapping.get(node.id, node.id)
        return node

    def visit_arg(self, node):
        node.arg = self.mapping.get(node.arg, node.arg)
        return node


def main():
    source = SOURCE.read_text()
    renamed = ast.fix_missing_locations(Rename().visit(ast.parse(source)))
    write(ALT / 'renamed_single_module/desk_methods.py', ast.unparse(renamed) + '\n')
    helpers, lanes = source.split('# --- lane 1:', 1)
    lanes, driver = lanes.split('# --- oracle entry point', 1)
    helper_names = [n.name for n in ast.parse(helpers).body if isinstance(n, ast.FunctionDef)]
    imports = 'import argparse\nimport json\nfrom pathlib import Path\nimport numpy as np\n'
    write(ALT / 'split_modules/transport.py', helpers)
    write(ALT / 'split_modules/lanes.py', '"""Alternate split-layout lane methods."""\n' + imports
          + 'from transport import FIT_PERIODS, LANES, ' + ', '.join(helper_names) + '\n\n# --- lane 1:' + lanes)
    lane_names = [n.name for n in ast.parse('# --- lane 1:' + lanes).body if isinstance(n, ast.FunctionDef)]
    write(ALT / 'split_modules/driver.py', '"""Alternate split-layout oracle driver."""\n' + imports
          + 'from transport import LANES, read_rows, write_rows\nfrom lanes import ' + ', '.join(lane_names)
          + '\n\n# --- oracle entry point' + driver)
    facade = '''
class Examination:
    """Own independent fitted objects; evaluate queries in reverse order."""

    def __init__(self, workspace):
        self.workspace = Path(workspace)
        self.fitted = {lane: globals()['fit_' + lane](workspace) for lane in LANES}

    def record(self, row):
        return dict(record_id=row['record_id'], **{lane: globals()['predict_' + lane](
            self.fitted[lane], row['beneficiary_id'], row['period'], self.workspace) for lane in LANES})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    desk = Examination(args.workspace)
    queries = read_rows(desk.workspace / 'queries.jsonl')
    answers = {r['record_id']: desk.record(r) for r in reversed(queries)}
    write_rows(args.output, [answers[r['record_id']] for r in queries])


if __name__ == '__main__':
    main()
'''
    write(ALT / 'class_facade/examination.py', helpers + '# --- lane 1:' + lanes + facade)
    for folder, module in (('renamed_single_module', 'desk_methods.py'), ('split_modules', 'driver.py'), ('class_facade', 'examination.py')):
        write(ALT / folder / 'solve.sh', '#!/bin/sh\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1\n'
              'here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\n'
              'workspace="${1:-/workspace}"\nout="${2:-$workspace}"\nmkdir -p "$out"\n'
              f'python3 -B "$here/{module}" --workspace "$workspace" --output "$out/predictions.jsonl"\n')
    for script in ROOT.rglob('solve.sh'):
        if '.venv' not in script.parts:
            script.chmod(0o755)
    (ROOT / 'tests/test.sh').chmod(0o755)


if __name__ == '__main__':
    main()
