#!/bin/sh
# Alternate oracle B: split module layout.
set -eu
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
out="${1:-${WORKSPACE:-/workspace}}"
PYTHONDONTWRITEBYTECODE=1 python3 -I -B "$here/driver.py" "$out" "$out/predictions.jsonl" || { echo "alternate B: lane fitting aborted" >&2; exit 2; }
cat "$here/transport.py" "$here/lanes.py" "$here/driver.py" > "$out/receivables_surveillance.py"
: > "$out/requirements.txt"
