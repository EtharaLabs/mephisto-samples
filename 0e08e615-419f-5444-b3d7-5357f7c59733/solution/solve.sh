#!/bin/sh
# Privileged oracle: recompute from the public workspace, never copy hidden truth.
set -eu
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
workspace="${1:-${WORKSPACE:-/workspace}}"
output="${2:-$workspace}"
mkdir -p "$output"
"${PYTHON:-python3}" -B "$here/estimators.py" --workspace "$workspace" --output "$output/predictions.jsonl"
cp "$here/estimators.py" "$output/transfer_pricing_settlement.py"
cp "$here/../environment/requirements.txt" "$output/requirements.txt"
