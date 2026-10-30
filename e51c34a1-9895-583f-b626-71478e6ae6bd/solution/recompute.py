# FORGE-CANARY-BEGIN
# FORGE-CANARY-SLOT-1: e982fee812b5db6e9f890a98d66334cb7a9a324515072566d5780345e6ee8a9c
# FORGE-CANARY-SLOT-2: 97a6b6a2007bfe0ad300b51a4ac2531e30f4dde5a95df7e3a8f8172eaba817aa
# FORGE-CANARY-SLOT-3: 1965d48ddc98c2c5d420e105285aee7a42781cb1e90dd17cf92ec0177d94790a
# FORGE-CANARY-END
"""Regenerate TRUTH.md, the compiled criteria, the verifier fixtures and solve.sh from grounding.

Run from the task directory: python solution/recompute.py. Reads solution/grounding.yaml only;
no network, clock, locale or random source is consulted.
"""

import json
from pathlib import Path

BANNER = "GENERATED SECTION. DO NOT HAND-EDIT."
PLACEHOLDER = "0" * 64
SLOTS = 3


def canary(open_marker, close_marker=""):
    lines = [f"{open_marker} FORGE-CANARY-BEGIN{close_marker}"]
    lines += [f"{open_marker} FORGE-CANARY-SLOT-{n}: {PLACEHOLDER}{close_marker}" for n in range(1, SLOTS + 1)]
    lines.append(f"{open_marker} FORGE-CANARY-END{close_marker}")
    return "\n".join(lines) + "\n"


def load_grounding():
    text = Path("solution/grounding.yaml").read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return json.loads(body)


def _scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(value)


def _yaml(value, indent=0):
    pad = " " * indent
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
    else:
        for item in value:
            if isinstance(item, dict):
                first, *rest = _yaml(item, indent + 2)
                lines.append(f"{pad}- {first.strip()}")
                lines.extend(rest)
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    return lines


def provenance(g):
    return canary("#") + f"# {BANNER}\n" + "\n".join(_yaml(g["provenance"])) + "\n"


def money(value):
    return f"{value:,.2f}"


