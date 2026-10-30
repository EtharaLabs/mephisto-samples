#!/bin/bash
# FORGE-CANARY-BEGIN
# FORGE-CANARY-SLOT-1: e982fee812b5db6e9f890a98d66334cb7a9a324515072566d5780345e6ee8a9c
# FORGE-CANARY-SLOT-2: 97a6b6a2007bfe0ad300b51a4ac2531e30f4dde5a95df7e3a8f8172eaba817aa
# FORGE-CANARY-SLOT-3: 1965d48ddc98c2c5d420e105285aee7a42781cb1e90dd17cf92ec0177d94790a
# FORGE-CANARY-END
set -euo pipefail
python3 - /solution/grounding.yaml /home/workspace/output <<'ORACLE'
"""Hindsight oracle: write the optimal purchase, the realized charge-offs and a consistent memo.

argv: <grounding.yaml> <output folder>. Reads the private grounding only; the purchase is the
linear-programme optimum on realized values, so it scores full reward and no solver can match it.
"""

import csv
import json
import sys
from pathlib import Path


def main():
    grounding, folder = Path(sys.argv[1]), Path(sys.argv[2])
    text = grounding.read_text(encoding="utf-8")
    body = json.loads("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    expected = body["expected"]
    loans, pools = expected["loans"], expected["pools"]
    bought = body["oracle"]["fractions"]
    folder.mkdir(parents=True, exist_ok=True)
    committed, by_pool, delinquent, exposure = 0.0, {pool: 0.0 for pool in pools}, 0.0, 0.0
    with open(folder / "purchases.csv", "w", newline="", encoding="utf-8") as handle:
        rows = csv.writer(handle, lineterminator="\n")
        rows.writerow(["pool", "assetNumber", "fraction"])
        for index, fraction in bought:
            pool = pools[loans["pool"][index]]
            rows.writerow([pool, loans["asset"][index], repr(fraction)])
            amount = fraction * loans["price"][index]
            committed += amount
            by_pool[pool] += amount
            if loans["delinquent"][index]:
                delinquent += amount
            exposure += fraction * loans["chargeoff"][index] * loans["balance"][index]
    with open(folder / "chargeoff_probabilities.csv", "w", newline="", encoding="utf-8") as handle:
        rows = csv.writer(handle, lineterminator="\n")
        rows.writerow(["pool", "assetNumber", "probability"])
        for pool, asset, flag in zip(loans["pool"], loans["asset"], loans["chargeoff"]):
            rows.writerow([pools[pool], asset, flag])
    memo = {
        "committed_usd": round(committed, 2),
        "committed_by_pool_usd": {pool: round(amount, 2) for pool, amount in by_pool.items()},
        "committed_delinquent_usd": round(delinquent, 2),
        "loans_bought": len(bought),
        "expected_value_usd": round(expected["anchors"]["value_full_usd"], 2),
        "expected_chargeoff_balance_usd": round(exposure, 2),
    }
    (folder / "memo.json").write_text(json.dumps(memo, indent=2) + "\n", encoding="utf-8")


main()
ORACLE
