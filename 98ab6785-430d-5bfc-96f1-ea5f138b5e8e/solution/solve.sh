#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1
solution_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
workspace=${1:-/workspace}
data=${2:-/workspace/data}
cp "$solution_dir/reserving_reference.py" "$workspace/reserving.py"
: > "$workspace/requirements.txt"
python3 -B "$workspace/reserving.py" --data-dir "$data" --output "$workspace/reserving_results.json"
