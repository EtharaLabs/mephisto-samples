# Loan tape fields

Every parquet tape in `tapes/` holds one row per loan per monthly tape. The columns are 44 asset-level fields of Regulation AB II Schedule AL for automobile loans (17 CFR 229.1125, Item 3), exactly as the trust filed them with the SEC in its Form ABS-EE Exhibit 102, plus `period`. Numeric fields are typed as floats; every other field keeps the filed text. A blank is a value the filer left out. Rates and percentages are decimal fractions, so 0.1599 is 15.99 percent.

| Field | Meaning |
|---|---|
| `period` | The tape's reporting month, `YYYY-MM`, added from the filing's period of report |
| `assetNumber` | The filer's identifier of the loan, unique within the trust |
| `reportingPeriodEndingDate` | Last day of the reporting period, `MM-DD-YYYY` |
| `originationDate` | Month the loan was originated, `MM/YYYY` |
| `originalLoanAmount` | Amount financed at origination |
| `originalLoanTerm` | Term at origination, in months |
| `loanMaturityDate` | Scheduled maturity month, `MM/YYYY` |
| `originalInterestRatePercentage` | Interest rate at origination |
| `reportingPeriodInterestRatePercentage` | Interest rate in effect at the end of the period |
| `vehicleNewUsedCode` | 1 new, 2 used |
| `vehicleModelYear` | Model year of the vehicle |
| `vehicleValueAmount` | Value of the vehicle at origination |
| `vehicleManufacturerName` | Vehicle make |
| `obligorCreditScore` | Credit score of the obligor at origination |
| `obligorCreditScoreType` | The scoring model the filer names for that score |
| `coObligorIndicator` | Whether the loan has a co-obligor |
| `paymentToIncomePercentage` | Scheduled payment as a share of the obligor's income at origination |
| `obligorGeographicLocation` | The obligor's state |
| `remainingTermToMaturityNumber` | Months remaining to maturity |
| `reportingPeriodBeginningLoanBalanceAmount` | Balance at the start of the period |
| `reportingPeriodActualEndBalanceAmount` | Balance at the end of the period |
| `nextReportingPeriodPaymentAmountDue` | Payment due in the next period |
| `reportingPeriodScheduledPaymentAmount` | Payment scheduled in the period |
| `scheduledPrincipalAmount` | Principal portion of the scheduled payment |
| `scheduledInterestAmount` | Interest portion of the scheduled payment |
| `totalActualAmountPaid` | Everything the obligor paid in the period |
| `actualInterestCollectedAmount` | Interest collected in the period |
| `actualPrincipalCollectedAmount` | Principal collected in the period |
| `actualOtherCollectedAmount` | Fees and other amounts collected in the period |
| `otherPrincipalAdjustmentAmount` | Other adjustments to principal in the period |
| `chargedoffPrincipalAmount` | Principal charged off |
| `recoveredAmount` | Amount recovered on a charged-off loan |
| `repossessedIndicator` | Whether the vehicle has been repossessed |
| `repossessedProceedsAmount` | Proceeds from the sale of a repossessed vehicle |
| `currentDelinquencyStatus` | Days past due at the end of the period |
| `paymentExtendedNumber` | Number of payments extended in the period |
| `reportingPeriodModificationIndicator` | Whether the loan was modified in the period |
| `modificationTypeCode` | Kind of modification: 1 rate, 2 principal, 3 term, 4 extension, 98 other |
| `zeroBalanceCode` | Why the balance went to zero: 1 prepaid or matured, 2 third-party sale, 3 repurchased or replaced, 4 charged off, 5 servicing transfer, 99 unavailable |
| `zeroBalanceEffectiveDate` | Month the zero-balance event took effect, `MM/YYYY` |
| `interestPaidThroughDate` | Date through which interest has been paid, `MM-DD-YYYY` |
| `servicingFeePercentage` | Servicing fee rate |
| `subvented` | Subvention: 0 none, 1 rate subvention, 2 cash rebate, 98 other |
| `gracePeriodNumber` | Grace period, in days |
