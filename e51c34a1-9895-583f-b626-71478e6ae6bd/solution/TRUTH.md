<!-- GENERATED SECTION. DO NOT HAND-EDIT. -->
<!-- FORGE-CANARY-BEGIN -->
<!-- FORGE-CANARY-SLOT-1: e982fee812b5db6e9f890a98d66334cb7a9a324515072566d5780345e6ee8a9c -->
<!-- FORGE-CANARY-SLOT-2: 97a6b6a2007bfe0ad300b51a4ac2531e30f4dde5a95df7e3a8f8172eaba817aa -->
<!-- FORGE-CANARY-SLOT-3: 1965d48ddc98c2c5d420e105285aee7a42781cb1e90dd17cf92ec0177d94790a -->
<!-- FORGE-CANARY-END -->

# TRUTH: auto-loan ABS forward-flow purchase

Boundary tape 2026-06; hidden outcome tapes 2026-07, 2026-08, 2026-09. Golden trajectory through instruction.md; every step binds one manifest deliverable or red line and names the criteria that grade it.

## Golden trajectory

| Step | Action | Binds | Criteria |
| --- | --- | --- | --- |
| S1 | value every reference-trust loan under the mandate's rules and fit charge-off and value models on the loan histories | D2 | D2-outcome-skill |
| S2 | score every offered loan's charge-off probability and write output/chargeoff_probabilities.csv | D2 | D2-outcome-skill |
| S3 | choose participations that maximize expected value less price and write output/purchases.csv | D1 | D1-outcome-capture |
| S4 | keep the committed price inside the budget, the 95 percent floor, every pool cap and the delinquent cap | R1 | D1-outcome-capture, D2-outcome-skill, D3-craft-memo |
| S5 | name only offered loans, each once, with fractions above 0 and at most 1 | R2 | D1-outcome-capture, D2-outcome-skill, D3-craft-memo |
| S6 | write output/memo.json with amounts recomputed from the purchase and the probabilities | D3 | D3-craft-memo |

## Criteria

| Criterion | Obligation | Dimension | Weight | Credit |
| --- | --- | --- | --- | --- |
| D1-outcome-capture | D1 | outcome | 70 | output/purchases.csv earns the share of the hindsight-optimal value gain over a pro rata slice that its realized value captures, clipped to [0, 1] and rounded to two decimals. |
| D2-outcome-skill | D2 | outcome | 20 | output/chargeoff_probabilities.csv earns its Brier skill over every offered loan against one rate equal to the realized charged-off share, clipped to [0, 1] and rounded to two decimals. |
| D3-craft-memo | D3 | craft | 10 | output/memo.json earns the share of its six entries consistent with output/purchases.csv and output/chargeoff_probabilities.csv, rounded to two decimals. |

## Scoring

The reward is continuous on [0, 1]: Reward Kit's weighted mean of three compiled criteria, purchase value 70, charge-off skill 20 and memo consistency 10, each rounded half up to two decimals.

A missing or malformed output/purchases.csv, a loan outside the offer or named twice, a fraction outside (0, 1], or a committed price above the budget, below the 95 percent floor, above a pool cap or above the delinquent cap, each with a 1.00 USD tolerance, scores every criterion 0.

| Term | Value |
| --- | --- |
| offered loans | 104,845 |
| offered price, USD | 1,564,236,457.06 |
| budget, USD | 234,635,468.56 |
| pool cap, USD | 58,658,867.14 |
| delinquent cap, USD | 46,927,093.71 |
| deployment floor, USD | 222,903,695.13 |
| tolerance, USD | 1.00 |
| zero-credit value (pro rata slice), USD | 204,531.97 |
| full-credit value (hindsight optimum), USD | 32,609,595.62 |
| realized charge-off share of offered loans | 0.032667 |
| Brier reference sum | 3313.1146 |

## September marks (per dollar of balance)

| Bucket | Mark |
| --- | --- |
| 0 | 1.00 |
| 1-29 | 0.96 |
| 30-59 | 0.85 |
| 60-89 | 0.65 |
| 90-119 | 0.35 |

## Offer price grid (per dollar of June balance)

| Bucket | <10 | 10-15 | 15-20 | 20+ |
| --- | --- | --- | --- | --- |
| 0 | 1.0088 | 1.0145 | 1.0205 | 1.0257 |
| 1-29 | 0.9702 | 0.9655 | 0.9593 | 0.9499 |
| 30-59 | 0.8888 | 0.8743 | 0.8577 | 0.8142 |
| 60-89 | 0.7442 | 0.7352 | 0.7158 | 0.6668 |
| 90-119 | 0.5328 | 0.5405 | 0.5291 | 0.5382 |

## Reference answer: offer pools

