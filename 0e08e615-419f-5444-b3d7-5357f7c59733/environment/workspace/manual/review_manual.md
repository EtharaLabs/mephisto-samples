# Intercompany settlement review manual

## Scope and units

This manual is not tax advice or a statement of any jurisdiction's law. Provider and recipient legal entities join through `pair_id` in `register/`. All amounts are USD equivalent, already converted; do not convert them again. Periods are consecutive month-end indices. `dataset_metadata.json` supplies feature names and category order.

The eight operational trees are register, invoices, allocation_drivers, tax_audits, comparables, settlements, tax_positions, and history. Register jurisdiction bands participate in modelling; they are not method labels. APA references identify the relevant arrangement, while `apa_coverage` measures the covered share in the audit view. A reference alone does not imply immunity from a challenge.

## Ledger conventions

Each period-sharded operational file mixes `kind: snapshot` and `kind: closed`. Snapshot keys are `(pair_id, period)`. Closed cases have `case_id`, `event_period`, `booked_period`, and `outcome`. The filename is a source-period shard, not a guarantee that every contained case was booked that month. A restated case carries the corrected top-level outcome, `restated_period`, and the original outcome under `as_booked`. These fields permit reconstruction of the ledger known at a review date. Do not confuse a closed-case observation with a published review label.

All named feature indices and driver shares are dimensionless numbers on [0,1], including normalized age and count indices. They are not raw years or event counts. Driver shares have independent denominators and need not sum to one. `charge_base`, `settlement_base`, `paid_on_account`, and `tax_exposure` are USD amounts.

| view | closed `outcome` | snapshot interpretation |
|---|---|---|
| invoices | agreed adjustment / reviewed charge base | margin and functional evidence; multiply an estimated ratio by charge base to obtain currency |
| allocation_drivers | eight agreed cost-base fractions | benefit evidence and operational allocation drivers; retained provider cost is the residual |
| tax_audits | recorded authority challenge, 0 or 1 | audit exposure, prior challenge and APA evidence |
| comparables | method code 0..3 selected in a completed comparable study | similarity, traceability, resale observability, integration and unique intangibles |
| settlements | settlement-priority ratio before payments on account | estimated gross review priority is scaled to settlement base, with payments deducted |
| tax_positions | realised tax-loss fraction of tax exposure, including zero | tax, treaty, documentation, interest and provision evidence |

## OECD-style method conventions

CUP compares sufficiently comparable uncontrolled prices; cost plus examines an appropriate markup on a traceable cost base; resale minus starts from resale value and an appropriate gross margin; profit split addresses integrated operations and unique contributions. Codes 0,1,2,3 are this desk's ordered review categories, not a universal OECD ranking. Historical records establish the desk's application of these conventions.

## Submission schema

One JSON object for every requested `record_id`, with exactly `record_id`, `adjustment_magnitude`, `allocation_key_profile`, `challenge_flag`, `method_tier`, `review_rank`, `uncertain_tax_reserve`. Currency values are nonnegative, rounded to cents. JSON numbers do not preserve trailing zeroes: 12.5 and 12.50 represent the same amount. Flags and method/rank values must be JSON integers, not strings or booleans.

Allocation order is headcount, revenue, assets, transactions, floor space, compute, licences, other. Exactly eight finite nonnegative numbers, total at most one (floating summation tolerance 1e-9). The residual is retained provider cost, not missing data. Do not renormalize it away. Only `history/review.jsonl` describes output distributions in practice.

Each requested period is one rank cohort; do not mix periods. Rank one is the highest estimated unsettled review priority. Equal priorities receive the same rank; the next distinct priority gets the next integer. Historical cohorts consist of the records published in that period; requested cohorts consist only of queries in that period.

The filed `review_rank` must be an integer from 1 through the cohort size.

## Acceptance rules

Materialities are USD 500 for adjustment and USD 50 for reserve.

Duplicated IDs are dropped in full. Unknown IDs are ignored. Submission cap is 20,000,000 bytes. `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse. Malformed lines yield no record. Non-finite numbers invalidate only their field value. The desk reads the filed records as submitted; it does not re-run the script. Submit code and requirements alongside predictions for collection.

The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

For `challenge_flag` and `method_tier`, a missing, non-integer or out-of-range value is recorded as an incorrect answer for that record; omitting a value is never better than submitting your best estimate.
