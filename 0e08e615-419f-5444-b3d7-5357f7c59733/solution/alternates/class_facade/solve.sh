#!/bin/sh
set -eu
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHONDONTWRITEBYTECODE=1 "${PYTHON:-python3}" -B "$here/settlement.py" "$1" "$2"
