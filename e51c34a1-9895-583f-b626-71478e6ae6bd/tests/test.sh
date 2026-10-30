#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
exec rewardkit /tests --workspace /home/workspace --output /logs/verifier/reward.json
