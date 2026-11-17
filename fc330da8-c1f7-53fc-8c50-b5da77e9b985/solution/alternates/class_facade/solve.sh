#!/bin/sh
# Alternate oracle C: class facade, reverse evaluation order.
set -eu
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
out="${1:-${WORKSPACE:-/workspace}}"
PYTHONDONTWRITEBYTECODE=1 python3 -I -B "$here/surveillance.py" "$out" "$out/predictions.jsonl" || { echo "alternate C: facade could not answer every record" >&2; exit 3; }
cp "$here/surveillance.py" "$out/floorplan_surveillance.py"
: > "$out/requirements.txt"
