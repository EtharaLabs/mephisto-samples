## Iterative Evaluation Mode

You are working with iterative test feedback. After implementing code, you can submit your work for evaluation at any time to see which tests pass and which fail, then iterate based on the results.

### How to Test Your Code

- Run `sforge-submit` to submit your current code for evaluation. It will package the files, send them to the judge server, and return results showing score, pass rate, and a summary of findings.
- Run `sforge-submit --details` to submit and see detailed per-test results.
- Run `sforge-submit --list` to view all previous submissions and their scores for this run.

You should use these regularly to check your progress and identify issues.

### Submitted Files

Only the following paths are submitted for evaluation: `predictions.jsonl`, `fund_nav_oversight.py`, `requirements.txt`

**Keep these files in a compilable/runnable state at all times.** A background process periodically auto-evaluates your code — if the submitted files are broken, incomplete, or contain syntax errors at that moment, the auto-evaluation will fail. Write changes to disk promptly and ensure the submitted files always represent your current best solution.

### Strategy

- **Implement incrementally**: Complete one module/project at a time
- **Read test feedback carefully**: Failed test names often hint at what's broken
- **Iterate**: Fix failing tests based on the feedback, then submit again

### Scoring

- Your **best score** across all submissions is your final score
- You don't lose points for failed attempts — experimentation is encouraged

---

# Fund administration NAV oversight

You are the NAV oversight analyst for a fund administrator reviewing daily and monthly net asset value production across a book of around 360 funds and their share classes. The desk publishes an oversight record at each monthly review cut. Reproduce the desk's record for the fund-periods listed in `queries.jsonl`.

## What you are given

Everything under `/workspace` is yours to read.

| path | contents |
|---|---|
| `register/<fund_id>.json` | fund and share-class register: domicile, strategy, currencies, production cycle and cohort |
| `positions/<period>.jsonl` | position reconciliation and FX-break snapshots; completed NAV reconciliation cases |
| `accruals/<period>.jsonl` | fee accrual snapshots and completed component allocations |
| `corporate_actions/<period>.jsonl` | corporate action processing snapshots and completed NAV reissue decisions |
| `prices/<period>.jsonl` | dominant-source snapshots aggregating multiple pricing feeds; completed reliability reviews |
| `flows/<period>.jsonl` | subscription/redemption and settlement snapshots; completed oversight work logs |
| `expenses/<period>.jsonl` | expense budgets, invoice-control snapshots and closed invoice overrun cases |
| `history/oversight.jsonl` | the desk's own published oversight records for reference funds and closed periods |
| `queries.jsonl` | the fund-periods you must produce records for |
| `manual/oversight_manual.md` | schema, units, NAV conventions, tolerances and acceptance rules |
| `dataset_metadata.json` | period, component and source-tier definitions |

`history/oversight.jsonl` is the desk's own prior output. It is the only statement of what the desk's records look like in practice.

## What you must produce

Write three files to `/workspace`.

| file | contents |
|---|---|
| `predictions.jsonl` | one JSON object per line, one per record in `queries.jsonl` |
| `fund_nav_oversight.py` | the code that produced them |
| `requirements.txt` | your dependencies, empty if you used only the standard library |

File all three. `predictions.jsonl` must be present and parseable — the desk reads it as filed and does not re-run your code.
The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record schema

One object per fund-period in `queries.jsonl`, with exactly these seven keys. The schema below specifies types, not an illustrative output distribution; consult the desk's history for actual records.

| field | type | units and constraints |
|---|---|---|
| `record_id` | string | exactly `<fund_id>:p<period>`, matching `queries.jsonl` |
| `nav_break_magnitude` | number | expected absolute NAV break, basis points, at least zero, two decimal places |
| `fee_accrual_profile` | array | exactly 8 non-negative floats, summing to at most 1.0; ordered management, performance, admin, custody, audit, transfer agency, regulatory, other. Residual mass is unallocated accrual pending invoice allocation, not rounding error |
| `restatement_flag` | integer | 0 or 1, whether the desk calls for NAV reissue |
| `pricing_source_tier` | integer | 0, 1, 2 or 3, dominant pricing source reliability from lowest to highest |
| `oversight_rank` | integer | 1-based dense rank within the fund's period cohort; 1 is highest estimated oversight workload |
| `expense_reserve` | number | expected expense overrun reserve net of waivers, USD, at least zero, two decimal places; a different scale from NAV basis points |

The filed `oversight_rank` must be an integer from 1 through the cohort size.

## How the desk reviews a record

All six fields carry equal importance and are reviewed independently. A problem in one does not invalidate the others.

## Acceptance rules

- Produce a record for every row in `queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full. Submit each record once.
- Non-finite values are invalid.
- `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse.
- Numeric currency/basis-point values must have at most two decimal places. JSON integers are accepted for integral magnitudes. Boolean values are not numbers for this schema.

Every field is derivable from the records under `/workspace`.
