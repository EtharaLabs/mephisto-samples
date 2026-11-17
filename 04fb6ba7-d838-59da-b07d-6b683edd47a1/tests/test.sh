#!/bin/sh
# Delivery rule 15: both reward carriers are seeded to 0 before scoring, so an
# infrastructure failure scores 0 instead of becoming a trial error. Scoring runs
# in a scratch dir and its output is published only after validation, so a stale
# or partial report can never be republished as a positive reward. Harbor reads
# reward.json in preference to reward.txt and rejects any non-numeric value, so
# reward.json must stay a flat numeric object.
set -u
export PYTHONDONTWRITEBYTECODE=1

LOGS=/logs/verifier
SCRATCH="$LOGS/.scoring"

mkdir -p "$LOGS" || exit 1
printf '0\n' > "$LOGS/reward.txt" || exit 1
printf '{"reward": 0}\n' > "$LOGS/reward.json" || exit 1
if rm -f "$LOGS/report.json" "$LOGS/ctrf.json" \
  && rm -rf "$SCRATCH" \
  && mkdir -p "$SCRATCH" \
  && python3 -I -B /tests/scoring/eval.py \
      --submission-dir "${1:-/workspace}" \
      --log-dir "$SCRATCH"
then
  python3 - "$SCRATCH" "$LOGS" <<'PY'
import json
import math
import os
import sys
from pathlib import Path

scratch, logs = Path(sys.argv[1]), Path(sys.argv[2])
try:
    report = json.loads((scratch / "report.json").read_text(encoding="utf-8"))
    score = report["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("score is not a JSON number")
    score = float(score)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("score is not a finite value in [0, 1]")

    for name in ("report.json", "ctrf.json"):
        if (scratch / name).exists():
            os.replace(scratch / name, logs / name)

    (scratch / "reward.txt").write_text(f"{score}\n", encoding="utf-8")
    os.replace(scratch / "reward.txt", logs / "reward.txt")
    (scratch / "reward.json").write_text(
        json.dumps({"reward": score}, allow_nan=False) + "\n", encoding="utf-8"
    )
    os.replace(scratch / "reward.json", logs / "reward.json")
except Exception as error:
    print(f"Reward publication failed: {type(error).__name__}: {error}", file=sys.stderr)
    try:
        (logs / "reward.txt").write_text("0\n", encoding="utf-8")
    except OSError:
        pass
    print("Both reward carriers left at 0.", file=sys.stderr)
PY
else
  printf '%s\n' 'Scoring failed; keeping the seeded reward of 0.' >&2
fi

rm -rf "$SCRATCH"
exit 0
