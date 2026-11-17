# Desk manual: documentary credit examination

This manual states what an examination record contains, not how the desk estimates it. The desk's own records in `history/examination.jsonl` are the only reference for its actual output. This manual is not legal advice or an authoritative interpretation of ICC rules.

## Deliverables and identifiers

Write `predictions.jsonl`, `documentary_credit_examination.py` and `requirements.txt` under `/workspace`. The desk reads the filed records as submitted; it does not re-run the code. Code and dependencies are filed alongside them.
The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

Each query names one presentation-period for a beneficiary. `record_id` is `<beneficiary_id>:p<period>`. The snapshot join key is `(beneficiary_id, period)`. Closed external cases use `case_id` and must not be joined to a beneficiary by their position in a file. A snapshot's group codes come from `credit_register/<beneficiary_id>.json`; closed cases carry their own group codes.

## Record fields

| field | units | range and precision |
|---|---|---|
| `record_id` | none | exact query id |
| `discrepancy_count` | expected number of discrepancies | non-negative, two decimal places |
| `discrepancy_class_profile` | shares of discrepancies | eight non-negative floats, each no greater than 1, total at most one |
| `refusal_flag` | notice decision | integer 0 or 1 |
| `tenor_tier` | settlement tenor band | integer 0..3 |
| `examiner_priority_rank` | cohort ordering | integer 1..cohort size, dense descending urgency rank |
| `charge_reserve` | USD expected charges | non-negative, two decimal places |

The filed `examiner_priority_rank` must be an integer from 1 through the cohort size.

Class order: late presentation, inconsistent data, missing document, expired credit, short shipment, insurance defect, transport defect, other. The residual is pending definitive class coding; it is not the probability of a compliant presentation. Each closed `class_counts` array contains these eight counts followed by a ninth pending-coding count. Its sum is the number of discrepancy observations in that external case sample. It is not the target presentation's count.

Tenor bands use estimated elapsed calendar days from the applicable draft/acceptance basis to settlement: tier 0 at most 45; tier 1 above 45 and at most 95; tier 2 above 95 and at most 160; tier 3 above 160. These are internal monitoring bands, not ICC categories.

The rank cohort is all queries with the same period. Reference history ranks use the reference beneficiaries with the same period. Tied estimated urgency scores receive the same rank, and the next distinct score takes the next integer. Priority is not the submitted refusal flag or discrepancy count, and there is no requirement to derive it from either.

## Documentary-credit conventions

The bank examines documents, not goods. Under UCP600-style conventions, an examination window is expressed in banking days; where an original transport document is required, the ordinary presentation window is 21 calendar days after shipment unless the credit states otherwise, and presentation cannot be later than credit expiry. An applicant waiver request is not itself a waiver accepted by the issuing bank and does not automatically extend the examination window. This dataset supplies numeric extracts rather than document images or holiday calendars: do not reinterpret a supplied banking-day measure as calendar days.

`presentation_lag_days` is calendar days from shipment to presentation. `expiry_margin_days` is calendar days from presentation to expiry; negative means expired. `notice_time_left` is remaining banking days in the examination window. `applicant_response_days` is elapsed banking days awaiting applicant response. `draft_tenor_days`, `acceptance_delay_days`, `maturity_extension_days` and `settled_tenor_days` are calendar-day measures. `bank_queue_hours` and `cutoff_margin_hours` are operational hours, while `corridor_delay_days` is calendar days. A quantity or amount tolerance must come from the credit terms; do not assume every discrepancy is excused by a blanket tolerance.

All amounts are already converted to USD; do not apply a second FX conversion. `face_amount_usd` is the presentation face amount, while `charges_usd` is incurred fees and handling charges, not credit principal loss. `charge_reserve` estimates those charges. The numeric `document_count`, `unwaived_items`, `message_count` and `amendment_count` are exposure-weighted period observations and may be fractional. All fields ending in `_share`, plus `insurance_gap`, `waiver_reliability`, `transport_complexity`, `document_complexity`, `claim_complexity`, and `cycle_phase`, are dimensionless. Cycle phase is a fraction of an operational cycle, with zero and one adjacent.

The six register group codes are categorical integers 0..3: document route, trade corridor, credit form, tenor basis, service band and charge schedule. Sector is 0..5. Bank identifiers and beneficiary identifiers are nominal labels, not numeric scores. Closed `handling_urgency` is a dimensionless operational index, where larger means more urgent; it may be negative.

## Ledger conventions

Periods are months 1..20. Each data view contains `snapshot` and `closed` rows. `event_period` is the completed external case's event month; `booked_period` is the ledger booking month. `restated_period` is the month an outcome correction was recorded. The top-level outcome is the corrected value; `as_booked` contains the original outcome. Corrections after the last query period are possible. File order has no financial meaning. Published historical examination records are not revised when a source case is restated.

## Filing requirements

Values must be within `1e-8` of two-decimal precision.

Total mass tolerance is `1e-9`.

Each entry in `discrepancy_class_profile` must be at least zero and no greater than 1, independently of the total mass tolerance.

Duplicate ids are discarded entirely.

`predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse.
