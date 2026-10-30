#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1
exec python3 -I -B /tests/scoring/entrypoint.py
