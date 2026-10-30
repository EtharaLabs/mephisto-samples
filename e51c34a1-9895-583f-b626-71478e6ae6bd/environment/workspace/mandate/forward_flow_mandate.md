# Forward-flow participation mandate: the June 2026 auto-loan offer

## The offer

A seller offers participations in every eligible loan of six auto-loan securitization trusts, as of the reporting period ending 30 June 2026. A loan is eligible when its June 2026 tape shows a balance above zero, no repossession, no zero-balance code, and fewer than 120 days past due. `offer/offer_2026-06.csv` lists all 104,845 eligible loans with their June balance, days past due, delinquency bucket, coupon, coupon band and offer price, 1,564,236,457.06 USD in all.

| Pool | Trust | Loans offered | Offer price, USD |
|---|---|---|---|
| `sdart-2022-5` | Santander Drive Auto Receivables Trust 2022-5 | 23,522 | 275,753,472.49 |
| `drive-2024-1` | Drive Auto Receivables Trust 2024-1 | 26,936 | 490,608,939.16 |
| `amcar-2022-2` | AmeriCredit Automobile Receivables Trust 2022-2 | 18,641 | 204,830,788.21 |
| `blast-2024-1` | Bridgecrest Lending Auto Securitization Trust 2024-1 | 14,096 | 239,349,047.86 |
| `crvna-2021-n3` | Carvana Auto Receivables Trust 2021-N3 | 5,000 | 34,500,854.30 |
| `fordo-2023-b` | Ford Credit Auto Owner Trust 2023-B | 16,650 | 319,193,355.04 |

You may buy any fraction of an offered loan, above 0 and up to 1, at that fraction of its offer price.

## Limits

- Commit at most 234,635,468.56 USD, which is 15 percent of the offer, and at least 222,903,695.13 USD, which is 95 percent of that budget.
- Commit at most 58,658,867.14 USD, a quarter of the budget, to any one pool.
- Commit at most 46,927,093.71 USD, a fifth of the budget, to loans 30 or more days past due on the June tape.
- Every amount is checked to within 1.00 USD.

## How a participation is valued

The buyer holds every participation through the July, August and September 2026 tapes of the loan's own trust, as the trust files them with the SEC, and values it on them.

- Cash: the loan's `totalActualAmountPaid` on the three tapes, summed.
- Exit: the first of the three tapes on which `zeroBalanceCode` is set and `zeroBalanceEffectiveDate` falls in that tape's own month. Code 1, prepaid or matured, adds nothing more. Code 4, charged off, adds 30 percent of that tape's `chargedoffPrincipalAmount`. Any other code refunds the participation at its price.
- Mark: a loan with no exit and a balance above zero on the September tape is marked at 30 percent of that balance when the September tape shows it repossessed or 120 or more days past due, and otherwise at its September balance times the mark for its September delinquency bucket. A loan with no exit and no balance on the September tape is refunded at its price.

| Days past due in September | Mark per dollar of balance |
|---|---|
| 0 | 1.00 |
| 1-29 | 0.96 |
| 30-59 | 0.85 |
| 60-89 | 0.65 |
| 90-119 | 0.35 |

A participation's value is its fraction of the loan's cash, exit recovery and mark, less its price. A refunded participation is worth 0.

Each loan's offer price is its June balance times the grid price below for its June bucket and band, rounded to the cent. The grid is the realized value per dollar of June balance, by bucket and band, of the six reference trusts' loans over the three months after each of their tapes from June 2025 to March 2026, valued by these same rules, leaving out the loans those rules refund.

| Days past due | <10 | 10-15 | 15-20 | 20+ |
|---|---|---|---|---|
| 0 | 1.0088 | 1.0145 | 1.0205 | 1.0257 |
| 1-29 | 0.9702 | 0.9655 | 0.9593 | 0.9499 |
| 30-59 | 0.8888 | 0.8743 | 0.8577 | 0.8142 |
| 60-89 | 0.7442 | 0.7352 | 0.7158 | 0.6668 |
| 90-119 | 0.5328 | 0.5405 | 0.5291 | 0.5382 |

