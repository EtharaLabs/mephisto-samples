#!/bin/sh
# Harbor separate-verifier entry point: score, then let Reward Kit write the flat reward carrier.
#
# Delivery rule 15: both reward carriers are seeded to 0 before anything is scored, so a scorer
# failure scores zero instead of leaving the trial with no reward at all. Without the seed an
# uncaught failure in eval.py leaves /logs/verifier/reward.txt absent and Harbor raises
# RewardFileNotFoundError, which errors the trial rather than scoring it.
#
# Reward Kit is invoked without exec and with a failure guard, so a Reward Kit fault cannot
# discard the score already published from report.json, and cannot turn a scored trial into a
# non-zero verifier exit.
export PYTHONDONTWRITEBYTECODE=1
logs=/logs/verifier
mkdir -p "$logs" || exit 1
printf '0\n' > "$logs/reward.txt"
printf '{"reward":0}\n' > "$logs/reward.json"
rm -f "$logs/report.json" "$logs/ctrf.json"

python3 -I -B /tests/scoring/eval.py --submission-dir "${1:-/workspace}" --log-dir "$logs" || exit 0

python3 -I -B -c 'import json,pathlib; r=json.loads(pathlib.Path("/logs/verifier/report.json").read_text()); pathlib.Path("/logs/verifier/reward.json").write_text(json.dumps({"reward": float(r["score"])})+"\n")' || exit 0

if command -v rewardkit >/dev/null 2>&1; then
  rewardkit /tests --workspace "${1:-/workspace}" --output "$logs/reward.json" || exit 0
fi
exit 0
