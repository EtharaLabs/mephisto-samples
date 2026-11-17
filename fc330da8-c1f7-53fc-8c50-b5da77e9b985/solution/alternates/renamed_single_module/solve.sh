#!/bin/sh
# Alternate oracle A: one renamed module.
set -eu
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
out="${1:-${WORKSPACE:-/workspace}}"
PYTHONDONTWRITEBYTECODE=1 python3 -I -B "$here/desk_methods.py" --workspace "$out" --output "$out/predictions.jsonl" || { echo "alternate A failed to fit the desk methods" >&2; exit 1; }
cp "$here/desk_methods.py" "$out/floorplan_surveillance.py"
: > "$out/requirements.txt"
