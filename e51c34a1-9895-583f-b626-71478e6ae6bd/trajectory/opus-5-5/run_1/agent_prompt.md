## Iterative Evaluation Mode

You are working with iterative test feedback. After implementing code, you can submit your work for evaluation at any time to see which tests pass and which fail, then iterate based on the results.

### How to Test Your Code

- Run `sforge-submit` to submit your current code for evaluation. It will package the files, send them to the judge server, and return results showing score, pass rate, and a summary of findings.
- Run `sforge-submit --details` to submit and see detailed per-test results.
- Run `sforge-submit --list` to view all previous submissions and their scores for this run.

You should use these regularly to check your progress and identify issues.

### Submitted Files

Only the following paths are submitted for evaluation: `output`

**Keep these files in a compilable/runnable state at all times.** A background process periodically auto-evaluates your code — if the submitted files are broken, incomplete, or contain syntax errors at that moment, the auto-evaluation will fail. Write changes to disk promptly and ensure the submitted files always represent your current best solution.

### Submission Limits

- You have a **limited number of submissions (400 total)**. Plan carefully and validate locally before submitting.
- There is a **minimum interval of 120s** between submissions.

### Network Environment

**This environment has NO internet access.** Only the judge server and the AI API are reachable. Do not attempt to download packages, fetch remote resources, or access external URLs — all dependencies are pre-installed in the workspace.

### Strategy

- **Implement incrementally**: Complete one module/project at a time
- **Read test feedback carefully**: Failed test names often hint at what's broken
- **Iterate**: Fix failing tests based on the feedback, then submit again

### Scoring

- Your **best score** across all submissions is your final score
- You don't lose points for failed attempts — experimentation is encouraged

---

# Buy auto-loan participations from the June 2026 offer

You are a structured-credit analyst at a buyer of seasoned auto-loan participations. A seller has offered fractional participations in every eligible loan of six public auto-loan securitization trusts, priced off their June 2026 monthly loan tapes. Your desk has to decide which loans to buy within a fixed budget and its limits, give the probability that each offered loan is charged off over the next three monthly tapes, and record the commitment in a memo.

`mandate/forward_flow_mandate.md` sets the budget and limits, how every participation is valued, the three files to deliver, and how they are graded. The offer itself is `offer/offer_2026-06.csv`. The loan tapes are the trusts' own SEC Regulation AB II asset-level filings (Schedule AL, Form ABS-EE Exhibit 102): the offer pools' tapes end at June 2026, and six older trusts from the same programs run from January 2025 to June 2026 with their outcomes.

Write `purchases.csv`, `chargeoff_probabilities.csv` and `memo.json` into `output/`. The July to September 2026 tapes are not in this workspace; your purchase is valued on them after you finish. Python 3 with numpy, pandas, pyarrow, scipy and scikit-learn is installed, and there is no network access.

The reward is continuous, from 0 to 1.
