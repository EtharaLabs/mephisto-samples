# Desk manual: dealer floorplan finance portfolio surveillance

This manual states what a surveillance record must contain and how it is accepted. It does not state how to arrive at the values. The desk's own published records in `history/surveillance.jsonl` are the reference for what its output looks like in practice.

## Deliverables

Three files in `/workspace`.

| file | contents |
|---|---|
| `predictions.jsonl` | one surveillance record per line, one per entry in `queries.jsonl` |
| `floorplan_surveillance.py` | the code that produced the records |
| `requirements.txt` | dependencies, empty if only the standard library was used |

File all three. `predictions.jsonl` must be present and parseable. The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record fields

| field | type | units | range | precision |
|---|---|---|---|---|
| `record_id` | string | none | exactly `<dealer_id>:p<period>` | exact match required |
| `aging_reserve` | number | currency | at least 0 | two decimal places |
| `turn_profile` | array of 8 floats | mass | each at least 0, total at most 1.0 | eight decimal places |
| `sot_flag` | integer | none | 0 or 1 | exact |
| `variance_tier` | integer | none | 0, 1, 2 or 3 | exact |
| `headroom_rank` | integer | none | 1-based dense rank within the dealer's period cohort | exact |
| `loss_reserve` | number | currency | at least 0 | two decimal places |

The filed `headroom_rank` must be an integer from 1 through the cohort size.

`aging_reserve` is the desk's expected write-down on the aged share of the dealer's floored inventory balance at the snapshot, in currency. The aged share is the part of the floored balance that has been on the floor beyond the programme's aging line; the write-down is what the desk expects to lose on that part through forced liquidation, curtailment shortfalls and value decline.

`turn_profile` describes when the units on the floor at the snapshot sell, as mass over eight consecutive day bands in order: 0 to 30, 31 to 60, 61 to 90, 91 to 120, 121 to 150, 151 to 180, 181 to 240 and 241 to 365 days. The eight entries need not sum to 1.0. Whatever mass is left over is the share not sold within 365 days, and that share carries information in its own right.

`sot_flag` is 1 when the desk flags the dealer for a sold-out-of-trust audit visit in the period and 0 otherwise. A unit is sold out of trust when the dealer has sold it and not remitted the payoff within the programme's grace period.

`variance_tier` is the desk's severity tier for the unit-count variance it expects the next physical audit to find: 0 clean, 1 minor, 2 material, 3 severe. The desk's severity bands on a realised variance fraction are: clean at most 0.02, minor above 0.02 up to 0.05, material above 0.05 up to 0.10, severe above 0.10.

`headroom_rank` is a dense rank inside the dealer's own period cohort by estimated undrawn line headroom, that is the estimated available line less the outstanding balance and the payoffs already pending, with 1 for the highest. Headroom can be negative. Ties take the same rank and the next rank follows immediately. The cohort of a record is the set of dealers in `queries.jsonl` with the same period.

`loss_reserve` is the desk's expected credit loss on the dealer's exposure after the collateral the programme holds, in currency. It sits on a different scale from `aging_reserve`.

## Ledger conventions

Every view carries two kinds of rows. A `snapshot` row is a month-end observation of one dealer. A `closed` row is a completed case, filed in the month it entered the ledger as `booked_period`, with `event_period` giving the month the case completed. A closed row the ledger later corrected carries `restated_period`, the month of the correction, and `as_booked`, the values the ledger carried before the correction; the top-level fields hold the corrected values.

The desk reads the ledger as it stood at the period under review. A record at period q draws only on closed rows whose `booked_period` is strictly before q, and it takes each of those rows at the values the ledger carried at q: a row whose `restated_period` is at or after q is read at its `as_booked` values, because the correction was not yet known at q, while a row whose `restated_period` is before q is read at its corrected top-level fields.

In the `lines` view the closed rows are each dealer's own completed facility periods and carry the dealer's `dealer_id`; in every other view the closed rows are external cases identified by `case_id` only.

Periods are months numbered 1 to 20. Closed rows are the completed cases the desk observes; snapshot rows are what the desk observes about a dealer at the month end it reviews.

## Filing requirements

- Produce a record for every row in `queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full, not resolved to the last one seen.
- `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse. Non-finite numbers are rejected.
