"""Alternate transport boundary; no fitted state is shared across lanes."""
import json
from pathlib import Path


def queries(workspace):
    return [json.loads(line) for line in (Path(workspace) / 'queries.jsonl').read_text().splitlines()]
