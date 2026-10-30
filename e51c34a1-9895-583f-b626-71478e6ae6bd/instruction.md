# Buy auto-loan participations from the June 2026 offer

You are a structured-credit analyst at a buyer of seasoned auto-loan participations. A seller has offered fractional participations in every eligible loan of six public auto-loan securitization trusts, priced off their June 2026 monthly loan tapes. Your desk has to decide which loans to buy within a fixed budget and its limits, give the probability that each offered loan is charged off over the next three monthly tapes, and record the commitment in a memo.

`mandate/forward_flow_mandate.md` sets the budget and limits, how every participation is valued, the three files to deliver, and how they are graded. The offer itself is `offer/offer_2026-06.csv`. The loan tapes are the trusts' own SEC Regulation AB II asset-level filings (Schedule AL, Form ABS-EE Exhibit 102): the offer pools' tapes end at June 2026, and six older trusts from the same programs run from January 2025 to June 2026 with their outcomes.

Write `purchases.csv`, `chargeoff_probabilities.csv` and `memo.json` into `output/`. The July to September 2026 tapes are not in this workspace; your purchase is valued on them after you finish. Python 3 with numpy, pandas, pyarrow, scipy and scikit-learn is installed, and there is no network access.

The reward is continuous, from 0 to 1.
