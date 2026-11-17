"""Alternate oracle B, driver: fit every lane, then emit the records grouped by period."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lanes  # noqa: E402
from transport import LANES, read_rows  # noqa: E402


def run(workspace, output):
    workspace = Path(workspace)
    queries = read_rows(workspace / "queries.jsonl")
    fitted = {lane: getattr(lanes, "fit_" + lane)(workspace) for lane in LANES}
    records = {}
    for period in sorted({r["period"] for r in queries}):
        for r in (q for q in queries if q["period"] == period):
            records[r["record_id"]] = dict(record_id=r["record_id"], **{lane: getattr(lanes, "predict_" + lane)(fitted[lane], r["obligor_id"], period, workspace) for lane in LANES})
    with open(output, "w") as handle:
        for r in queries:
            handle.write(json.dumps(records[r["record_id"]], sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: driver.py <workspace> <output>")
    run(sys.argv[1], sys.argv[2])
