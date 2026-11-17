# Transfer pricing intercompany settlement (PRIVATE)

Private design record. Never copy solution/ or tests/ into the agent image.

## Design and provenance

The reference bundle was studied lane-for-lane. This construction preserves its additive competence-floored scoring, point-in-time ledger problem, independent fitted methods, private oracle, and public-only candidate ladder. It does not reuse receivables outcomes or relabel their economic interpretation.

The register joins 360 directed pairs among 360 legal entities. The six operational views each supply independently generated closed cases and current observations. Register jurisdiction bands are actually used, unlike the reference decoy register. The eight input trees are register, invoices, allocation_drivers, tax_audits, comparables, settlements, tax_positions, and history. There are 1080 historical review records and 560 graded records. All output distribution examples visible to the agent reside only in history/review.jsonl.

Closed-case outcomes contain fixed-seed synthetic observation variation. No graded outcome is sampled: every graded value is a deterministic fitted functional of the published inputs. The generator fits the oracle afresh; the oracle reads no hidden truth. Full credit remains attainable in principle. Floors reduce credit for competence; they do not impose a mathematical ceiling below one.

## Six independent lanes

| Lane | Fitted desk method | Metric |
|---|---|---|
| adjustment_magnitude | weighted nonlinear-basis ridge plus local residual correction, scaled to charge base | mean/RMS relative agreement |
| allocation_key_profile | local compositional kernel shrunk toward jurisdiction centre, retaining provider residual | nine-category overlap |
| challenge_flag | ridge logistic interactions with training-prevalence threshold | positive-class F1 |
| method_tier | local expected method suitability rounded to ordered desk codes | unweighted macro F1 |
| review_rank | seasonal ridge plus local residual correction, net of paid-on-account amounts | within-ten share averaged by period |
| uncertain_tax_reserve | logistic incidence times local geometric severity times tax exposure | mean/RMS relative agreement |

The fit_lane dispatcher centralizes transport and period iteration, not shared fitted state. Every invocation creates fresh models on just one operational view plus register. predict_batch never reads another fitted lane. The isolated-lane check fits and predicts every lane with all other fitted objects absent. Method codes mean CUP, cost plus, resale minus and profit split; they are not cohort quartiles or an OECD preference hierarchy.

The ledger discipline uses only cases booked strictly before review; restatements at or after review are replaced with as_booked. Recency weighting lets the desk follow the fixed period-14 change in case levels. History is pre-change; queries are post-change. Candidate as-of handling and seasonal/interacting feature engineering are distinct measurable steps.

## Measured floors

Floors are the measured maximum of the frozen public-only constant, pair-target-encoding, history random-forest and closed-case random-forest portfolio, plus all binary/class-constant combinations. No floor was adjusted to force a desired aggregate. Candidates are generated before scoring and read only public workspace files. They share neither private estimator imports nor query labels. The denominator safeguards are fixed USD 500 and USD 50. This portfolio is not a proof over every possible degenerate numeric/vector predictor; that is a limitation relative to the reference optimized envelope.

| Lane | Raw competent floor | Source |
|---|---:|---|
| adjustment_magnitude | 0.764053170843 | closed_rf |
| allocation_key_profile | 0.941535028696 | history_rf |
| challenge_flag | 0.898395721925 | history_rf |
| method_tier | 0.550334963775 | closed_rf |
| review_rank | 0.598214285714 | closed_rf |
| uncertain_tax_reserve | 0.736179837366 | history_rf |

## Executed estimator ladder

These are fixed public-only algorithms, not artificial interpolations with truth. The engineered feature candidates are informed author-side probes; they are not independent blind-agent evidence. Rungs are listed by attained score, not asserted to improve monotonically in complexity.

| Method | Aggregate |
|---|---:|
| naive_constant | 0.0000 |
| target_encoding_alone | 0.0000 |
| history_rf | 0.0000 |
| closed_rf | 0.0000 |
| closed_extra | 0.0477 |
| hgb_plain | 0.0490 |
| hgb_asof | 0.0624 |
| closed_ridge | 0.0994 |
| local_kernel_80 | 0.1659 |
| local_kernel | 0.1893 |
| engineered_ridge | 0.3543 |
| residual_kernel | 0.5222 |

Best fitted non-oracle method: **residual_kernel**, score **0.5222**.

