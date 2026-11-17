## Iterative Evaluation Mode

You are working with iterative test feedback. After implementing code, you can submit your work for evaluation at any time to see which tests pass and which fail, then iterate based on the results.

### How to Test Your Code

- Run `sforge-submit` to submit your current code for evaluation. It will package the files, send them to the judge server, and return results showing score, pass rate, and a summary of findings.
- Run `sforge-submit --details` to submit and see detailed per-test results.
- Run `sforge-submit --list` to view all previous submissions and their scores for this run.

You should use these regularly to check your progress and identify issues.

### Submitted Files

Only the following paths are submitted for evaluation: `predictions.jsonl`, `receivables_surveillance.py`, `requirements.txt`

**Keep these files in a compilable/runnable state at all times.** A background process periodically auto-evaluates your code — if the submitted files are broken, incomplete, or contain syntax errors at that moment, the auto-evaluation will fail. Write changes to disk promptly and ensure the submitted files always represent your current best solution.

### Strategy

- **Implement incrementally**: Complete one module/project at a time
- **Read test feedback carefully**: Failed test names often hint at what's broken
- **Iterate**: Fix failing tests based on the feedback, then submit again

### Scoring

- Your **best score** across all submissions is your final score
- You don't lose points for failed attempts — experimentation is encouraged

---

# Receivables finance portfolio surveillance

You are the surveillance analyst for a supply-chain finance desk that funds purchased receivables against a book of around 360 obligors. The desk publishes a monthly surveillance record for every obligor-period it reviews. Your job is to reproduce the desk's record for the obligor-periods listed in `queries.jsonl`.

## What you are given

Everything under `/workspace` is yours to read.

| path | contents |
|---|---|
| `register/<obligor_id>.json` | obligor master: sector, region, contract type, rating band, credit limit, cohort |
| `dilution/<period>.jsonl` | dilution view: completed invoice cohorts with realised dilution, and month-end obligor snapshots |
| `collections/<period>.jsonl` | collection view: completed cohorts with the band in which they were collected, and obligor snapshots |
| `disputes/<obligor_id>.jsonl` | dispute view: month-end obligor snapshots and, for some obligors, completed external dispute cases |
| `delinquencies/<period>.jsonl` | recovery view: resolved delinquent exposures with recovered fraction, and obligor snapshots |
| `borrowing_base/<period>.jsonl` | availability view: completed facility periods with realised availability ratio, and obligor snapshots with gross receivables, holdback and drawn balance |
| `writeoffs/<obligor_id>.jsonl` | loss view: month-end obligor snapshots and, for some obligors, resolved loss cases |
| `history/surveillance.jsonl` | the desk's own published surveillance records for reference obligors and closed periods |
| `queries.jsonl` | the obligor-periods you must produce records for |
| `manual/surveillance_manual.md` | the desk manual: schema, units, ledger conventions, tolerances and acceptance rules |
| `dataset_metadata.json` | period and bucket definitions |

`history/surveillance.jsonl` is the desk's own prior output. It is the only statement of what the desk's records look like in practice.

## What you must produce

Write three files to `/workspace`.

| file | contents |
|---|---|
| `predictions.jsonl` | one JSON object per line, one per record in `queries.jsonl` |
| `receivables_surveillance.py` | the code that produced them |
| `requirements.txt` | your dependencies, empty if you used only the standard library |

File all three. `predictions.jsonl` must be present and parseable — the desk reads it as filed and does not re-run your code.
The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record schema

One object per obligor-period in `queries.jsonl`, with exactly these seven keys.

```json
{"record_id": "OB0147:p16",
 "dilution_reserve": 48210.55,
 "collection_profile": [0.31,0.18,0.11,0.07,0.09,0.05,0.05,0.04],
 "dispute_flag": 0,
 "recovery_tier": 2,
 "availability_rank": 37,
 "loss_reserve": 2310.40}
```

| field | type | units and constraints |
|---|---|---|
| `record_id` | string | exactly `<obligor_id>:p<period>`, matching `queries.jsonl` |
| `dilution_reserve` | number | currency, at least zero, two decimal places |
| `collection_profile` | array | exactly 8 floats, each at least zero, summing to at most 1.0. The residual `1 - sum` is the share not collected within 270 days and is meaningful, so a vector that sums to less than 1.0 is a statement, not an error |
| `dispute_flag` | integer | 0 or 1 |
| `recovery_tier` | integer | 0, 1, 2 or 3 |
| `availability_rank` | integer | 1-based dense rank within the obligor's period cohort, 1 is highest estimated undrawn headroom |
| `loss_reserve` | number | currency, at least zero, two decimal places, on a different scale from `dilution_reserve` |

The filed `availability_rank` must be an integer from 1 through the cohort size.

## How the desk reviews a record

All six fields carry equal importance and are reviewed independently. A problem in one does not invalidate the others.

## Acceptance rules

- Produce a record for every row in `queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full. Submit each record once.
- `collection_profile` must have exactly 8 entries, each at least zero, summing to at most 1.0.
- `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse.

Every field is derivable from the records under `/workspace`.
