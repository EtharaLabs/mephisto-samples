# Desk manual: receivables finance portfolio surveillance

This manual states what a surveillance record must contain and how it is accepted. It does not state how to arrive at the values. The desk's own published records in `history/surveillance.jsonl` are the reference for what its output looks like in practice.

## Deliverables

Three files in `/workspace`.

| file | contents |
|---|---|
| `predictions.jsonl` | one surveillance record per line, one per entry in `queries.jsonl` |
| `receivables_surveillance.py` | the code that produced the records |
| `requirements.txt` | dependencies, empty if only the standard library was used |

File all three. `predictions.jsonl` must be present and parseable. The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record fields

| field | type | units | range | precision |
|---|---|---|---|---|
| `record_id` | string | none | exactly `<obligor_id>:p<period>` | exact match required |
| `dilution_reserve` | number | currency | at least 0 | two decimal places |
| `collection_profile` | array of 8 floats | mass | each at least 0, total at most 1.0 | eight decimal places |
| `dispute_flag` | integer | none | 0 or 1 | exact |
| `recovery_tier` | integer | none | 0, 1, 2 or 3 | exact |
| `availability_rank` | integer | none | 1-based dense rank within the obligor's period cohort | exact |
| `loss_reserve` | number | currency | at least 0 | two decimal places |

The filed `availability_rank` must be an integer from 1 through the cohort size.

`dilution_reserve` is the desk's expected dilution (credit notes, returns, pricing adjustments and discounts) on the obligor's open purchased balance at the snapshot, in currency.

`collection_profile` describes when the open balance is collected, as mass over eight consecutive day bands in order: 0 to 15, 16 to 30, 31 to 45, 46 to 60, 61 to 90, 91 to 120, 121 to 180 and 181 to 270 days. The eight entries need not sum to 1.0. Whatever mass is left over is the share not collected within 270 days, and that share carries information in its own right.

`dispute_flag` is 1 when the desk escalates the obligor to formal dispute handling in the period and 0 otherwise.

`recovery_tier` is the desk's tier for the obligor's delinquent exposure: 0 weak, 1 below average, 2 above average, 3 strong.

`availability_rank` is a dense rank inside the obligor's own period cohort by estimated undrawn headroom under the facility, that is the estimated net availability less the balance already drawn, with 1 for the highest. Headroom can be negative. Ties take the same rank and the next rank follows immediately. The cohort of a record is the set of obligors in `queries.jsonl` with the same period.

`loss_reserve` is the desk's expected credit loss on the obligor's exposure net of credit insurance, in currency. It sits on a different scale from `dilution_reserve`.

## Ledger conventions

Every view carries two kinds of rows. A `snapshot` row is a month-end observation of one obligor. A `closed` row is a completed external case, filed in the month it entered the ledger as `booked_period`, with `event_period` giving the month the case completed. A closed row the ledger later corrected carries `restated_period`, the month of the correction, and `as_booked`, the values the ledger carried before the correction; the top-level fields hold the corrected values.

Periods are months numbered 1 to 20. Closed rows are the completed cases the desk observes; snapshot rows are what the desk observes about an obligor at the month end it reviews.

## Filing requirements

- Produce a record for every row in `queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full, not resolved to the last one seen.
- `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse. Non-finite numbers are rejected.
