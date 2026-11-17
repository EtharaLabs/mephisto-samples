#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
workspace="${1:-/workspace}"
out="${2:-$workspace}"
mkdir -p "$out"
python3 -B "$here/examination.py" --workspace "$workspace" --output "$out/predictions.jsonl"
