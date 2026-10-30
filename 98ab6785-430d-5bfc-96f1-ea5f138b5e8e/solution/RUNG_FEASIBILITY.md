# Cross-sub-problem independence study

This replaces the rejected fifteen-knobs study. Historical findings are preserved
in `PREVIOUS_RUNG_FEASIBILITY.md`, `measurements/previous_rung_study.json` and the
archived reference/study source. No prior rejection has been reclassified as a pass.

Five estimator families and five distinct output artifacts replace the shared
reserve projection. See `TRUTH.md` for exact private methods and `instruction.md`
for the public task. Five equal 20-point lanes remove cross-output stability and
inert self-report weight. No individual lane controls another's reward.

## Measurement

`rung_study.py` evaluates all 32 combinations of naive/reference fields, first from
copy-forward, then independently from the competent public-data control. For each
of five sub-problems it reports naive-to-reference gain with all others naive,
the gain with all others reference, discrepancy, minimum/maximum gain over every
context, and the maximum off-target lane change. It checks all 80 directed edges
and all 120 repair orders per control. It also reconciles every combination with
the sum of its individual cold gains. Tolerance is 1e-10 points for roundoff only.

These are synthetic perfect-method substitution experiments, NOT agent-discovered
repairs. Additivity is a designed scorer property, not evidence of search speed.
The reason to also inspect estimator source is that additive lanes alone could
still grade five transforms of the same reserve. Here the actual methods estimate
claim size, report-count timing, event propensity, payment timing and excess-cell
incidence separately. Neither code path nor artifact dependency forces a shared
repair. Genuine domain correlations remain; statistical independence of insurance
data is neither expected nor claimed.

The acceptance predicates require unique fields, weights totaling 100 with no
lane above 20, equal cold/warm gains, zero off-target changes, additive factorial
totals, positive measurable headroom in every family for both controls, monotone
diagnostic repair orders, exact oracle 100, exact empty 0, every non-reference control below public_reference below oracle, all floors strictly below one, and both textbook controls below 1 point of 100. Strict five-point ordering is recorded but is not a qualification predicate under the new baseline-relative scoring version: matching a competent anchor intentionally earns zero. See `NOTES.md` for the post-hoc policy change and its limits.
The >0.01-point headroom check is a detectability check, not a difficulty quota.
There is no demanded uninformed total or per-knob point cap. `selftest.py` asserts
these predicates and exits nonzero on any failure. It also explicitly tests that
a falsified independence predicate raises, rather than silently reporting success.

## Evidence boundaries and honest verdict

Current numerical results and acceptance status are generated, not manually
maintained: `measurements/rung_study.json`, `summary.json`, and verbatim `selftest.txt`.
Passing establishes available independent progress in any repair order; it does
not establish that an agent will find those repairs, improve on five different
schedules, or remain productively occupied for hours. The panel still has only
100 cohorts and 25 complete historical periods. Settlement timing now depends
on record exposure, while reporting support and the contamination mechanism
remain stable. There are still few plausible model families.
Standard methods can already solve substantial parts. Aggregate feedback may
not identify exact private coefficients. Those search-depth/identifiability limits,
not cross-lane entanglement, remain the binding uncertainty for a 12-hour run.

Do not call this long-horizon-qualified. An isolated pilot with per-lane trajectories
is needed to distinguish early saturation from durable staggered progress. No
Docker, sforge, new agent trajectory or container-isolation test was run here.
The existing Opus pilot is negative duration evidence: cash and tail saturated
on its first scored submission. Recipe removal plus measured cash heterogeneity
does not erase that finding. `measurements/frozen_replay.json` replays the original
first checkpoint on the new panel, not a new attempt under the opaque spec.
