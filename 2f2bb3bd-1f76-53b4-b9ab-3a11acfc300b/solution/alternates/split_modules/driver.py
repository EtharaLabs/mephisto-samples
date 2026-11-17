"""Alternate split-layout oracle driver."""
import argparse
import json
from pathlib import Path
import numpy as np
from transport import LANES, read_rows, write_rows
from lanes import fit_discrepancy_count, predict_discrepancy_count, fit_discrepancy_class_profile, predict_discrepancy_class_profile, refusal_design, fit_refusal_flag, predict_refusal_flag, fit_tenor_tier, predict_tenor_tier, priority_basis, fit_examiner_priority_rank, priority_score, predict_examiner_priority_rank, fit_charge_reserve, predict_charge_reserve

# --- oracle entry point -------------------------------------------------------------------

def records(workspace, queries=None):
    queries = read_rows(Path(workspace) / 'queries.jsonl') if queries is None else queries
    fitted = {lane: globals()['fit_' + lane](workspace) for lane in LANES}
    return [dict(record_id=r['record_id'], **{
        lane: globals()['predict_' + lane](fitted[lane], r['beneficiary_id'], r['period'], workspace)
        for lane in LANES}) for r in queries]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    write_rows(args.output, records(args.workspace))


if __name__ == '__main__':
    main()
