#!/bin/sh
# Privileged oracle: recompute all six lanes from public observations, never copy truth.
set -eu
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
workspace="${1:-${WORKSPACE:-/workspace}}"
out="${2:-$workspace}"
mkdir -p "$out"
python3 -I -B "$here/estimators.py" --workspace "$workspace" --output "$out/predictions.jsonl"
cp "$here/estimators.py" "$out/documentary_credit_examination.py"
printf 'numpy==2.1.3\n' > "$out/requirements.txt"
