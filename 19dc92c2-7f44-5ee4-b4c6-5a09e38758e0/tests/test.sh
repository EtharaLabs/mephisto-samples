#!/bin/sh
# Fail closed, and never republish an earlier positive report.
set -u
export PYTHONDONTWRITEBYTECODE=1
LOGS="${VERIFIER_LOG_DIR:-/logs/verifier}"
TESTS=/tests  # sforge runs this script from /tmp; the scorer lives at /tests (judge Dockerfile COPY . /tests/)
mkdir -p "$LOGS" || exit 1
printf '0\n' > "$LOGS/reward.txt"
printf '{"reward":0}\n' > "$LOGS/reward.json"
rm -f "$LOGS/report.json" "$LOGS/ctrf.json"
if python3 -I -B "$TESTS/scoring/eval.py" --submission-dir "${1:-/workspace}" --log-dir "$LOGS"; then
  :
else
  printf '0\n' > "$LOGS/reward.txt"
  printf '{"reward":0}\n' > "$LOGS/reward.json"
fi
exit 0
