# Claims methods laboratory: five independently scored problems

Recover five fixed deterministic insurance methods from observable claims data
and aggregate scoring feedback. This is **method imitation**, not prediction of
unknowable future realizations. Every target is a deterministic function of the
public panel; the private reference achieves 100/100. Exact estimation choices
are withheld. Observations alone do not uniquely identify those choices; judge
feedback is part of the task. There are no identifier hashes or random target salts.

You have 12 hours in a single turn. Write your artifacts, run your script locally,
then invoke `sforge-submit`; obey cooldowns. Best score is kept. Feedback gives
each lane's metric, coverage and points, not individual answers. You can improve
one problem without solving any other. There is no cross-lane consistency veto.

## Observable panel

Read `/workspace/data/train.jsonl` and `/workspace/data/queries.jsonl`.
Training has 25,000 rows: 100 cohorts in five lines, 25 completed accident periods
per cohort and ten development quarters per record. Group by `record_id`.
Queries have 5,000 objects `{"record_id":"...","history":[...]}`, with two to six
ordered observed quarters (20,000 history rows). The full horizon ends at lag ten.
Training realizations precede all query accident periods. Queries are independent
rolling valuations, not a common diagonal. Pooling observable query information
is allowed; calendar extrapolations use only indices at or before each cutoff.

| Fields | Meaning |
|---|---|
| `record_id`, `lob`, `cohort` | Record, line, cohort identifiers; not encoded answers |
| `accident_period`, `development_lag`, `calendar_period` | Integer quarters; calendar = accident + lag |
| `exposure`, `risk_index` | Exposure and underwriting proxy |
| `inflation_index` | Observed claims cost index |
| `primary_paid`, `settlement_paid`, `reopening_paid` | Incremental payments by type |
| `paid` | Cumulative total payments |
| `case_reserve`, `incurred` | Booked outstanding reserve; incurred = paid + case |
| `reported_count`, `new_reported_count`, `reopened_count` | Cumulative reports, incremental reports, cumulative reopenings |

No inputs are null. Amounts are synthetic currency. Booked reserves are estimates,
not answers. Individual claim sizes and large-loss labels are NOT observed.

## Five output fields, five different estimators

1. **Primary ultimate severity — `ultimate_severity`.** A credibility estimate of
   average primary claim size after full development, in deflated currency per
   reported claim. This is NOT total ultimate loss or remaining reserve dollars.
   The model family is credibility-based severity estimation. Predict the
   method's estimate, not a realized individual claim size.
2. **Reporting timing — `reporting_pattern`.** Ten probabilities for the entire
   reporting-lag distribution, lags 1–10, INCLUDING observed lags. It describes
   when claims report, not how much they cost. The model family is a conditional
   reporting-lag distribution. The target covers the entire development horizon,
   rather than only reports already observed.
3. **Elevated reopening incidence — `reopening_flag`.** Boolean: is the estimated
   per-report reopening event propensity in the top quintile of accident-period
   × line peers? Fit a delayed binomial event model to report counts and increments
   of cumulative reopenings, then update with observed eligible reports. It is a
   classification of elevated occurrence propensity, NOT whether at least one
   random future event actually occurs, and NOT a share of reopening dollars.
4. **Future payment timing — `cash_pattern`.** Ten probabilities allocating the
   remaining cash across development lags 1–10. Entries at/before cutoff must be
   zero. The target is a conditional future-payment distribution in nominal
   currency, including primary, settlement and reopening payments. This is a
   schedule, not the reporting curve or a reserve amount.
5. **Large-loss signal — `large_loss_score`.** Rank of aggregate excess-loss-cell
   incidence within accident-period × line peers. A cell is a cohort-period-lag
   observation with at least one new report. The model family is standardized
   aggregate primary-loss upper-tail incidence estimation. This is a
   tail-contamination PROXY, not a reconstructed individual large-loss label.
   Predict peer-relative incidence of unusually large aggregate primary losses,
   not average claim size or post-lag-six payments.

Peer percentiles are `(number below + 0.5 × number tied)/peer count`. Top quintile
means percentile >=0.8. Large-loss scores should express this peer-relative
ordering; any globally order-preserving transformation is accepted. Method
construction, fitting choices and hyperparameters remain private. The quantities,
output requirements and scoring rules are public. All methods use only public inputs.

## Submission