def truth(g):
    e, s = g["expected"], g["summary"]
    terms, anchors = e["mandate"], e["anchors"]
    items = {item["id"]: item for item in g["rubric"]["items"]}
    loans = e["loans"]
    out = [f"<!-- {BANNER} -->", canary("<!--", " -->").rstrip("\n"), "",
           "# TRUTH: auto-loan ABS forward-flow purchase", "",
           f"Boundary tape {g['boundary']}; hidden outcome tapes {', '.join(g['hidden_window'])}. Golden trajectory "
           "through instruction.md; every step binds one manifest deliverable or red line and names the criteria "
           "that grade it.", "",
           "## Golden trajectory", "", "| Step | Action | Binds | Criteria |", "| --- | --- | --- | --- |"]
    for step in g["steps"]:
        out.append(f"| {step['id']} | {step['action']} | {step['obligation']} | {', '.join(step['checkers'])} |")
    out += ["", "## Criteria", "", "| Criterion | Obligation | Dimension | Weight | Credit |",
            "| --- | --- | --- | --- | --- |"]
    for item in g["rubric"]["items"]:
        out.append(f"| {item['id']} | {item['obligation']} | {item['dimension']} | {item['weight']} | {item['criterion']} |")
    scoring = g["scoring"]
    out += ["", "## Scoring", "", scoring["statement"], "", scoring["gate"], "",
            "| Term | Value |", "| --- | --- |",
            f"| offered loans | {terms['loans']:,} |", f"| offered price, USD | {money(terms['offer_usd'])} |",
            f"| budget, USD | {money(terms['budget_usd'])} |", f"| pool cap, USD | {money(terms['pool_cap_usd'])} |",
            f"| delinquent cap, USD | {money(terms['delinquent_cap_usd'])} |",
            f"| deployment floor, USD | {money(terms['deployment_floor_usd'])} |",
            f"| tolerance, USD | {terms['tolerance_usd']:.2f} |",
            f"| zero-credit value (pro rata slice), USD | {money(anchors['value_zero_usd'])} |",
            f"| full-credit value (hindsight optimum), USD | {money(anchors['value_full_usd'])} |",
            f"| realized charge-off share of offered loans | {anchors['chargeoff_mean']:.6f} |",
            f"| Brier reference sum | {anchors['brier_reference']:.4f} |"]
    out += ["", "## September marks (per dollar of balance)", "", "| Bucket | Mark |", "| --- | --- |"]
    out += [f"| {bucket} | {s['marks'][bucket]:.2f} |" for bucket in g["buckets"]]
    out += ["", "## Offer price grid (per dollar of June balance)", "",
            "| Bucket | " + " | ".join(g["bands"]) + " |", "| --- |" + " --- |" * len(g["bands"])]
    for bucket in g["buckets"]:
        out.append(f"| {bucket} | " + " | ".join(f"{s['grid'][bucket + '|' + band]:.4f}" for band in g["bands"]) + " |")
    out += ["", "## Reference answer: offer pools", "",
            "| Pool | Trust | Loans | Offered USD | Bought USD | Charged off | Paid | Refunded | Live | Recovery |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    bought = {}
    for index, fraction in g["oracle"]["fractions"]:
        pool = e["pools"][loans["pool"][index]]
        bought[pool] = bought.get(pool, 0.0) + fraction * loans["price"][index]
    for pool in s["pools"]:
        st = s["states"].get(pool["pool"], {})
        out.append(f"| {pool['pool']} | {pool['trust']} | {pool['loans']:,} | {money(pool['offer_usd'])} | "
                   f"{money(bought.get(pool['pool'], 0.0))} | {st.get('chargeoff', 0):,} | {st.get('paid', 0):,} | "
                   f"{st.get('refund', 0):,} | {st.get('live', 0):,} | {st.get('recovery', 0):,} |")
    out += ["", "## Reference answer: deliverables", "",
            f"- purchases.csv: {len(g['oracle']['fractions']):,} participations, the linear-programme optimum on "
            "realized values within the budget, the deployment band and both caps, half a dollar inside each bound.",
            "- chargeoff_probabilities.csv: 1 for every offered loan charged off on the hidden tapes, 0 otherwise.",
            "- memo.json: the committed amounts recomputed from purchases.csv, the realized value as expected value, "
            "and the charged-off balance of the purchased participations.", "",
            "## Reference trusts shown to the agent", "", "| Trust tape | Trust | Months | Loans |", "| --- | --- | --- | --- |"]
    for ref in s["reference"]:
        out.append(f"| {ref['slug']} | {ref['trust']} | {ref['first']} to {ref['last']} | {ref['loans']:,} |")
    out += ["", "## Rejected routes", "", "| Route | Known-wrong control |", "| --- | --- |"]
    for route in g["rejected_routes"]:
        out.append(f"| {route['route']} | {route['control']} |")
    out += ["", "## Not applicable rubric cells", ""]
    for cell, reason in sorted(g["rubric"]["not_applicable"].items()):
        out.append(f"- {cell}: {reason}")
    missing = {c for step in g["steps"] for c in step["checkers"]} ^ set(items)
    if missing:
        raise SystemExit(f"steps and criteria disagree: {sorted(missing)}")
    return "\n".join(out) + "\n"


CRITERIA = '''"""Compiled rubric criteria; each function credits one item of the forward-flow purchase in [0, 1]."""

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
'''

REWARD = """[[reward]]
name = "reward"
aggregation = "weighted-mean"

[scoring.test_output]
aggregation = "weighted-mean"
"""


def main():
    g = load_grounding()
    Path("solution/TRUTH.md").write_text(truth(g), encoding="utf-8")
    Path("solution/provenance.yaml").write_text(provenance(g), encoding="utf-8")
    fixtures = dict(g["expected"])
    fixtures["items"] = [{"id": i["id"], "weight": i["weight"]} for i in g["rubric"]["items"]]
    fixtures["layout"] = g["layout"]
    Path("tests/expected.json").write_text(json.dumps(fixtures, sort_keys=True, separators=(",", ":")) + "\n",
                                           encoding="utf-8")
    Path("tests/test_output.py").write_text(CRITERIA, encoding="utf-8")
    Path("tests/reward.toml").write_text(REWARD, encoding="utf-8")
    solve = Path("solution/solve.sh")
    solve.write_text("#!/bin/bash\n" + canary("#") + "set -euo pipefail\n"
                     "python3 - /solution/grounding.yaml /home/workspace/output <<'ORACLE'\n" + g["oracle_source"]
                     + "ORACLE\n", encoding="utf-8")
    solve.chmod(0o755)


main()
