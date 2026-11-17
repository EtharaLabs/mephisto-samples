# Trade finance documentary credit examination

You are the examination analyst for a bank's documentary credit desk, reviewing presentations under letters of credit for a book of around 360 beneficiaries. The desk publishes an examination record for every beneficiary-presentation period it reviews. Your job is to reproduce the desk's record for the presentation-periods listed in `queries.jsonl`.

## What you are given

Everything under `/workspace` is yours to read.

| path | contents |
|---|---|
| `credit_register/<beneficiary_id>.json` | beneficiary and credit master: issuing bank, sector, currency, limit, document route, corridor, credit form, tenor basis, service band, charge schedule and cohort |
| `presentation_documents/<period>.jsonl` | document examination observations and completed cases with observed discrepancy counts |
| `discrepancy_logs/<period>.jsonl` | class-mix observations and closed cases with counts by discrepancy class, including pending coding |
| `refusal_notices/<period>.jsonl` | waiver and notice observations, and completed cases with refusal decisions |
| `amendment_histories/<period>.jsonl` | draft tenor, amendment and extension observations, and completed cases with settlement tenor |
| `correspondent_banks/<period>.jsonl` | correspondent queues, cutoffs and handling observations, and completed handling cases |
| `settlement_payments/<period>.jsonl` | payment and fee observations, and completed cases with charges incurred |
| `history/examination.jsonl` | the desk's own published examination records for reference beneficiaries and closed periods |
| `queries.jsonl` | the presentation-periods you must produce records for |
| `manual/examination_manual.md` | schema, units, documentary-credit conventions, tolerances and acceptance rules |
| `dataset_metadata.json` | period, class and tenor-band definitions |

`history/examination.jsonl` is the desk's own prior output. It is the only statement of what the desk's records look like in practice.

## What you must produce

Write three files to `/workspace`.

| file | contents |
|---|---|
| `predictions.jsonl` | one JSON object per line, one per record in `queries.jsonl` |
| `documentary_credit_examination.py` | the code that produced them |
| `requirements.txt` | your dependencies, empty if you used only the standard library |

File all three. `predictions.jsonl` must be present and parseable — the desk reads it as filed and does not re-run your code.
The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record schema

One object per presentation-period in `queries.jsonl`, with exactly these seven keys. Match `record_id` to the query; see the desk's history for actual examples.

| field | type | units and constraints |
|---|---|---|
| `record_id` | string | exactly `<beneficiary_id>:p<period>`, matching `queries.jsonl` |
| `discrepancy_count` | number | expected discrepancy count, at least zero, two decimal places; not necessarily an integer |
| `discrepancy_class_profile` | array | exactly 8 floats, each at least zero and no greater than 1, summing to at most 1.0. The residual is the share of discrepancies awaiting definitive class coding and is meaningful |
| `refusal_flag` | integer | 0 or 1, whether the desk issues a refusal notice |
| `tenor_tier` | integer | 0, 1, 2 or 3, increasing settlement tenor |
| `examiner_priority_rank` | integer | 1-based dense rank within the presentation's period cohort; 1 is highest estimated handling urgency |
| `charge_reserve` | number | expected USD charges, at least zero, two decimal places, on a different scale from `discrepancy_count` |

The filed `examiner_priority_rank` must be an integer from 1 through the cohort size.

The eight discrepancy classes, in order, are late presentation, inconsistent data, missing document, expired credit, short shipment, insurance defect, transport defect and other. “Other” means classified but outside the named categories, not pending classification.

## How the desk reviews a record

All six fields carry equal importance and are reviewed independently. A problem in one does not invalidate the others.

## Acceptance rules

- Produce a record for every row in `queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full. Submit each record once.
- Mass tolerance is `1e-9`.
- Flags, tiers and ranks must be JSON integers, not booleans or fractional numbers. Numeric magnitude precision tolerance is `1e-8` around two-decimal values; JSON need not retain trailing zeros.
- `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse.

Every field is derivable from the records under `/workspace`.