| Pool | Trust | Loans | Offered USD | Bought USD | Charged off | Paid | Refunded | Live | Recovery |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sdart-2022-5 | Santander Drive Auto Receivables Trust 2022-5 | 23,522 | 275,753,472.49 | 56,357,910.39 | 634 | 1,540 | 7 | 21,273 | 68 |
| drive-2024-1 | Drive Auto Receivables Trust 2024-1 | 26,936 | 490,608,939.16 | 58,658,866.64 | 1,220 | 1,503 | 17 | 24,046 | 150 |
| amcar-2022-2 | AmeriCredit Automobile Receivables Trust 2022-2 | 18,641 | 204,830,788.21 | 34,745,961.44 | 316 | 1,325 | 0 | 16,863 | 137 |
| blast-2024-1 | Bridgecrest Lending Auto Securitization Trust 2024-1 | 14,096 | 239,349,047.86 | 58,658,866.64 | 1,008 | 247 | 18 | 12,820 | 3 |
| crvna-2021-n3 | Carvana Auto Receivables Trust 2021-N3 | 5,000 | 34,500,854.30 | 10,061,941.61 | 206 | 306 | 10 | 4,476 | 2 |
| fordo-2023-b | Ford Credit Auto Owner Trust 2023-B | 16,650 | 319,193,355.04 | 16,151,921.34 | 41 | 1,516 | 38 | 15,016 | 39 |

## Reference answer: deliverables

- purchases.csv: 16,932 participations, the linear-programme optimum on realized values within the budget, the deployment band and both caps, half a dollar inside each bound.
- chargeoff_probabilities.csv: 1 for every offered loan charged off on the hidden tapes, 0 otherwise.
- memo.json: the committed amounts recomputed from purchases.csv, the realized value as expected value, and the charged-off balance of the purchased participations.

## Reference trusts shown to the agent

| Trust tape | Trust | Months | Loans |
| --- | --- | --- | --- |
| sdart-2022-4 | Santander Drive Auto Receivables Trust 2022-4 | 2025-01 to 2026-06 | 44,652 |
| drive-2021-3 | Drive Auto Receivables Trust 2021-3 | 2025-01 to 2026-06 | 32,370 |
| amcar-2022-1 | AmeriCredit Automobile Receivables Trust 2022-1 | 2025-01 to 2026-06 | 23,847 |
| blast-2023-1 | Bridgecrest Lending Auto Securitization Trust 2023-1 | 2025-01 to 2026-06 | 29,697 |
| crvna-2021-n2 | Carvana Auto Receivables Trust 2021-N2 | 2025-01 to 2026-06 | 20,928 |
| fordo-2023-a | Ford Credit Auto Owner Trust 2023-A | 2025-01 to 2026-06 | 30,574 |

## Rejected routes

| Route | Known-wrong control |
| --- | --- |
| buy a slice of every offered loan, spread evenly within the caps | K3-naive |
| buy the current loans with the highest coupons | K3-persist |
| rank loans by the average value of their delinquency bucket | K3-bucket |
| spend more than the budget | K4-over-budget |
| commit less than 95 percent of the budget | K4-under-floor |
| concentrate the purchase in one pool | K4-pool-cap |
| load the purchase with delinquent loans | K4-delinquent-cap |
| name a loan outside the offer | K4-unoffered |
| name a loan twice | K4-duplicate |
| give every offered loan one charge-off rate | K4-constant-probability |
| state memo figures that the files do not support | K4-memo-off |

## Not applicable rubric cells

- D1/constraints: the purchase limits are the R1 gate
- D1/coverage: every row must name an offered loan; coverage is the R2 gate, not a separate item
- D1/craft: the purchase file has a fixed three-column schema with nothing further to judge
- D1/process: only the purchase file is graded, not the method that produced it
- D1/robustness: graded on one hidden three-month window over six disjoint pools; no drift is injected
- D2/constraints: the probability range is enforced inside the outcome item
- D2/coverage: a file that misses or repeats any offered loan already earns 0 under the outcome item
- D2/craft: the probability file has a fixed three-column schema with nothing further to judge
- D2/process: only the probabilities are graded, not how they were produced
- D2/robustness: graded on one hidden window; no drift is injected
- D3/constraints: the memo restates committed amounts the R1 gate already bounds
- D3/coverage: the six entries are counted inside the craft item
- D3/outcome: the memo's expected value is a forecast the buyer owns; only its consistency is graded
- D3/process: the memo records results, not process
- D3/robustness: the memo is recomputed from the agent's own files, so no drift applies
- R1/constraints: the budget, floor and cap red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R1/coverage: the budget, floor and cap red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R1/craft: the budget, floor and cap red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R1/outcome: the budget, floor and cap red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R1/process: the budget, floor and cap red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R1/robustness: the budget, floor and cap red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R2/constraints: the offer-membership and fraction-range red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R2/coverage: the offer-membership and fraction-range red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R2/craft: the offer-membership and fraction-range red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R2/outcome: the offer-membership and fraction-range red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R2/process: the offer-membership and fraction-range red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
- R2/robustness: the offer-membership and fraction-range red line is a gate inside every compiled criterion, which scores 0 on any breach, not a weighted item
