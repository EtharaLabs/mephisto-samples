# Five independent claims methods (PRIVATE)

The seed and record split are unchanged. The settlement-only workload scenario
in `process.py` and `grounding.yaml` changes payment timing within cohorts.
Generator future realizations/latent parameters are discarded, never used as targets.
All current truths are produced solely
from the two observable datasets by self-contained `reserving_reference.py`.

## Settlement hardening and protected lanes

Exposure at or below 1.1 uses a one-quarter settlement delay; exposure above 1.1
uses four quarters. Deferred settlement amounts are three times the original
cohort fraction. This models a small-versus-large workload service regime and
makes substantial cash mass move between the existing ten observable quarters.
It is a synthetic stress scenario, not a calibrated claim about insurance markets.
The original two-quarter setting remains the fallback for reproducing the old
configuration. Booked outstanding settlement reserves use the actual record delay
and amount scale. No additional random draws are consumed.

Every report count, primary payment, reopening count and reopening payment is
identical to the pre-edit panel. All four noncash targets are identical as well.
The reference estimators and canonical controls remain byte-identical. Anchors were unchanged during settlement hardening but subsequently changed under the new baseline-relative scoring version documented in `NOTES.md`.
The scorer has one numerical correction: zero-mass vectors return exactly zero,
not floating-point phantom credit when a target sums just below one. Positive-mass
scoring is unchanged. `hardening_study.py` checks the exact permitted source delta
against the captured
pre-edit evidence and measures exposure-conditioned public-only cash controls.

Large-loss targets are NOT unseen rare-event realizations: the deterministic
public-input method below attains Spearman 1.0 before and after hardening.
The recorded agent's 0.890345 plateau is therefore not an irreducible target-noise
ceiling. Neither contamination frequency nor this target or metric was changed.
Severity and reporting remain shorter secondary problems: their original pilot
improvements were real but closed in roughly eight submissions, not hours.
Removing their recipe leaks does not establish durable difficulty.

## Reference estimators

1. **Severity**: cohort and line robust location of deflated primary payment per
   new report, using median-centered winsorization at 2.5 times max(MAD, 10% median,
   1e-9). Blend cohort with line using 180 report credibility. Update observed
   primary loss/count with 80 pseudo-reports at the prior size. The output is
   expected ultimate average PRIMARY claim size, not total ultimate dollars.
   It does not require a fitted frequency curve or future cash schedule.
2. **Report timing**: cohort counts by lag with 120 pseudo-reports from the line
   lag distribution. Fit exponential tilt over the entire curve by minimizing
   the observed-prefix conditional multinomial negative log likelihood plus
   12 × tilt². Forty-eight ternary-search iterations on [-1.5,1.5]. Output ten
   lag probabilities, including observed lags. No monetary fields are used.
3. **Reopening**: for each cohort compare delays 1–5 using binomial event-count
   likelihood, including combinations and a penalty for impossible counts or
   events preceding the candidate delay. Fit event probability as total event
   increments / eligible initial reports. Update with query event count and
   eligible reports, using 40 pseudo-eligible reports. Classify top-quintile
   posterior hazard within period × line. This is an incidence propensity
   classification, not a future event realization or reopening dollar share.
4. **Cash timing**: normalize deflated observed payment increments across each
   prefix. Find eight nearest completed histories in the same cohort by squared
   prefix-shape distance. Average their normalized remaining-cash vectors with
   weights 1/(0.02+distance). Reinflate by recent four-position median annual
   index log-growth and seasonal phase; normalize the future schedule. This
   empirical conditional-distribution estimator does NOT call the severity,
   report-count or reopening estimator. Prefix distance ties use historical IDs
   for deterministic ordering only, never hashes or encoded target values.
5. **Large loss**: line median cell severity centers deflated primary loss;
   divide the excess over count × center by sqrt(count). Learn the empirical
   upper-decile residual threshold among nonempty training cells. Estimate
   cohort exceedance probability with a Beta(2,18) prior, then query probability
   with eight pseudo-cells at that cohort probability. Rank within period × line.
   This deliberately targets an observable aggregate tail proxy. The panel does
   NOT support identifying individual contaminated claims. Its simulator has a
   common contamination probability; no claim of hidden cohort-specific true
   contamination rates is made. Finite-sample aggregate tail behavior is the
   method-imitation target, not an asserted causal risk trait.

Shared helpers only normalize arrays, group records, and compute ranks. No
estimator consumes another estimator's output or fitted parameters. Severity and
tail use some of the same raw amounts, but estimate location versus exceedance
incidence; neither artifact determines the other. Report and cash curves use
different observations and different estimators. Scalar reserve total cannot
determine a payment vector, and report probabilities cannot determine payments.

## Scorer independence and accounting decision

Each of five lanes is 20 points and reads one distinct field. Global stability
was removed. No prediction is transformed into another scored output by the
scorer. Self-report points were removed under the operator's allowed alternative:
truthful sums were invariant under every model ablation, so they did not measure
modeling work. Testing deliberately false sums would only demonstrate bookkeeping
responsiveness, not create an additional modeling problem. The informational
`self_reported_metrics` object remains in submissions and is ignored by scoring.
There is no consistency veto. Transport/schema failures and duplicate IDs retain
their ordinary record/file-level meaning, not a model-field mismatch veto.

## Controls and scope

Old cash-flow controls are retained; `public_reference.prediction` merely exports
their previously internal cash schedule. Four genuinely new outputs require new
baseline estimators in `baselines/adapt.py`. Copy-forward uses observed severity,
observed report shares, observed reopening incidence and observed tail counts;
its zero future cash schedule honestly expresses its no-future-payments rule.
Chain ladder combines its original volume-weighted paid factors with line size,
line count timing, line reopening incidence and cohort tail counts. The competent
control uses cohort/line arithmetic severity credibility, cohort reporting curves,
eligible-count reopening updates and historical/query tail incidence. It preserves
the prior skilled cash-flow solver. None imports the private reference, reads
targets, omits fields intentionally or is tuned to a desired total score.

The original scoring anchors and five equal weights were set before the first measurement. The four competent-reference floors were selected after the recorded Opus pilot; they define a stricter scoring version, not a prospective difficulty measurement. See `NOTES.md` and `measurements/anchors.json`. The preceding zero-mass-only scorer description is historical to settlement hardening; current scoring also rescales severity, distribution and rank credit.
Current outputs are in `measurements/summary.json` and `rung_study.json`. Archived
sources/reports prefixed `previous_` or `PREVIOUS_` are historical rejected designs,
not inputs to current regeneration. Their old source digests describe that old
snapshot, not the new code. Local verification is not container or harness proof.