Delinquency buckets read `currentDelinquencyStatus`, the days past due: 0, 1 to 29, 30 to 59, 60 to 89, and 90 to 119. Coupon bands read `reportingPeriodInterestRatePercentage`, or `originalInterestRatePercentage` when the current rate is zero: under 0.10, from 0.10 to under 0.15, from 0.15 to under 0.20, and 0.20 or more.

## Data

- `tapes/offer/<pool>.parquet` holds each offer pool's tapes from January to June 2026.
- `tapes/reference/<trust>.parquet` holds six older trusts from the same programs, every tape from January 2025 to June 2026, whose outcomes you can value by the rules above.

| Trust tape | Trust | Months | Loans |
|---|---|---|---|
| `sdart-2022-4` | Santander Drive Auto Receivables Trust 2022-4 | 2025-01 to 2026-06 | 44,652 |
| `drive-2021-3` | Drive Auto Receivables Trust 2021-3 | 2025-01 to 2026-06 | 32,370 |
| `amcar-2022-1` | AmeriCredit Automobile Receivables Trust 2022-1 | 2025-01 to 2026-06 | 23,847 |
| `blast-2023-1` | Bridgecrest Lending Auto Securitization Trust 2023-1 | 2025-01 to 2026-06 | 29,697 |
| `crvna-2021-n2` | Carvana Auto Receivables Trust 2021-N2 | 2025-01 to 2026-06 | 20,928 |
| `fordo-2023-a` | Ford Credit Auto Owner Trust 2023-A | 2025-01 to 2026-06 | 30,574 |

Each tape keeps 44 Schedule AL fields as the trust filed them, plus `period`; `reference/schedule_al_fields.md` describes them. The July to September 2026 tapes are not in this workspace.

## What to deliver

Write three files into `output/`.

1. `purchases.csv`, with the header `pool,assetNumber,fraction`: one row per participation, naming an offered loan by its pool and `assetNumber` exactly as in the offer file, with a fraction above 0 and at most 1. Name each loan at most once.
2. `chargeoff_probabilities.csv`, with the header `pool,assetNumber,probability`: one row for every offered loan, giving the probability, from 0 to 1, that the loan exits charged off, code 4, on the July, August or September tape.
3. `memo.json`, an object with these entries:
   - `committed_usd`: the total price committed;
   - `committed_by_pool_usd`: an object from pool to the price committed to it;
   - `committed_delinquent_usd`: the price committed to loans 30 or more days past due on the June tape;
   - `loans_bought`: the number of rows in `purchases.csv`;
   - `expected_value_usd`: your expected total value of the purchase;
   - `expected_chargeoff_balance_usd`: the sum, over your participations, of fraction times charge-off probability times June balance.

## How the work is graded

The reward runs from 0 to 1. Purchase value carries 70 percent of it, the charge-off probabilities 20 percent and the memo 10 percent, and each part is rounded to two decimals.

- Purchase value is the realized value of your purchase, scored 0 at the value of a 15 percent slice of every offered loan and 1 at the best purchase hindsight allows within these limits, in proportion in between, and never below 0.
- The charge-off probabilities earn their Brier skill: 1 minus the sum of squared errors of your probabilities, divided by the sum of squared errors of one rate equal to the realized share of offered loans that are charged off, and never below 0. A file that misses, repeats or mis-ranges any offered loan earns 0.
- The memo earns the share of its six entries that hold. Each amount must match the figure recomputed from your `purchases.csv`, and for the charge-off balance from your probabilities as well, within 1.00 USD; `loans_bought` must be exact; and `expected_value_usd` must be a finite number.

A `purchases.csv` that is missing or malformed, names a loan outside the offer or names one twice, carries a fraction outside the range, or breaks the budget, the floor or either cap makes the whole reward 0.
