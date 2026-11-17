# Fund administration NAV oversight (PRIVATE)

Private design record. Never copy `solution/` or `tests/` into the agent image. The agent image contains only the published workspace and pinned scientific dependencies. The judge image contains only the scorer and generated hidden truth, never the oracle or baseline-fitting code.

## Status and evidence limits

This is an original synthetic NAV-domain construction following the reference bundle's six-lane layout and scoring structure. It is **not** a renamed receivables ledger. The reference's source/configuration and probe code were reviewed; bulk reference data was sampled rather than exhaustively read. This limitation must not be described as exhaustive byte-level review.

The measurements below are real author-side executions of the delivered generator, independent analyst portfolio and scorer. They are not a frontier-agent trial, a measured human time estimate, or evidence of a twelve-hour trajectory. No long-run pass-rate or asymptotic claim is made. The reference's reported long-run scores are not evidence for this new bundle.

## What is graded

Six equal-weight independent lanes, purely additive, no global gate or consistency veto. The private oracle refits on each review's public ledger, then emits deterministic expectations or decisions. No realised future draw is graded. The oracle recomputes from public files without reading hidden truth. The shared `prepare` routine transports and normalises only a selected lane's own view; fitted state is never shared between lanes.

| field | quantity and estimator | metric |
|---|---|---|
| nav_break_magnitude | Expected absolute break in basis points; recency-weighted local linear regression of log-one-plus reconciled breaks | Relative agreement with 1bp materiality |
| fee_accrual_profile | Kernel-pooled, segment-shrunk nine-category accrual composition; emit eight components and preserve unallocated residual | Distribution overlap including residual |
| restatement_flag | Interaction logistic fit, threshold chosen by recency-weighted completed-case prevalence | Positive-class F1 |
| pricing_source_tier | Shrunk local reliability estimate, mapped into fixed ordered reliability bands | Unweighted macro F1 across truth-present tiers |
| oversight_rank | Nonlinear ridge review workload plus robust residual kernel; descending dense ranks within registered review cohort | Within-ten-place share, equally averaged across graded period cohorts (one query cohort per period) |
| expense_reserve | Two-part kernel probability and empirical-Bayes log severity, scaled by public budget net of waivers | Relative agreement with 100 USD materiality |

The public schemas and units do not describe output frequencies or typical values. Only the desk's history does. The private design record can discuss scoring measurements without leaking them into the workspace.

## Ledger discipline and domain modelling

Eight substantive input trees: register, positions, accruals, corporate_actions, prices, flows, expenses, history; plus manual, metadata and queries. Cases are independent of the funds whose review snapshots are graded. Position and pricing files are production-system summaries, not security-level trade tapes; source coverage and dispersion aggregate multiple price feeds. The register contains share classes, base currency and daily/monthly production cycle. Monthly cuts standardise review timing while preserving those production-cycle labels.

Closed cases must be booked strictly before the cut. A correction at or after that cut is replaced with `as_booked`; earlier corrections are known. The case-generating process has a late-period regime shift, while the public history precedes it. The oracle's recency weighting tracks the evolving ledger without relying on future labels. Randomness occurs only during construction of published cases and snapshots. Every truth record is a function of those files.

## Generated scale and reproducibility

Observed generator report: **360 funds, 20 periods, 240 history records, 560 graded records**. The query cohorts are the non-reference funds at the two query cuts. `solution/measure.py regenerate` executed the generator twice and compared SHA-256 hashes of every public and hidden data file, including path-set equality. Observed result: **485 files, zero differences**. The complete digest map is in `measurements/nonregression.json`.

Reproduction uses the pinned packages in `environment/requirements.txt`, Python 3.12 and single-threaded BLAS/OpenMP. Cross-platform floating-point byte identity has not been measured; same-environment deterministic regeneration has. The fixed public stream key is in metadata and generator source; no private random draw feeds a graded value.

## Floors

Every lane floor is the actual maximum raw agreement from the frozen one-shot portfolio (ridge and random forest on corrected closed cases), public-history constants, classification constants, simplex point masses, uniform mass, identity/reverse ranks, and a private magnitude/rank constant-grid safety envelope. The two competent methods deliberately use eventual corrections available in the public workspace, making them ledger-naive hindsight controls rather than strictly point-in-time controls, just as in the reference's closed-case tier. No high-performing competent method is excluded; no floor is chosen to force a target aggregate. The two floor-setting methods themselves score zero after flooring.

The constant-grid envelope is not claimed to be an exact global optimum over the simplex or all real-valued constants. This is a deliberate difference from the reference's more exhaustive degenerate envelope. Every tested degenerate control is bound into `floors.json`.

| lane | measured floor | winning floor setter |
|---|---:|---|
| nav_break_magnitude | 0.7658886126114046 | ridge_closed |
| fee_accrual_profile | 0.9513717315535715 | ridge_closed |
| restatement_flag | 0.9314586994727593 | ridge_closed |
| pricing_source_tier | 0.8462716774887861 | ridge_closed |
| oversight_rank | 0.3678571428571429 | rf_closed |
| expense_reserve | 0.5520540974178461 | ridge_closed |

Payable fraction is `max(0, min(1, (metric-floor)/(1-floor)))`. Full precision is retained until final aggregate rounding. Floors are absent from public instructions, manual and agent feedback. Raw metrics are withheld from public feedback because their combination with payable fractions would reveal the floors algebraically; this is not a claim of secrecy against unlimited probing. `floors.json` records source, manifest, dependency, public-input and truth hashes; `scorer_manifest.json` is the sole grading source of floor constants. Source hash freshness is checked by the final verification script, after actually remeasuring floors on final inputs rather than merely refreshing hashes.