Write `/workspace/reserving.py`, `/workspace/requirements.txt` (empty for stdlib),
and `/workspace/reserving_results.json`. Put a runnable CLI in a source comment.
Run your script yourself. The judge reads static JSON and **never executes the
submitted script**. No packages are installed on submission; both images have no
network. Example shape, for a query observed through lag two:

```json
{
  "predictions": [{
    "record_id": "<query record_id>",
    "ultimate_severity": 1800.0,
    "reporting_pattern": [0.25,0.25,0.2,0.15,0.1,0.05,0,0,0,0],
    "reopening_flag": false,
    "cash_pattern": [0,0,0.2,0.2,0.2,0.15,0.1,0.05,0.05,0.05],
    "large_loss_score": 0.65
  }],
  "self_reported_metrics": {"record_count": 1}
}
```

`self_reported_metrics` is informational and ignored by grading. The former
accounting award has been removed rather than allocating points for easy invariant
sums. It cannot veto, add or subtract any points. There is no stability aggregate.

## Scoring: exactly 100 points, five lanes capped at 20

| Lane | Field | Weight | Metric | Baseline floor method | Full |
|---|---|---:|---|---|---:|
| severity | ultimate_severity | 20 | Relative-error agreement | chain_ladder | 1 |
| report_timing | reporting_pattern | 20 | Distribution overlap | chain_ladder | 1 |
| reopening | reopening_flag | 20 | F1 | All-positive classification (1/3) | 1 |
| cash_timing | cash_pattern | 20 | Distribution overlap | chain_ladder | 1 |
| large_loss | large_loss_score | 20 | Spearman correlation | copy_forward | 1 |

This version uses a **new, stricter baseline-relative bar**. Each lane rescales credit against the named baseline method's performance: `credit = clip((metric-floor)/(1-floor),0,1)`. Matching or underperforming that baseline earns **zero on that lane**; metric 1 earns full credit before any coverage multiplier. The four textbook-method floors are fixed measured calibration values, withheld rather than per-record answers. Reopening retains its all-positive F1 floor of 1/3. Chain-ladder and copy-forward are legitimate reference methods, unlike that degenerate classification guess. This is a change from raw agreement credit, not a correction to previously unearned credit.

Each lane reads ONLY its own field and its own private target. No scored field is
computed from another submitted field. Missing one field does not invalidate the
other four. Shared record IDs and file/JSON transport validity are the only common
requirements. Weights, raw metrics and baseline floors are fixed for this version.

* Severity: per-row `e=min(1,abs(pred-target)/max(target,1))`. Missing/invalid values
  have e=1. Metric `(1-mean(e))/(1+sqrt(mean(e²)))`. Points = 20 × credit.
* Distributions: ten finite nonnegative entries, each <=1, total mass <=1+1e-6.
  Full predictions should sum to one. Partial mass is allowed and penalized.
  Row quality is `clip(1-0.5*(sum(abs(p[j]-t[j]))+abs(sum(p)-sum(t))),0,1)`.
  This is overlap with an additional unallocated-mass category. Zero vectors,
  invalid vectors and missing rows earn zero. Cash mass at/before the private
  observed cutoff makes that cash vector invalid, not other fields. Lane quality
  is mean row quality over ALL queries. Use this quality as the metric in the baseline rescale. Points = 20 × credit. Severity and distribution metrics already penalize missing rows; no additional coverage multiplication applies.
* Reopening: F1 = `2TP/(2TP+FP+FN)`, zero if denominator is zero. Missing positives
  count as false negatives. Points = `20*clip((F1-1/3)/(1-1/3),0,1)*valid coverage`.
  The target has 20% positives; all-positive and all-negative controls earn zero.
* Large loss: Spearman uses average ranks for ties. Constant vectors earn zero.
  Points = `20*clip((correlation-floor)/(1-floor),0,1)*valid coverage`.

Numeric magnitudes must be <=1e100; booleans are not numbers. Severity must be
nonnegative; ranking scores may be signed. Flags must be JSON booleans. Unknown
IDs and extra fields are ignored. Duplicate IDs invalidate that record. Malformed
JSON, missing any of the three files or symlinked submissions yield zero. JSON
limit: 20,000,000 bytes. The judge returns a bare 0–100 total and lane diagnostics.

## Iteration

Historical pseudo-valuations test model plausibility but are not labeled examples
of the private methods. Isolate each estimator while using judge feedback to
distinguish specifications. Independent scoring removes repair-order penalties;
it does not guarantee unique inverse identification or a particular learning time.
