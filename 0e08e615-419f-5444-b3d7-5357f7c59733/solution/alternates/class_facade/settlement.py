"""Alternate invocation order; same fitted desk, no truth-file access."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import estimators


class Settlement:
    def __init__(self, workspace):
        self.workspace = Path(workspace)

    def records(self):
        queries = estimators.read_rows(self.workspace/'queries.jsonl')
        reverse = estimators.records_for(self.workspace,list(reversed(queries)))
        table = {r['record_id']:r for r in reverse}
        return [table[r['record_id']] for r in queries]


if __name__ == '__main__':
    estimators.write_rows(Path(sys.argv[2]),Settlement(sys.argv[1]).records())
