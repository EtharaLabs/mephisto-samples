# Transfer pricing intercompany settlement

You are the review analyst for a multinational group's transfer pricing unit. The desk reviews intercompany charges across a register of 360 entity pairs and settles arm's-length adjustments. Reproduce its review record for the entity-pair-periods listed in `/workspace/queries.jsonl`.

## What you are given

Everything under `/workspace` is yours to read.

| path | contents |
|---|---|
| `register/<pair_id>.json` | provider and recipient legal entities, jurisdictions, functional role, jurisdiction band and APA reference |
| `invoices/<period>.jsonl` | closed intercompany charge reviews and current charge-base snapshots |
| `allocation_drivers/<period>.jsonl` | closed cost-allocation studies and current benefit/driver snapshots |
| `tax_audits/<period>.jsonl` | closed authority challenge cases and current audit-risk snapshots |
| `comparables/<period>.jsonl` | closed benchmarking method decisions and current comparability snapshots |
| `settlements/<period>.jsonl` | closed settlement reviews, current settlement bases and amounts paid on account |
| `tax_positions/<period>.jsonl` | closed uncertain-tax positions and current exposure snapshots |
| `/workspace/history/review.jsonl` | the desk's own published review records for closed periods |
| `/workspace/queries.jsonl` | the entity-pair-periods you must produce records for |
| `/workspace/manual/review_manual.md` | schema, units, OECD-style conventions, tolerances and acceptance rules |
| `/workspace/dataset_metadata.json` | period, currency, feature and allocation-key definitions |

`/workspace/history/review.jsonl` is the desk's own prior output. It is the only statement of what the desk's records look like in practice. Closed operational outcomes in the other trees are not desk review records.

## What you must produce

Write three files to `/workspace`.

| file | contents |
|---|---|
| `/workspace/predictions.jsonl` | one JSON object per line, one per record in `/workspace/queries.jsonl` |
| `/workspace/transfer_pricing_settlement.py` | the code that produced them |
| `/workspace/requirements.txt` | your dependencies, empty if you used only the standard library |

File all three. `/workspace/predictions.jsonl` must be present and parseable — the desk reads it as filed and does not re-run your code.
The task module and `/workspace/requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record schema

One object per entity-pair-period in `/workspace/queries.jsonl`, with exactly these seven keys. The table defines structure, not an output distribution; consult history for examples.

| field | type | units and constraints |
|---|---|---|
| `record_id` | string | exactly `<pair_id>:p<period>`, matching `/workspace/queries.jsonl` |
| `adjustment_magnitude` | number | nonnegative USD adjustment magnitude, two decimal places |
| `allocation_key_profile` | array | exactly 8 nonnegative floats, sum at most 1.0, ordered headcount, revenue, assets, transactions, floor space, compute, licences, other |
| `challenge_flag` | integer | 0 or 1: whether the desk records an authority challenge |
| `method_tier` | integer | 0 CUP, 1 cost plus, 2 resale minus, 3 profit split |
| `review_rank` | integer | 1-based dense rank within the requested period cohort; 1 is highest estimated unsettled review priority |
| `uncertain_tax_reserve` | number | nonnegative USD reserve, two decimal places, on a different scale from adjustment magnitude |

The filed `review_rank` must be an integer from 1 through the cohort size.

The allocation residual `1 - sum(allocation_key_profile)` is meaningful: the share retained by the provider as shareholder or unsupported-benefit costs. Do not force it to zero.

## How the desk reviews a record

All six fields carry equal importance and are reviewed independently. A problem in one does not invalidate the others.

## Acceptance rules

- Produce a record for every row in `/workspace/queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full. Submit each record once.
- Non-finite values invalidate only their own field value.
- For `challenge_flag` and `method_tier`, a missing, non-integer or out-of-range value is recorded as an incorrect answer for that record; omitting a value is never better than submitting your best estimate.
- `/workspace/predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse. Isolated malformed lines contribute no records. Unknown record IDs are ignored.
- Rank ties are allowed: equal estimated priority means equal rank, with the next distinct priority receiving the next integer. Rank bounds use the requested cohort size.

Every field is derivable from the records under `/workspace`.
