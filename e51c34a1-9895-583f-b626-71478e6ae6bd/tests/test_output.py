"""Compiled rubric criteria; each function credits one item of the forward-flow purchase in [0, 1]."""

import csv
import json
import math
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

from rewardkit import criteria, criterion

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
LOANS = EXPECTED["loans"]
POOLS = EXPECTED["pools"]
TERMS = EXPECTED["mandate"]
ANCHORS = EXPECTED["anchors"]
LAYOUT = EXPECTED["layout"]
INDEX = {(POOLS[p], a): i for i, (p, a) in enumerate(zip(LOANS["pool"], LOANS["asset"]))}
SLACK = TERMS["tolerance_usd"]


def _cents(value):
    return float(Decimal(repr(value)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _number(text):
    value = float(text)
    return value if math.isfinite(value) else None


def _rows(folder, name):
    path = folder / LAYOUT[name]["file"]
    with open(path, newline="", encoding="utf-8-sig") as handle:
        table = list(csv.reader(handle))
    if not table or [cell.strip() for cell in table[0]] != LAYOUT[name]["columns"]:
        return None
    return [[cell.strip() for cell in row] for row in table[1:] if any(cell.strip() for cell in row)]


def _keyed(rows, low, high, closed_low):
    """Map each named offered loan to its number; None when a loan is unknown, repeated or out of range."""
    seen = {}
    for row in rows:
        if len(row) != 3 or (row[0], row[1]) not in INDEX:
            return None
        index = INDEX[(row[0], row[1])]
        value = _number(row[2])
        if index in seen or value is None or value > high or value < low or (value == low and not closed_low):
            return None
        seen[index] = value
    return seen


def _purchase(folder):
    rows = _rows(folder, "purchases")
    return None if rows is None else _keyed(rows, 0.0, 1.0, False)


def _committed(bought):
    total, delinquent = 0.0, 0.0
    by_pool = {pool: 0.0 for pool in POOLS}
    for index, fraction in bought.items():
        amount = fraction * LOANS["price"][index]
        total += amount
        by_pool[POOLS[LOANS["pool"][index]]] += amount
        delinquent += amount * LOANS["delinquent"][index]
    return total, by_pool, delinquent


def _admissible(bought):
    total, by_pool, delinquent = _committed(bought)
    within_budget = TERMS["deployment_floor_usd"] - SLACK <= total <= TERMS["budget_usd"] + SLACK
    within_pools = max(by_pool.values()) <= TERMS["pool_cap_usd"] + SLACK
    return within_budget and within_pools and delinquent <= TERMS["delinquent_cap_usd"] + SLACK


@lru_cache(maxsize=8)
def _book(workspace):
    folder = Path(workspace) / LAYOUT["folder"]
    bought = _purchase(folder)
    if bought is None or not _admissible(bought):
        return None
    try:
        rows = _rows(folder, "probabilities")
        chances = None if rows is None else _keyed(rows, 0.0, 1.0, True)
    except (OSError, ValueError, csv.Error, UnicodeDecodeError):
        chances = None
    if chances is not None and len(chances) != len(INDEX):
        chances = None
    try:
        memo = json.loads((folder / LAYOUT["memo"]["file"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        memo = None
    return bought, chances, memo if isinstance(memo, dict) else None


def _capture(book):
    bought = book[0]
    value = 0.0
    for index, fraction in bought.items():
        value += fraction * LOANS["value"][index]
    span = ANCHORS["value_full_usd"] - ANCHORS["value_zero_usd"]
    return _cents(max(0.0, min(1.0, (value - ANCHORS["value_zero_usd"]) / span)))


def _skill(book):
    chances = book[1]
    if chances is None:
        return 0.0
    error = 0.0
    for index, flag in enumerate(LOANS["chargeoff"]):
        error += (chances[index] - flag) ** 2
    return _cents(max(0.0, min(1.0, 1.0 - error / ANCHORS["brier_reference"])))


def _close(stated, actual):
    return isinstance(stated, (int, float)) and not isinstance(stated, bool) and abs(stated - actual) <= SLACK


def _memo(book):
    bought, chances, memo = book
    if memo is None:
        return 0.0
    keys = LAYOUT["memo"]["keys"]
    total, by_pool, delinquent = _committed(bought)
    stated_pools = memo.get(keys["by_pool"])
    exposure = None
    if chances is not None:
        exposure = 0.0
        for index, fraction in bought.items():
            exposure += fraction * chances[index] * LOANS["balance"][index]
    count = memo.get(keys["count"])
    expected = memo.get(keys["value"])
    holds = [
        _close(memo.get(keys["total"]), total),
        isinstance(stated_pools, dict) and set(stated_pools) <= set(POOLS)
        and all(_close(stated_pools.get(pool, 0.0), amount) for pool, amount in by_pool.items()),
        _close(memo.get(keys["delinquent"]), delinquent),
        isinstance(count, int) and not isinstance(count, bool) and count == len(bought),
        isinstance(expected, (int, float)) and not isinstance(expected, bool) and math.isfinite(expected),
        exposure is not None and _close(memo.get(keys["exposure"]), exposure),
    ]
    return _cents(sum(holds) / len(holds))


CHECKS = {
    "D1-outcome-capture": _capture,
    "D2-outcome-skill": _skill,
    "D3-craft-memo": _memo,
}


@criterion(shared=True)
def forward_flow(workspace: Path, item_id: str) -> float:
    try:
        book = _book(str(workspace))
        return 0.0 if book is None else float(CHECKS[item_id](book))
    except (OSError, KeyError, TypeError, ValueError, ArithmeticError, csv.Error, UnicodeDecodeError):
        return 0.0


for _item in EXPECTED["items"]:
    criteria.forward_flow(_item["id"], weight=_item["weight"], name=_item["id"])
