#!/bin/sh
# Fail closed: seed both carriers before invoking the isolated, trusted scorer.
set -u
export PYTHONDONTWRITEBYTECODE=1
here="${TEST_DIR:-/tests}"  # sforge runs this script from /tmp; the scorer lives at /tests (judge Dockerfile COPY . /tests/)
logs="${VERIFIER_LOG_DIR:-/logs/verifier}"
mkdir -p "$logs" || exit 1
printf '0\n' > "$logs/reward.txt" || exit 1
printf '{"reward":0}\n' > "$logs/reward.json" || exit 1
rm -f "$logs/report.json" "$logs/ctrf.json"
if ! python3 -I -B "$here/scoring/eval.py" --submission-dir "${1:-/workspace}" --log-dir "$logs"; then
    printf '0\n' > "$logs/reward.txt"
    printf '{"reward":0}\n' > "$logs/reward.json"
    printf '%s\n' 'Scoring failed; retaining zero reward.' >&2
fi
exit 0
