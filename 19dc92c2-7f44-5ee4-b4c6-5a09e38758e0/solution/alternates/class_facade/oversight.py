"""Class-facade oracle: reverse evaluation order must not change record values."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import estimators


class OversightDesk:
    def __init__(self, workspace):
        self.workspace = Path(workspace)

    def records(self):
        queries = estimators.read_rows(self.workspace / 'queries.jsonl')
        rows = estimators.predict_all(self.workspace, list(reversed(queries)))
        indexed = {r['record_id']: r for r in rows}
        return [indexed[q['record_id']] for q in queries]
