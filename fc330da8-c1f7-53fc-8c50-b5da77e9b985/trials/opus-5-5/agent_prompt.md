## Iterative Evaluation Mode

You are working with iterative test feedback. After implementing code, you can submit your work for evaluation at any time to see which tests pass and which fail, then iterate based on the results.

### How to Test Your Code

- Run `sforge-submit` to submit your current code for evaluation. It will package the files, send them to the judge server, and return results showing score, pass rate, and a summary of findings.
- Run `sforge-submit --details` to submit and see detailed per-test results.
- Run `sforge-submit --list` to view all previous submissions and their scores for this run.

You should use these regularly to check your progress and identify issues.

### Submitted Files

Only the following paths are submitted for evaluation: `predictions.jsonl`, `floorplan_surveillance.py`, `requirements.txt`

**Keep these files in a compilable/runnable state at all times.** A background process periodically auto-evaluates your code — if the submitted files are broken, incomplete, or contain syntax errors at that moment, the auto-evaluation will fail. Write changes to disk promptly and ensure the submitted files always represent your current best solution.

### Network Environment

**This environment has NO internet access.** Only the judge server and the AI API are reachable. Do not attempt to download packages, fetch remote resources, or access external URLs — all dependencies are pre-installed in the workspace.

### Strategy

- **Implement incrementally**: Complete one module/project at a time
- **Read test feedback carefully**: Failed test names often hint at what's broken
- **Iterate**: Fix failing tests based on the feedback, then submit again

### Scoring

- Your **best score** across all submissions is your final score
- You don't lose points for failed attempts — experimentation is encouraged

---

# Dealer floorplan finance portfolio surveillance

You are the surveillance analyst for a floorplan finance desk that funds the vehicle inventory of around 360 franchised dealers. The desk publishes a monthly surveillance record for every dealer-period it reviews. Your job is to reproduce the desk's record for the dealer-periods listed in `queries.jsonl`.

## What you are given

Everything under `/workspace` is yours to read.

| path | contents |
|---|---|
| `register/<dealer_id>.json` | dealer master: franchise, region, segment, rating band, audit stage, credit line, locations, cohort |
| `aging/<period>.jsonl` | aging view: liquidated aged-unit cohorts with realised haircut ratio, and month-end dealer snapshots with the floored balance and aged share |
| `turns/<period>.jsonl` | turn view: completed unit cohorts with the band in which they sold, and dealer snapshots |
| `audits/<dealer_id>.jsonl` | audit view: month-end dealer snapshots and, for some dealers, completed external audit cases with the sold-out-of-trust outcome |
| `reconciliations/<period>.jsonl` | variance view: completed physical audits with the realised unit-count variance fraction, and dealer snapshots |
| `lines/<period>.jsonl` | line view: each dealer's own completed facility periods with the realised available fraction, and dealer snapshots with credit line, outstanding and pending payoffs |
| `repossessions/<dealer_id>.jsonl` | loss view: month-end dealer snapshots and, for some dealers, resolved repossession cases with the realised loss |
| `history/surveillance.jsonl` | the desk's own published surveillance records for reference dealers and closed periods |
| `queries.jsonl` | the dealer-periods you must produce records for |
| `manual/surveillance_manual.md` | the desk manual: schema, units, ledger conventions, tolerances and acceptance rules |
| `dataset_metadata.json` | period, band and tier definitions |

`history/surveillance.jsonl` is the desk's own prior output. It is the only statement of what the desk's records look like in practice.

## What you must produce

Write three files to `/workspace`.

| file | contents |
|---|---|
| `predictions.jsonl` | one JSON object per line, one per record in `queries.jsonl` |
| `floorplan_surveillance.py` | the code that produced them |
| `requirements.txt` | your dependencies, empty if you used only the standard library |

File all three. `predictions.jsonl` must be present and parseable — the desk reads it as filed and does not re-run your code.
The task module and `requirements.txt` are collected with the submission; their absence does not by itself invalidate the filed records.

## Record schema

One object per dealer-period in `queries.jsonl`, with exactly these seven keys.

```json
{"record_id": "DL0147:p16",
 "aging_reserve": 18210.55,
 "turn_profile": [0.38,0.21,0.14,0.10,0.07,0.04,0.02,0.01],
 "sot_flag": 0,
 "variance_tier": 1,
 "headroom_rank": 37,
 "loss_reserve": 3310.40}
```

| field | type | units and constraints |
|---|---|---|
| `record_id` | string | exactly `<dealer_id>:p<period>`, matching `queries.jsonl` |
| `aging_reserve` | number | currency, at least zero, two decimal places |
| `turn_profile` | array | exactly 8 floats, each at least zero, summing to at most 1.0. The residual `1 - sum` is the share not sold within 365 days and is meaningful, so a vector that sums to less than 1.0 is a statement, not an error |
| `sot_flag` | integer | 0 or 1 |
| `variance_tier` | integer | 0, 1, 2 or 3 |
| `headroom_rank` | integer | 1-based dense rank within the dealer's period cohort, 1 is highest estimated undrawn headroom |
| `loss_reserve` | number | currency, at least zero, two decimal places, on a different scale from `aging_reserve` |

The filed `headroom_rank` must be an integer from 1 through the cohort size.

## How the desk reviews a record

All six fields carry equal importance and are reviewed independently. A problem in one does not invalidate the others.

## Acceptance rules

- Produce a record for every row in `queries.jsonl`. A missing, unparseable, out-of-range or wrong-length value does not remove that record from review.
- Duplicate `record_id` values are discarded in full. Submit each record once.
- `turn_profile` must have exactly 8 entries, each at least zero, summing to at most 1.0.
- `predictions.jsonl` must be a regular file, at most 20,000,000 bytes, and must parse.

Every field is derivable from the records under `/workspace`.