| Lane | Best raw metric | Best paid fraction |
|---|---:|---:|
| adjustment_magnitude | 0.902025958944 | 0.584762205086 |
| allocation_key_profile | 0.954953352625 | 0.229510485157 |
| challenge_flag | 0.975177304965 | 0.755692422546 |
| method_tier | 0.641252883607 | 0.202190325036 |
| review_rank | 0.992857142857 | 0.982222222222 |
| uncertain_tax_reserve | 0.836115218805 | 0.378801151668 |

Pure pair target encoding earns 0.0. Its allocation and method information is absorbed by the floor; it is not a paid shortcut. A literal constant-output baseline earns 0.0.

## Executed verification

Two full generator runs compared 485 generated files byte-for-byte. regeneration.diff is empty and nonregression.json records every SHA-256. Oracle score: 1.0. Oracle and reverse-order alternate both reproduce hidden truth bytes exactly. Isolated lane fits change no outputs. Scorer unit checks passed; Python source parsed without bytecode writes.

Observed method counts: `{"0": 2, "1": 310, "2": 247, "3": 1}`.
Observed currency ranges: `{"adjustment_magnitude": [52812.91, 1433385.32], "uncertain_tax_reserve": [114.4, 5167.17]}`.

floors.json binds the final generator, estimator, candidate, floor-measurement and scorer sources plus truth and manifest hashes. Source hashes are checked during verification; stale source bindings are rejected.

## Failures and limitations encountered

- The default python3 was Python 3.15, not the reference Python 3.12. Initial pinned dependency installation fell back to source and SciPy failed for lack of a Fortran compiler. That first pip attempt used OS temporary storage outside the requested output directory; no governed repository file was touched. Subsequent dependency temporary storage was explicitly confined inside the bundle.
- Reusing the existing venv with Python 3.12 retained its Python 3.15 interpreter link; the binary-only attempt still failed. A fresh .venv312 resolved this. The pinned scientific versions were retained rather than changed to hide the failure.
- The initial naive_constant implementation normalized currency by exposure and therefore was a constant-rate rule, not a literal constant answer. It was corrected and remeasured; the delivered ladder uses the literal constant-output implementation.
- Initial static diagnostics found an inferred None-only output list, an over-broad generated-row union, and unresolved local/environment imports. Explicit output typing and a separately typed booking-period local fixed the source errors. The workspace language server still resolves from the governed parent rather than the authoring venv; a bundle-local Pyright configuration is supplied for standalone checking.
- Modelling failures are retained in the ladder: plain boosted trees do not dominate simpler closed ridge; point-in-time correction alone does not rescue every lane; local smoothing helps allocation and method but loses rank accuracy; pair-only encoding yields no paid credit. No failed candidate was silently removed.
- The public informed basis includes the desk-relevant seasonal and interaction terms. Its measured quality is an author calibration result, not evidence that an unaided agent finds those terms quickly.
- Native verifier entry points are supplied without rewardkit so runtime grading requires only the standard library. test_output.py provides matching lane accessors, not rewardkit discovery decorators. Container images and cross-platform numeric identity are not claimed tested by this local run.
- Two implementation-agent launches failed before execution; work proceeded directly. Read-only source reviews were used instead of claiming unavailable specialist execution.

- Source review prompted explicit assertions for period-set agreement, prior-only history, lane-order alignment and nonempty reserve classes, plus a target-encoding fallback. Currency closed outcomes are ratios, so rescaling them is correct. A separate adversarial vector-overflow review found that summing huge finite components could abort grading; components above one are now rejected before summation.

## Evidence limits

No twelve-hour trajectory has been run for this bundle. The requested reference trajectory statistics are not transferred as evidence. The measured ladder establishes nonzero gradient and a best tested fitted method below one, not an asymptotic bound, universal difficulty, or pass-rate estimate. Test-time scores are deterministic against frozen truth and floors.

## Reproduction

```sh
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3.12 -m venv .venv312
TMPDIR="$PWD/.venv312" .venv312/bin/python -m pip install --no-cache-dir -r environment/requirements.txt
.venv312/bin/python -B solution/generate.py
.venv312/bin/python -B solution/measure_floors.py
.venv312/bin/python -B solution/measure.py
PYTHON="$PWD/.venv312/bin/python" sh solution/solve.sh environment/workspace solution/measurements/results/oracle
VERIFIER_LOG_DIR="$PWD/solution/measurements/native-verifier" sh tests/test.sh solution/measurements/results/oracle
```

LICENSE is copied verbatim as requested, including the reference task attribution line. The placeholder task name is not a sealed UUID.