## Observed estimator ladder

All candidates train on public case outcomes only, apart from public-history constant outputs and public-history tier proportions. No candidate imports the private oracle or reads truth. Parameters were frozen before this first ladder execution. The table is sorted by observed score, not falsely presented as a monotonically improving chronological optimisation run. Ten named methods yield eight distinct aggregate scores.

| method | distinct approach | observed score |
|---|---|---:|
| constant | public-history mean/mode-like constant outputs | 0.0000 |
| ridge_closed | one-shot standardised linear fit, corrected case values | 0.0000 |
| rf_closed | one-shot random forest, corrected case values | 0.0000 |
| rf_asof | point-in-time cases and recency-weighted forest | 0.0033 |
| hgb | per-target histogram gradient boosting | 0.0306 |
| kernel_wide | broad local kernel pooling | 0.0945 |
| extra_trees | recency-weighted extremely randomised trees | 0.0968 |
| kernel_local | narrower local kernel pooling | 0.2029 |
| local_linear | local-linear NAV fit plus local kernels | 0.2501 |
| structured | lane-specific logistic, nonlinear ridge/residual, local-linear and two-part reserve models | **0.5328** |

Full raw metrics, fractions and prediction-file hashes are in `measurements/ladder.json`; every method's actual prediction file is retained in `measurements/results/`.

### Best non-oracle method by lane

| lane | raw metric | earned fraction |
|---|---:|---:|
| nav_break_magnitude | 0.9203763221359405 | 0.6598897697705994 |
| fee_accrual_profile | 0.9770428561607143 | 0.5279053815256344 |
| restatement_flag | 0.9982964224872232 | 0.9751452409033329 |
| pricing_source_tier | 0.8414204159932234 | 0.0000000000000000 |
| oversight_rank | 0.8607142857142858 | 0.7796610169491526 |
| expense_reserve | 0.6660422972677261 | 0.2544686739912181 |

This establishes useful author-side headroom, not an intrinsic ceiling: the oracle can attain perfect agreement. The near-perfect binary lane does not rescue the failed tier lane; every lane contributes independently. Conversely the failed tier lane does not veto the useful fits elsewhere.

## Failure modes actually encountered

- System `python3` lacked NumPy (`ModuleNotFoundError`). A project-local Python 3.12 environment was created and the exact pinned packages installed. The runtime environment and package cache are authoring-only, not agent-image inputs.
- The competent ridge floor was unexpectedly strong on fees and restatement. It was retained, not clipped or excluded; broad forests and histogram boosting consequently earned little despite plausible raw predictions.
- Correcting ledger timing alone did not solve the task: the point-in-time forest earned only 0.0033. Nonlinear and lane-specific fitting mattered more than one transport correction.
- The structured tier method transferred class proportions from the earlier history instead of identifying the desk's absolute reliability cutpoints. It fell below its competent floor and earned zero in that lane. This failed modelling choice is retained in the measured ladder.
- Direct conditional-mean expense regressions miss the desk's two-part severity calculation. Even the approximate two-part model left substantial error and earned only the recorded partial fraction.
- Review of untrusted numeric handling found a possible Python integer-to-float overflow on enormous submitted integers. `numeric` now catches overflow, and adversarial tests cover it; it was identified before final scorer verification, not a measured model failure.
- Security review identified that exposing raw metrics with earned fractions would algebraically disclose floor values. The public verifier now omits raw metrics; private measurement reports retain them.
- The initial language-server pass used an environment without scientific packages and did not resolve the runtime scorer import path; it also inferred overly narrow heterogeneous dictionaries and flagged an unchecked optional import specification. A bundle-local Pyright environment/search-path configuration, explicit JSON dictionary annotations and a loader assertion address those findings.

The desk's amounts are deterministic model-based reserve estimates, not a claim of statistically unbiased arithmetic conditional means. NAV back-transforms a log fit without lognormal smearing; expense severity uses a deliberately partial variance adjustment. Those estimation conventions are part of the method-imitation task.

## Execution and evidence

From the bundle root, with `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`:

```sh
python3 -B solution/measure.py regenerate
python3 -B solution/measure_floors.py
python3 -B solution/measure.py ladder
python3 -B solution/checks/verify.py
```

`verify.py` runs the actual oracle CLI, compares its output bytes to truth, calls the separate verifier shell, tests malformed submissions and lane-only damage, checks the two alternate evaluation orders, and binds source hashes. Machine-readable final outcomes are in `measurements/verification.json` after execution. No Docker build or cross-platform run is claimed unless separately recorded.

Observed end-to-end verification: oracle **1.0000**, empty submission **0.0000**, all **8 scorer tests passed**, both alternate evaluation orders byte-identical, and **zero mismatches in every lane-isolation check**. The actual shell verifier published an oracle reward of **1.0000**. Python source syntax and floor/input/source hash binding passed. Docker image builds and cross-platform numerical reproduction remain untested.

Final language-server status is **not clean**: the second check still reports **9 missing-import diagnostics** for installed scientific packages and the dynamically added scorer path. The heterogeneous-dictionary and optional-loader diagnostics were resolved. The configured authoring interpreter successfully executed all affected imports and the full verification; the editor service did not adopt the bundle-local environment/search paths during this session. No clean-LSP claim is made. This is a remaining validation limitation, distinct from the passing runtime tests.

The bundle LICENSE is copied verbatim as requested, including its original reference-task attribution. Task identity for this bundle is established by `task.toml`, not by altering the copied license header. A production UUID remains unassigned.
