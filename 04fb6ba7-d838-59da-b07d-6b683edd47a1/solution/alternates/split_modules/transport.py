"""Alternate oracle B, transport layer: file reading, ledger view and numeric helpers.

Standard library only. Each lane carries its own fitted estimator over its own data view,
and no estimator reads another lane's data, labels, or fitted object; the only shared code is
transport (file reading) and ordering helpers that hold no fitted state.

Ledger discipline, applied identically in every lane: a surveillance record at period q is
fitted on closed rows booked strictly before q, and each closed row enters the fit with the
values the ledger carried at q. A row restated at or after q enters with its as_booked values.

"""
import json
import math
import sys
from pathlib import Path
from statistics import median

LANES = ('dilution_reserve', 'collection_profile', 'dispute_flag', 'recovery_tier', 'availability_rank', 'loss_reserve')
FIT_PERIODS = (8, 10, 12, 16, 20)
BUCKET_UPPER_DAYS = [15, 30, 45, 60, 90, 120, 180, 270]


# --- transport and ordering helpers (no fitted state) ---------------------------------------

def read_rows(path):
    with open(path) as stream:
        return [json.loads(line) for line in stream if line.strip()]


def read_tree(workspace, name):
    return [row for path in sorted((Path(workspace) / name).glob('*.jsonl'), key=lambda p: (len(p.stem), p.stem))
            for row in read_rows(path)]


def asof(rows, q):
    """Closed rows booked before q, each carrying the values the ledger held at q."""
    out = []
    for r in rows:
        if r.get('kind') != 'closed' or r['booked_period'] >= q:
            continue
        if 'restated_period' in r and r['restated_period'] >= q:
            r = dict(r, **r['as_booked'])
        out.append(r)
    return out


def recency(q, booked, tau):
    return math.exp(-(q - 1 - booked) / tau)


def expit(x):
    return 1.0 / (1.0 + math.exp(-x)) if x > -700 else 0.0


def logit(p):
    return math.log(p / (1 - p))


def mad_scale(values, floor):
    centre = median(values)
    return max(floor, median(abs(v - centre) for v in values))


def solve(matrix):
    """Gauss-Jordan on an augmented matrix; returns the solution vector."""
    width = len(matrix)
    m = [list(row) for row in matrix]
    for i in range(width):
        pivot = max(range(i, width), key=lambda j: abs(m[j][i]))
        m[i], m[pivot] = m[pivot], m[i]
        divisor = m[i][i] if abs(m[i][i]) > 1e-12 else 1e-12
        m[i] = [v / divisor for v in m[i]]
        for j in range(width):
            if i != j and m[j][i] != 0.0:
                factor = m[j][i]
                m[j] = [a - factor * b for a, b in zip(m[j], m[i])]
    return [m[i][-1] for i in range(width)]


def dense_ranks_descending(values):
    order = {value: i + 1 for i, value in enumerate(sorted(set(values.values()), reverse=True))}
    return {key: order[value] for key, value in values.items()}


