# Dealer floorplan finance portfolio surveillance (PRIVATE)

GENERATED SECTION. DO NOT HAND-EDIT. Generated from solution/generate.py and solution/estimators.py.

This file is oracle-only. It never enters the agent work image. The judge image carries the graded truth at tests/hidden/truth.jsonl and the scorer; it carries neither this file, nor the estimators, nor the floor-setting portfolio.

## What is graded

Six lanes, equal weight, purely additive, with no global gate and no consistency veto. Every graded value is the deterministic output of the private estimators in solution/estimators.py applied to the published inputs under the ledger discipline below. No realised random draw is graded anywhere, so full credit is reachable in principle and the aggregate is not bounded by outcome noise. The oracle solution/solve.sh recomputes the truth from the public workspace and never copies it.

| lane | quantity | published view it is estimated from | metric family | floor source |
|---|---|---|---|---|
| aging_reserve | expected write-down on the aged share of the floored inventory balance | aging | relative_agreement | oneshot_aging_reserve_normalised |
| turn_profile | sell-through timing over eight day bands plus unsold mass | turns | distribution_overlap | oneshot_turn_profile |
| sot_flag | sold-out-of-trust audit flag | audits | f1_detection | oneshot_closed_sot_prevalence |
| variance_tier | four-tier audit variance severity | reconciliations | macro_f1 | oneshot_closed_variance_classifier |
| headroom_rank | dense rank by estimated undrawn line headroom within the period cohort | lines | rank_agreement | oneshot_closed_headroom_rank |
| loss_reserve | expected credit loss after collateral | repossessions | relative_agreement | aged_haircut_table |

## The ledger discipline

Training rows
A record at period q is fitted on closed rows with booked_period strictly before q. Each closed row enters with the values the ledger carried at q: a row whose restated_period is at or after q enters with its as_booked values, and a row whose restatement was already known at q enters with its corrected top-level values. The manual documents the fields and never states which version the desk uses; the published history is consistent only with this point-in-time reading. A solver that fits on corrected values throughout is fitting a ledger the desk never saw.

## The structural property this construction carries

Each lane carries its own fitted estimator over its own data view. Shared code is transport only. No lane consumes another lane's estimator output and no estimator calls another; solution/measure.py verifies this by walking the estimator module's syntax tree and by a deletion ablation. The six methods are deliberately from six different families, none shared with the sibling receivables bundle: boosted regression stumps, a discrete-time complementary log-log hazard model, a distance-weighted neighbour vote with a precision-weighted threshold, proportional-odds ordinal regression, a mixed-effects line model with shrunk dealer intercepts, and hierarchical credibility with a Hill-estimated tail loading.

## Regime break

Closed-case levels shift at period 14: haircuts rise, turns slow, sold-out-of-trust events and audit variances rise, available line fractions fall and losses rise. The history periods [8, 10, 12] precede the break and the query periods [16, 20] follow it, so a method that treats the history as a labelled training set is calibrated to a regime the graded records no longer sit in. The private estimators refit at every record period with recency weighting, so the truth tracks the break.

## Floors

Each lane's floor is the measured maximum over a frozen portfolio: cheap methods, a complete set of degenerate controls, a distribution-derived envelope optimised over error breakpoints for the currency lanes and over the full simplex for the turn lane, and two one-shot competent tiers, one fitted to the history labels and one fitted naively to the closed cases at their corrected values. A one-shot member is dropped from a lane's floor only where it would leave less than a 0.10 payable range, and every such exclusion is recorded in solution/floors.json. The competent public reference in solution/public_reference.py never sets a floor; it measures what an informed first attempt earns.

## Randomness

Published inputs are keyed draws under the public key floorplan-surveillance-public-v1-2026; the private key feeds one audit sentinel and nothing graded. Continuing the public stream predicts no private quantity because no private quantity is drawn.

## Generated counts

Dealers 360, periods 20, reference dealers 80, history rows 240, graded rows 560.
