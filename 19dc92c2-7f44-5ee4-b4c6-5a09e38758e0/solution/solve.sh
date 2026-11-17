#!/bin/sh
# Oracle recomputes from published inputs; hidden truth is never read.
set -eu
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
OUT="${1:-/workspace}"
python3 -B "$HERE/estimators.py" --workspace "$OUT" --output "$OUT/predictions.jsonl"
cp "$HERE/estimators.py" "$OUT/fund_nav_oversight.py"
printf 'numpy==2.1.3\n' > "$OUT/requirements.txt"
