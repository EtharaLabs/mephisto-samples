# Desk manual: fund administration NAV oversight

This manual states the schema and accounting conventions, not how to estimate the desk's values. `history/oversight.jsonl` is the sole reference for what the desk's actual output looks like.

## Deliverables and records

Submit `predictions.jsonl`, `fund_nav_oversight.py` and `requirements.txt` in `/workspace`. The desk reads the filed records as submitted; it does not re-run the script.
The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

| field | type | units and range | precision |
|---|---|---|---|
| record_id | string | `<fund_id>:p<period>` exactly as queried | exact |
| nav_break_magnitude | number | basis points, non-negative | 2 decimal places |
| fee_accrual_profile | array | 8 non-negative masses, total at most 1 | up to 8 decimal places recommended |
| restatement_flag | integer | 0 or 1 | exact |
| pricing_source_tier | integer | 0 through 3 | exact |
| oversight_rank | integer | 1 through cohort population | exact |
| expense_reserve | number | USD, non-negative | 2 decimal places |

The filed `oversight_rank` must be an integer from 1 through the cohort size.

NAV breaks are absolute differences between production and independently reconciled NAV, divided by reconciled NAV and multiplied by 10,000. All underlying class exposures have already been translated to the fund's USD base currency at the production cut. This is oversight of aggregate fund production, not a request to compute an individual share class price. Daily funds contribute a monthly review snapshot of their daily production; monthly funds contribute their month-end production.

Fee components, in order: management fee, performance fee, administration fee, custody fee, audit fee, transfer agency, regulatory, other. The residual is accrual not yet assigned to any component, pending invoice allocation. It is separate from `other`, which is an identified expense category. The ninth entry of a completed case's `component_amounts` records this unallocated amount; all nine entries are USD, not proportions. Performance fee inputs reflect positive returns before any desk-estimated accrual allocation.

`restatement_flag` is the desk's decision to reissue a NAV following processing review, not a future random incident. `pricing_source_tier` refers to the dominant source by priced exposure: 0 unreliable, 1 limited, 2 supported, 3 independently corroborated. Source-count and dispersion fields aggregate multiple independent quotes; exchange coverage is a fraction of priced exposure.

`oversight_rank` orders estimated review workload, highest first. The cohort is all funds in queries with the same period. Reference funds form a separate reference cohort. Equal workloads share a rank and the next distinct workload gets the next integer (dense ranks). It is not a rank of another output lane.

`expense_reserve` is expected invoice overrun against the annual fund expense budget, net of contractual waivers. It is measured in USD, not basis points.

## Ledger and field conventions

Periods are monthly review cuts numbered 1 through 20. `snapshot` rows describe one fund at a cut; `closed` rows are independently completed cases, not the desk's own oversight outputs. `event_period` is completion, `booked_period` is ledger entry. Corrected cases have `restated_period` and original outcome fields under `as_booked`; top-level outcomes contain eventual corrected amounts. Future booking or correction is not information available at an earlier cut. Snapshot observations are available at their cut. Cases booked at that cut are available only to the next review.

All fields ending in `_share`, `coverage`, `completion`, `rate` (except `_bps`) and `utilisation` are dimensionless. Days and hours have their named units. `_log` is natural log of USD. Counts in snapshots are period-average counts and may be fractional. `group` is a view-specific operating segment, not a shared group across ledgers. `complexity`, `vendor_stress`, `turnover` and `leverage` are dimensionless control indices. `cycle_phase` is a fraction of the production cycle. `annual_budget` and closed `overrun_amount` are USD. `break_bps`, `reissued`, `reliability` and `review_hours` are completed-case outcomes in the corresponding ledgers. Reliability is a reviewed fraction, not a tier label.

## Tolerances

Materiality is 1 basis point for NAV and 100 USD for expenses.

## Acceptance

Duplicate IDs are discarded in full. Unknown IDs are ignored. Exactly seven keys are requested. No numeric booleans, non-finite numbers, negative amounts, fractional class labels, or overfull fee vectors are accepted. Monetary and basis-point outputs are checked at 2dp with tolerance 1e-7 on the value multiplied by 100; vector sum tolerance is 1e-9. `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse.
