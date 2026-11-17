#!/bin/sh
# Privileged oracle: recompute the desk's six fitted lanes from the public workspace alone.
# It never copies the judge's truth; the estimators are deterministic, so the bytes agree.
set -eu
solution_dir="${SOLUTION_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
out="${1:-${WORKSPACE:-/workspace}}"
mkdir -p "$out"
PYTHONDONTWRITEBYTECODE=1 python3 -I -B "$solution_dir/estimators.py" --workspace "$out" --output "$out/predictions.jsonl"
cp "$solution_dir/estimators.py" "$out/receivables_surveillance.py"
: > "$out/requirements.txt"
