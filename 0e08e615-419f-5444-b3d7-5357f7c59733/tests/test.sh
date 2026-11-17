#!/bin/sh
# Both reward carriers start at zero; a scorer failure cannot publish stale credit.
set -u
export PYTHONDONTWRITEBYTECODE=1
here=/tests  # sforge runs this script from /tmp; the scorer lives at /tests (judge Dockerfile COPY . /tests/)
logs="${VERIFIER_LOG_DIR:-/logs/verifier}"
mkdir -p "$logs" || exit 1
printf '0\n' > "$logs/reward.txt" || exit 1
printf '{"reward":0}\n' > "$logs/reward.json" || exit 1
python3 -I -B "$here/scoring/eval.py" --submission-dir "${1:-/workspace}" --log-dir "$logs" || exit 0
