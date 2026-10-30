# VERDICT:  2 bundles (collective)

Author-side summary compiled on 2026-10-30 from the CRUCIBLE lane outcomes and the recorded `opus-5-5` rollouts in each bundle's `trajectory/`. It is not a CRUCIBLE root report, and no signed pilot exists for either bundle.

## Collective disposition

| Field           | Value                                                 |
| --------------- | ----------------------------------------------------- |
| Outcome         | `hold`                                              |
| Reason          | `coverage-gap` (10 medium, 19 low across 2 bundles) |
| Bundles audited | 2                                                     |
| Retained        | none                                                  |
| Fired lanes     | none, in either bundle                                |
| Sealed digests  | absent, both                                          |
| Successors owed | none                                                  |

Both bundles are on HOLD and neither was retained. No lane fired in either, so nothing at these digests is a defect that forces a successor. Each bundle is held by the same two unrun lanes — discrimination and pilot — plus bundle-specific rubric, environment and probe gaps. Neither bundle can be placed until its medium gaps close.

| # | UUID                                     | Task                                      | Medium | Low | Outcome  |
| - | ---------------------------------------- | ----------------------------------------- | ------ | --- | -------- |
| 1 | `98ab6785-430d-5bfc-96f1-ea5f138b5e8e` | `edgebench/synthetic_claims_reserving`  | 5      | 8   | `hold` |
| 2 | `e51c34a1-9895-583f-b626-71478e6ae6bd` | `ethara/abs-auto-forward-flow-purchase` | 5      | 11  | `hold` |

## Collective executive summary

The two bundles fail placement for opposite reasons, and the contrast is the most useful finding in this audit.

Bundle 1 is engineering-clean and provenance-thin. Its scorer is correct at line level, its control ladder has exact endpoints — `empty` at 0.0 and `oracle` at 100.0 — and its selftest carries more than fifty passing predicates including factorial independence across 32 combinations, 80 directed edges and 120 repair orders. But its provenance record is unminted and unsigned, its screening was never run, and four of its five lane floors were installed after the author observed the recorded plateau and an operator score goal. The bundle's own manifest says so in writing.

Bundle 2 inverts that. Its provenance is the strongest artifact in either bundle — real screening roots with digests, a near-duplicate screen actually executed, a recorded empty-submission run, hash-locked dependencies, digest-pinned base images, non-root users in both images, and a full SEC EDGAR source attestation naming every filing by accession and sha256. But its reward ceiling is anchored to hindsight the agent cannot obtain, and its graded holdout is real public record rather than synthetic data, with no freeze-date check performed against it.

Neither defect fires. Bundle 1's floors are arithmetically exact and self-disclosed; bundle 2's hindsight anchor is a declared scoring design with a proportional band above a measured pro-rata floor, and its recorded agent did score inside that band. Both are provenance-of-policy gaps rather than mechanism defects, which is why both land at HOLD rather than retained.

The recorded rollouts agree that both tasks are hard. Neither reached full reward in a full twelve-hour budget: bundle 1 best 60.3467 of 100 across 71 submissions, bundle 2 best 0.429 of 1.0 across 73. Both rollouts are single, author-side, locally judged, and both timed out at the wall clock. Neither constitutes measured difficulty.

---

# Part I — `98ab6785` (`edgebench/synthetic_claims_reserving`)

## Disposition

| Field                 | Value                                                                |
| --------------------- | -------------------------------------------------------------------- |
| Outcome               | `hold`                                                             |
| Reason                | `coverage-gap` (5 medium, 8 low)                                   |
| Retained              | no                                                                   |
| UUID                  | `98ab6785-430d-5bfc-96f1-ea5f138b5e8e`                             |
| Canonical bundle hash | `a07621cda2989841d08184aa664ed5dc406be06b1a1ee03d755100b38f03fd9a` |
| Sealed digest         | absent                                                               |
| Declared status       | `draft-unpiloted` (`task.toml`)                                  |
| Lineage               | attempt 1; no predecessor recorded                                   |

## Task

| Field         | Value                                                                                                                                                                                                                                                                 |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name          | `edgebench/synthetic_claims_reserving`                                                                                                                                                                                                                              |
| Category      | professional-knowledge-work, insurance, claims-reserving, synthetic                                                                                                                                                                                                   |
| Goal          | Recover five independent deterministic claims methods — primary ultimate severity, reporting-lag timing, elevated reopening incidence, future payment timing and aggregate large-loss tail rank — from an observable 25,000-row panel plus aggregate judge feedback |
| Reward        | Five independent lanes at 20 points each, 100 total; `credit = clip((metric - floor)/(1 - floor), 0, 1)` per lane                                                                                                                                                   |
| Null floor    | 0.0, measured                                                                                                                                                                                                                                                         |
| Harbor schema | 1.4                                                                                                                                                                                                                                                                   |
| Agent budget  | single turn, 43,200 s, no-network                                                                                                                                                                                                                                     |
| Verifier      | separate image, 3,600 s, no-network, static JSON judge that never executes the submission                                                                                                                                                                             |

## Findings

| Lane          | Outcome | Minor gaps                                                             |
| ------------- | ------- | ---------------------------------------------------------------------- |
| surface       | clean   | `README-ABSENT` (low)                                                |
| environment   | clean   | `G-ENV-SBOM` (medium), `G-ENV-BASEPIN` (low), `G-ENV-PRIV` (low) |
| verifier      | clean   | none                                                                   |
| statement     | clean   | none                                                                   |
| rubric        | clean   | `G-RUB-POSTHOC` (medium), `RUBRIC-FLOOR-ABOVE-CONTROL` (medium)    |
| contamination | clean   | `G-CON-RECORD` (low)                                                 |
| isolation     | clean   | none                                                                   |

The verifier lane is the bundle's strongest evidence. Every formula in `instruction.md` traces to an exact line in `tests/scoring/score.py`: the severity form `(1-mean(e))/(1+sqrt(mean(e²)))` at lines 76–77, the absence of a coverage multiplier on severity and distribution lanes at lines 78 and 84 against its presence on reopening and large loss at lines 74 and 68, the zero-vector guard at line 82, the cash-cutoff invalidation scoped to `cash_pattern` alone at lines 60–61, missing positives counted as false negatives at line 72, and the `type(x) in (int, float)` test at lines 12–13 that correctly excludes booleans from numbers. Floors are read from `spec["anchor_floor"]` in `scorer_manifest.json`, never hardcoded.

Failure attribution is deliberate. `tests/scoring/eval_script.py` holds exactly one `except`, at line 31, typed to `(OSError, ValueError, UnicodeError, RecursionError)`, scoped only to agent-caused modes. Loading the private truth corpus at line 20 sits outside it, and the `raise ValueError("empty private target corpus: infrastructure failure")` guard in `score.py` lines 90–91 is caught nowhere. The comment at `eval_script.py:19` states the rule: "Infrastructure errors intentionally propagate; never disguise missing truth as agent failure." No bare `except` and no `|| true` exists anywhere on the scoring path. `tests/test.sh` sets `set -eu` and `exec`s the evaluator.

Reward transport is triply redundant and invariant to stray output. Lines 38–40 write `/logs/verifier/reward.txt` as a bare ten-decimal float and `/logs/verifier/reward.json` as the full report; lines 41–43 print the same dict between `>>>>> Start Structured Result` and `>>>>> End Structured Result`. All three derive from one dict built at line 34. The submission is parsed as inert JSON, never imported or executed, the verifier runs in a separate image, and `judge_requirements.txt` declares stdlib only.

Isolation was checked at field level. `environment/Dockerfile` carries exactly one COPY, at line 19, scoped to the two observable datasets into `/workspace/data/`. The five target fields `ultimate_severity`, `reporting_pattern`, `reopening_flag`, `cash_pattern` and `large_loss_score` appear only in `tests/hidden_test_data/outcomes.jsonl`, which `tests/Dockerfile:9` copies into the judge image alone. A targeted search for those names across both attachments returned nothing.

Determinism holds: no `random`, no clock or environment branching, no threading, `json.dumps(..., sort_keys=True, allow_nan=False)`, `python3 -I -B`, and a stable sort in the tie-ranking at lines 16–27.

The control ladder has exact endpoints. `empty` measures 0.0 with coverage 0.0 on every lane; `oracle` measures 100.0 with metric 1.0 and 20.0 points on all five lanes over 5,000 of 5,000 records. The selftest under Python 3.14.3 adds byte-idempotent regeneration, train and query key disjointness, every training realization preceding every query accident period, reopening prevalence at exactly 20 percent in each period, each missing field losing exactly its own 20 points, duplicate-key invalidation, symlink rejection, malformed JSON and every NaN or Infinity form yielding zero, and all 240 diagnostic repair paths telescoping to oracle. Factorial independence is tight: maximum additivity error 1.42e-14 against copy-forward and 7.11e-15 against the public reference.

## Coverage gaps

| Lane           | Outcome | Code                     | Severity |
| -------------- | ------- | ------------------------ | -------- |
| discrimination | gap     | `discrimination-unrun` | medium   |
| pilot          | gap     | `pilot-unsigned`       | medium   |

These lanes were not run in this audit. Each caps the bundle at HOLD and neither is a defect in the task.

## Minor gaps

| #  | Severity | Code                           | Gap                                                                                                                                             |
| -- | -------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | medium   | `discrimination-unrun`       | No `solution/alternates/`; the lane needs three alternates and could not run                                                                  |
| 2  | medium   | `pilot-unsigned`             | Judge reached at a local `host.docker.internal:8081`; `screening_status: not-run`, `status = "draft-unpiloted"`                           |
| 3  | medium   | `G-RUB-POSTHOC`              | Four of five lane floors were installed after the author observed the recorded plateau and an operator score goal                               |
| 4  | medium   | `RUBRIC-FLOOR-ABOVE-CONTROL` | The cash floor exceeds the bundle's own competent control, which earns 0 of 20 there and 1.41 of 20 on large loss                               |
| 5  | medium   | `G-ENV-SBOM`                 | No SBOM anywhere, and OS packages install unpinned                                                                                              |
| 6  | low      | `NOTES-STALE`                | `NOTES.md` and `task.toml` describe an unpiloted draft with placeholder tags, but the bundle ships resolved digests and a new-rules rollout |
| 7  | low      | `ANCHOR-REPLAY`              | The same archived submission scores 33.878 by calculation and 37.421 by local replay; cause recorded as not established                         |
| 8  | low      | `ANCHOR-ARCHIVE-ABSENT`      | The calibration anchor is an `agent-45` record from `refine-runs/opus-5/`, which is not in this bundle                                      |
| 9  | low      | `PROBE-OUTAGE`               | The one rollout timed out after three resumes and an authentication exhaustion; cost covers about 41 minutes of 12 hours                        |
| 10 | low      | `G-ENV-BASEPIN`              | Both Dockerfiles read `FROM python:3.11-slim`, a floating tag, though the pushed images are digest-pinned                                     |
| 11 | low      | `G-ENV-PRIV`                 | The agent user holds passwordless unrestricted sudo; the judge container has no `USER` directive                                              |
| 12 | low      | `G-CON-RECORD`               | `provenance.yaml` declares `binding_status: unminted-unsigned` while `provenance.sig` is present                                          |
| 13 | low      | `README-ABSENT`              | No bundle `README.md`; the uuid is absent from the repository reconcile tables                                                                |

What the material gaps mean:

1. `discrimination-unrun` (medium): the bundle carries no alternate solutions, so nothing shows the verifier separates a correct recovery of the five methods from a near-miss. The factorial study substitutes perfect reference fields rather than authoring near-misses, and its own `scope` field says so: "Independent available score gains, NOT learned repair paths or demonstrated hours of progress."
2. `pilot-unsigned` (medium): `run_config.json` records `judge_url: http://host.docker.internal:8081`. `provenance.yaml` states `screening_status: not-run` and `claim: No screening, image-build, pilot or publication attestation is asserted`. `task.toml` sets `status = "draft-unpiloted"`.
3. `G-RUB-POSTHOC` (medium): `measurements/scorer_manifest.json.anchors.diff` shows four floors moved from `0` to measured values — severity 0.8635424166399702, report timing 0.784706166733507, cash timing 0.7887383677353506, all chain-ladder metrics, and large loss 0.5251815431467007, a copy-forward metric. Reopening's 0.3333333333333333 was already public and is unchanged. The same diff rewrites the manifest's `calibration` field from "Five equal substantive weights fixed before measuring the restructured ladder. No score-target fitting." to "Four new floors are the best measured textbook-control metrics per lane, selected after observing the Opus plateau and the operator's below-0.50 goal. This is retrospective calibration, not independent difficulty evidence." `NOTES.md:7` repeats it: "the selection of this scoring policy occurred AFTER seeing the Opus plateau and the operator's score goal, and is post-hoc calibration." The mechanism is sound and each floor equals, to full precision, the metric the named control actually measured. The gap is provenance of the policy, not arithmetic. Because the judge returns per-lane metric and points, a floor is recoverable algebraically from any positive-credit submission, which `NOTES.md:9` concedes — so withholding the four numbers is not a secrecy guarantee.
4. `RUBRIC-FLOOR-ABOVE-CONTROL` (medium): the bundle's own `public_reference` control totals 45.15699702394183, and two of its five lanes are near-dead under the installed floors. Cash timing measures 0.739451038478272 against a 0.7887383677353506 floor and earns exactly 0 of 20. Large loss measures 0.5587302679526188 against a 0.5251815431467007 floor and earns 1.4131179747413802 of 20. A competent public-only method therefore collects 44 of its 45 points from three lanes. The `every_problem_has_competent_headroom` predicate passes on a greater-than-0.01-point test, which `RUNG_FEASIBILITY.md:35` correctly calls "a detectability check, not a difficulty quota." It does not fire: the recorded agent beat the cash floor at metric 0.8834847470135483 for 8.969577510364783 points, so the lane is winnable. Separately, the declared control ordering is violated — `summary.json` records `copy_forward->chain_ladder: -0.34482758620689774`, because chain ladder anchors three lanes exactly and scores 0.0 while copy-forward retains a small reopening excess. This is disclosed and deliberately retired at `NOTES.md:15` and `RUNG_FEASIBILITY.md:34`, so it is recorded rather than counted separately.
5. `G-ENV-SBOM` (medium): a bundle-wide search for `*sbom*`, `*spdx*` and `*cyclonedx*` returns nothing. `environment/Dockerfile` lines 8–10 install `git curl jq build-essential ca-certificates sudo xz-utils` with no version pins, and no agent-side dependency manifest exists — the agent authors `/workspace/requirements.txt` itself. `no-network` blocks late substitution at run time but does nothing for build reproducibility.
6. `NOTES-STALE` (low): `NOTES.md:31` says "Placeholder image tags remain unresolved," and `selftest.txt` carries `PASS three submit paths, Python base and tag-only placeholders` — but `task.toml` lines 18 and 27 carry fully resolved digests whose short tags are the first twelve hex characters of those digests. The selftest predates the shipped manifest and does not certify it. `NOTES.md:11` and `RUNG_FEASIBILITY.md:56` both assert no new agent trajectory was run, yet `trajectory/opus-5-5/run_1/` is a 71-submission rollout whose lane fractions reconcile exactly against the new floors.
7. `ANCHOR-REPLAY` (low): `anchors.json` scores one archived submission two ways. Rescaling the recorded rounded metrics gives 33.878439126442636; an independent local replay of the same archive gives 37.42119487625333. Severity, reopening and large loss match; report timing differs at coverage 0.97 and metric 0.929028708013897 against the recorded 0.93 and 0.8908915183617553, and cash timing at 0.92 and 0.7259982873483335 against 0.96 and 0.7581878550843415. `NOTES.md:13` is explicit the cause "has not been established." The honesty is correct; the open question sits on the two lanes carrying gap 4.
8. `ANCHOR-ARCHIVE-ABSENT` (low): the calibration rests on an `agent-45` record scoring 76.3475107155616 under the old rules, placed at `NOTES.md:23` in `refine-runs/opus-5/` "outside this draft." That directory is not in the bundle. The shipped trajectory is a different model line whose own `auto-45` scores 60.34664280395813 under the new rules; the two must not be conflated.
9. `PROBE-OUTAGE` (low): the single rollout ran 43,199.175857543945 s with `timed_out: true` and `resume_count: 3`. The first segment lasted 2,071.8 s; two resumes then failed within roughly 178 s and 188 s each against `401 all 3 accounts exhausted`; a third ran about eleven and a quarter hours to the wall clock. `agent_output.txt` holds exactly three terminal result blocks, all flagged `is_error: true` with `api_error_status: 401`, each reporting `total_cost_usd: 3.1008250000000013` — so the only authoritative cost figure covers about the first 41 minutes of twelve hours, and spend for the remainder is not recoverable.
10. `G-ENV-BASEPIN` (low): `environment/Dockerfile:1` and `tests/Dockerfile:1` both read `FROM python:3.11-slim`. The consumed artifacts are digest-pinned in `task.toml`, so a runner gets a fixed image; a rebuild from source does not.
11. `G-ENV-PRIV` (low): `environment/Dockerfile` lines 12–14 grant `agent ALL=(ALL) NOPASSWD:ALL`, so the only isolation backstop in the agent image is `no-network` rather than lack of privilege. `tests/Dockerfile` has no `USER` directive, so the judge runs as root for the whole of `test.sh`. Neither is stated as intentional anywhere.
12. `G-CON-RECORD` (low): `provenance.yaml` declares `binding_status: unminted-unsigned` and `screening_status: not-run` with an empty `external_evidence` list, yet `provenance.sig` is a real SSH ed25519 blob under namespace `trinity.attestation.v1`. A signature exists while the record it covers says it is unsigned. Separately, `grounding.yaml` holds JSON inside a `.yaml` filename — cosmetic, folded in here.
13. `README-ABSENT` (low): the bundle ships no `README.md`, though the repository's own bundle diagram lists one as a standard member, and its uuid is absent from the repository reconcile tables.

## Difficulty evidence (author-side, not signed)

`claude-opus-5-5`, run `opus55-r2`, single turn, 43,200 s, judge enabled on a local container, cooldown 1,800 s, auto-eval interval 900 s, submissions unbounded.

| Probe                         | Submissions            | Best              | Passes |
| ----------------------------- | ---------------------- | ----------------- | ------ |
| 2026-10-29 `opus-5-5/run_1` | 71 (24 agent, 47 auto) | 60.34664280395813 | 0      |

`best_pass_rate` is 0.0 on all 71. Best total 60.34664280395813 of 100, reached at `auto-45` and tied by `agent-24`, `auto-46` and `auto-47`, then flat to the wall clock. Against a client bar of pass@1 below 0.70, this meets it on difficulty.

The channels must be read separately. The 24 `agent-N` records are genuine decision points; the 47 `auto-N` records are timed re-scores of persisted state on a 900 s cadence.

| Channel     | n  | Min       | Max       | Mean   | Zeros |
| ----------- | -- | --------- | --------- | ------ | ----- |
| `agent-N` | 24 | 0.0       | 60.346643 | 12.767 | 5     |
| `auto-N`  | 47 | 34.002015 | 60.346643 | 47.517 | 0     |

All five zeros are agent-authored, at `agent-11`, `agent-13`, `agent-15`, `agent-17` and `agent-22`. The auto series is a monotone staircase: 34.00, 38.85, 45.77, 46.47, 48.00, 52.20, 52.38, 57.82, 60.35.

Lane detail at the best submission, full coverage of 5,000 of 5,000:

| Lane          | Metric             | Floor              | Fraction           | Points of 20       |
| ------------- | ------------------ | ------------------ | ------------------ | ------------------ |
| severity      | 0.9212365969995068 | 0.8635424166399702 | 0.4227993706096655 | 8.45598741219331   |
| report_timing | 0.9258657880476628 | 0.784706166733507  | 0.6556603093198073 | 13.113206186396146 |
| reopening     | 1.0                | 0.3333333333333333 | 1.0                | 20.0               |
| cash_timing   | 0.8834847470135483 | 0.7887383677353506 | 0.4484788755182392 | 8.969577510364783  |
| large_loss    | 0.7580294683085459 | 0.5251815431467007 | 0.4903935847501948 | 9.807871695003897  |

Every fraction reconciles exactly against the installed floor, confirming the rollout was graded under the current version.

Per-lane ceilings across all 71 submissions:

| Lane          | Best of 20 | Share  | First reached | Behaviour after         |
| ------------- | ---------- | ------ | ------------- | ----------------------- |
| reopening     | 20.000000  | 100.0% | `agent-18`  | solved, held            |
| report_timing | 13.113206  | 65.6%  | `agent-1`   | never improved again    |
| large_loss    | 9.807872   | 49.0%  | `agent-21`  | held                    |
| cash_timing   | 8.969578   | 44.8%  | `agent-23`  | still rising at timeout |
| severity      | 8.455987   | 42.3%  | `agent-8`   | never improved again    |

Against the controls: `empty` 0.0, `chain_ladder` 0.0, `copy_forward` 0.34482758620689774, `public_reference` 45.15699702394183, `opus-5-5` best 60.34664280395813, `oracle` 100.0.

Two observations point in opposite directions on duration. Report timing hit its final value on the first submission and never moved across 70 later ones; severity stopped at `agent-8`. Against that, reopening was only solved at `agent-18` and cash timing peaked at `agent-23`, the second-to-last agent submission, still rising when the clock ran out. One rollout cannot separate those readings. Coverage also confirms most zero-point lane results were missing output rather than wrong output: between 14 and 19 of the 71 submissions had coverage 0.0 on a given lane, and when coverage was 1.0 the lane almost always scored above zero.

---

# Part II — `e51c34a1` (`ethara/abs-auto-forward-flow-purchase`)

## Disposition

| Field                 | Value                                                                |
| --------------------- | -------------------------------------------------------------------- |
| Outcome               | `hold`                                                             |
| Reason                | `coverage-gap` (5 medium, 11 low)                                  |
| Retained              | no                                                                   |
| UUID                  | `e51c34a1-9895-583f-b626-71478e6ae6bd`                             |
| Canonical bundle hash | `b7c8cadfd1dc530a9301d09b51ea703ecaf2cb7ac972719ce8c8b8d1d449311a` |
| Sealed digest         | absent                                                               |
| Declared status       | absent (no `status` field)                                         |
| Lineage               | attempt 1; no predecessor recorded                                   |
| Seed run              | `forge-0shreyansh-20261028t131720z-b40481`                         |

## Task

| Field         | Value                                                                                                                                                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name          | `ethara/abs-auto-forward-flow-purchase` 1.0.0                                                                                                                                                                                           |
| Category      | professional-knowledge-work, finance, structured-credit, auto-loan-abs, portfolio-decision, credit-risk                                                                                                                                   |
| Goal          | Price and select participations in 104,845 offered auto-loan ABS loans across six trusts as of 30 June 2026 within a budget, a deployment floor and two concentration caps; forecast per-loan charge-off; and file a self-consistent memo |
| Reward        | Continuous 0 to 1; weighted mean of D1-outcome-capture 70, D2-outcome-skill 20, D3-craft-memo 10                                                                                                                                          |
| Null floor    | 0.0, recorded by a real empty run                                                                                                                                                                                                         |
| Harbor schema | 1.4                                                                                                                                                                                                                                       |
| Agent budget  | single turn, 43,200 s, no-network, user `1000:1000`                                                                                                                                                                                     |
| Verifier      | separate image, 1,800 s, no-network, static data judge that never imports the submission                                                                                                                                                  |

The statement lives in `environment/workspace/mandate/forward_flow_mandate.md` rather than `instruction.md`, which is nine lines and delegates to it. Published limits: commit at most 234,635,468.56 and at least 222,903,695.13 USD, at most 58,658,867.14 per pool, at most 46,927,093.71 to loans at 30 or more days past due, every amount checked to within 1.00 USD. Valuation runs over the withheld July, August and September 2026 tapes.

## Findings

| Lane          | Outcome | Minor gaps                                                                                                    |
| ------------- | ------- | ------------------------------------------------------------------------------------------------------------- |
| surface       | clean   | `README-ABSENT` (low), `GROUNDING-STUB` (low)                                                             |
| environment   | clean   | `G-ENV-SBOM` (medium), `BUILD-NET-FETCH` (low), `DEPS-UNUSED` (low)                                     |
| verifier      | clean   | `REWARDKIT-OPAQUE` (low)                                                                                    |
| statement     | clean   | none                                                                                                          |
| rubric        | clean   | `RUBRIC-HINDSIGHT-CEILING` (medium), `DIAG-NOLANE` (low)                                                  |
| contamination | clean   | `CON-PUBLIC-HOLDOUT` (medium), `G-CON-RECORD` (low), `GEN-REVIEW-PENDING` (low), `NODUP-NARROW` (low) |
| isolation     | clean   | none                                                                                                          |

The isolation lane is clean with triple-redundant structural evidence, and this is the bundle's strongest result. `tests/` is a sibling of `environment/`, not a child, so the agent build context cannot reach the answer key at all — Docker rejects any `COPY` outside the context root, making the leak structurally impossible rather than merely forbidden. `environment/.dockerignore` adds a deny-all followed by an allowlist of `requirements.txt` and `workspace/**`. `task.toml` sets `environment_mode = "separate"` with no shared mount beyond the one-way agent-to-host extraction of `/home/workspace/output`. A direct search of `environment/` for the answer key's distinctive anchors — `3313.11459773952`, `32609595.6`, `204531.9704849955` — returns zero hits.

The second isolation question was settled empirically rather than by assertion. The offer-pool parquet tapes were read with pyarrow and carry 44 Schedule AL fields plus `period`, with the period range strictly `2026-01` to `2026-06`; the graded July-to-September window is genuinely absent from the workspace. `offer_2026-06.csv` carries only snapshot fields — `pool,assetNumber,balance,days_past_due,delinquency_bucket,coupon,coupon_band,offer_price` — with no value or charge-off column. Cross-joining the offer file against the June tape for `sdart-2022-5` matched 23,522 of 23,522 offered loans and confirmed the mandate's eligibility filter holds for all of them: `zeroBalanceCode` 100 percent blank, `repossessedIndicator` 100 percent false, maximum `currentDelinquencyStatus` 119, and zero loans with positive `chargedoffPrincipalAmount`. No stale outcome leaks through. The six reference trusts are a different vintage from the six offer pools — `sdart-2022-4` against `sdart-2022-5`, `drive-2021-3` against `drive-2024-1`, and so on — so they are legitimate model-training signal, not the graded trusts' own answers.

The verifier lane is clean and notably stronger than a naive expected-answer judge. Comparison is never exact float equality on computed financials: `tests/test_output.py:118` defines `_close` as an absolute-difference test against `SLACK = TERMS["tolerance_usd"]`, a flat 1.00 USD on a roughly 235 million USD budget, and final per-criterion scores use `_cents()` at lines 23–24, a `Decimal(repr(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)`. The only exact `==` is on the integer `loans_bought` count at line 140, which is appropriate. `math.isfinite` guards at lines 29 and 141. `tests/expected.json` is not hand-typed — `solution/recompute.py` lines 315–324 generate it mechanically from `solution/grounding.yaml`, and the mandate and anchor blocks were verified byte-identical between the two.

Failure attribution is correctly split. `tests/test.sh:2` sets `set -euo pipefail` and line 4 `exec`s `rewardkit /tests --workspace /home/workspace --output /logs/verifier/reward.json`. A search of `tests/` and `solution/` for `|| true`, bare `except:` and `except Exception` returns zero matches. All three `except` clauses in `test_output.py` are typed and scoped only to parsing untrusted agent output — lines 87, 93 and 159. An infrastructure failure is not caught by any of them and propagates as a nonzero exit under strict mode, so agent mistakes yield a graceful 0.0 inside a written `reward.json` while harness crashes yield no reward file at all.

A stub submission cannot score. `_rows` returns `None` on a missing or wrong-header `purchases.csv`, and even a header-only file producing an empty book fails `_admissible` at lines 71–75, because the deployment-floor gate `222,903,695.13 - 1.00 <= 0.0` is false. All three criteria then return 0.0. This is independently corroborated by the provenance record's `empty_submission_validation` atom, which records a real `harbor run -a nop` at reward 0.0 with a result digest — a measured null floor, not an assertion.

The judge is a pure static data judge. No `import`, `exec`, `eval`, `subprocess` or `__import__` appears in `test_output.py` or `recompute.py`; it reads only the three output files via `csv.reader` and `json.loads`. `EXPECTED` loads once at module import. Grading is a deterministic pure function of the three files, invariant to stdout and stderr.

Environment hygiene is materially better than bundle 1. Both Dockerfiles pin `FROM ... python:3.12-slim@sha256:12316debb...` by digest and also pin the `docker/dockerfile:1.17` syntax directive by digest. `environment/requirements.txt` is a 304-line lock with every package `==`-pinned and full `--hash=sha256:` sets, installed at `environment/Dockerfile:8` with `--require-hashes --only-binary=:all:`, which hard-fails on any mismatch. Both images run `USER 1000:1000`, matching `task.toml` exactly, with `COPY --chown=1000:1000` keeping ownership consistent. No failure-swallowing pattern appears in either Dockerfile. `network_mode = "no-network"` is declared in all four relevant sections.

Contamination controls were actually executed rather than declared. `provenance.yaml` records four screening roots with paths and digests — exclusion-list, freeze-date-table, near-duplicate-index and source-attestation-trust-root — with `screening_measured_at: 2026-10-29T06:35:21Z` and `screening_expires_at: 2026-11-28T06:35:21Z`, still valid at this audit date. The near-duplicate atom passes on 15 comparisons at `max_similarity: 0.179856` against a review threshold of 0.1978 and a hard threshold of 0.2078, under `jaccard-5shingle-idabstract v1` with `floor_recall: 1.0`. The sanitization atom passes over the closure `instruction.md and environment/**`. Instruments are pinned throughout: `harbor: 0.25.0 at fdba28fc411e47e8765420a1a063b4918fce3def`, `rewardkit: 0.2.4` from a digest-named archive, `leak_gate: leakscan.py version 1`. The three FORGE canary slots are filled with real hashes in `TRUTH.md`, `provenance.yaml` and `policy.yaml` alike — directly unlike bundle 1, whose slots were zeroed. `sources` names every SEC EDGAR ABS-EE Exhibit 102 filing by accession, CIK, period, role, sha256 and URL across all twelve trusts.

## Coverage gaps

| Lane           | Outcome | Code                     | Severity |
| -------------- | ------- | ------------------------ | -------- |
| discrimination | gap     | `discrimination-unrun` | medium   |
| pilot          | gap     | `pilot-unsigned`       | medium   |

These lanes were not run in this audit. Each caps the bundle at HOLD and neither is a defect in the task.

## Minor gaps

| #  | Severity | Code                         | Gap                                                                                                                                              |
| -- | -------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1  | medium   | `discrimination-unrun`     | `discrimination_weight = 1.0` is declared, but no `solution/alternates/` exists and the eleven rejected routes are named only in prose       |
| 2  | medium   | `pilot-unsigned`           | Judge reached at a local `host.docker.internal:8080`, started and removed as a local container per submission; one run                         |
| 3  | medium   | `RUBRIC-HINDSIGHT-CEILING` | 90 of 100 reward weight is anchored to a hindsight optimum requiring the withheld tapes, so full credit is unattainable in principle             |
| 4  | medium   | `CON-PUBLIC-HOLDOUT`       | The graded holdout is real public SEC filings, yet `freeze_holdout` is marked `not_applicable` and no freeze-date check was run against them |
| 5  | medium   | `G-ENV-SBOM`               | No SBOM anywhere in the bundle                                                                                                                   |
| 6  | low      | `DIAG-NOLANE`              | The D1, D2 and D3 sub-scores are never persisted; only the blended scalar survives, so no lane-level diagnosis is possible                       |
| 7  | low      | `REWARDKIT-OPAQUE`         | The `rewardkit` aggregation is checksum-pinned but its source is not in-bundle and cannot be audited here                                      |
| 8  | low      | `GEN-REVIEW-PENDING`       | `generator.origin` reads "model-authored by the FORGE agent, human review pending"                                                             |
| 9  | low      | `G-CON-RECORD`             | `provenance.sig` is present while `source_attestation.status` reads `attestation-unavailable` with no signer identities                    |
| 10 | low      | `NODUP-NARROW`             | The near-duplicate screen compared against only five in-repo bundles                                                                             |
| 11 | low      | `PROBE-FLAT`               | 60 of 73 submissions scored exactly 0.422; the run timed out after 11 resumes and the recorded cost is a provable undercount                     |
| 12 | low      | `GROUNDING-STUB`           | `solution/grounding.yaml` is seven lines, against a full parameter block in the sibling bundle                                                 |
| 13 | low      | `BUILD-NET-FETCH`          | `tests/Dockerfile:10` fetches `rewardkit` from `codeload.github.com` at verifier build time                                                |
| 14 | low      | `DEPS-UNUSED`              | `tests/requirements.txt` carries `litellm`, `openai` and `boto3`, none of which the judge imports                                        |
| 15 | low      | `README-ABSENT`            | No bundle `README.md`; the uuid is absent from the repository reconcile tables                                                                 |
| 16 | low      | `NO-SELFTEST`              | The bundle ships no selftest or measurement tree, so its design predicates are unverified in-bundle                                              |

What the material gaps mean:

1. `discrimination-unrun` (medium): `task.toml` declares `discrimination_weight = 1.0`, the maximum, yet no `solution/alternates/` directory exists. `TRUTH.md` names eleven rejected routes — `K3-naive` an even slice of every offered loan, `K3-persist` highest coupons, `K3-bucket` ranked by bucket average value, plus `K4-over-budget`, `K4-under-floor`, `K4-pool-cap`, `K4-delinquent-cap`, `K4-unoffered`, `K4-duplicate`, `K4-constant-probability` and `K4-memo-off`. Naming them in prose is not shipping them as runnable alternates, so nothing demonstrates the verifier separates a skilled purchase from a plausible wrong one. The declared weight makes this gap heavier here than in bundle 1.
2. `pilot-unsigned` (medium): `run_config.json` records `judge_url: http://host.docker.internal:8080` and `api_base_url: http://host.docker.internal:9090`, and `run_instance.log` shows the judge started, stopped and removed as a local Docker container for every submission. Both submission channels are self-triggered inside the same sandbox session. No third-party attestation of any score exists, and `source_attestation.status` is `attestation-unavailable`.
3. `RUBRIC-HINDSIGHT-CEILING` (medium): the reference answer is pure hindsight by the bundle's own description. `TRUTH.md` describes `purchases.csv` as 16,932 participations forming "the linear-programme optimum on realized values within the budget, the deployment band and both caps, half a dollar inside each bound," and `chargeoff_probabilities.csv` as "1 for every offered loan charged off on the hidden tapes, 0 otherwise." D1 at weight 70 and D2 at weight 20 are both anchored there, so 90 of 100 weight requires information the agent is definitionally denied; only D3 at weight 10 is fully attainable by legitimate work.

   - The published anchors quantify the band: zero credit at a pro-rata value of 204,531.97 USD, full credit at a hindsight optimum of 32,609,595.62 USD, with credit proportional between and never below zero. So the scoring is a well-defined continuous band, not a broken all-or-nothing gate, and the recorded agent did score inside it.
   - This does not fire, because the design is declared in the mandate the agent reads and the floor is measured. But it is a materially different posture from bundle 1, whose oracle scores exactly 100 from public inputs alone. Here no attainable submission can approach 1.0, which means the reward scale's upper half carries no achievable signal and `reward_type = "continuous"` over 0 to 1 overstates the usable range. The empirical consequence is below: 0.429 best after twelve hours, with 82 percent of attempts at exactly 0.422.
   - Two reference pools, `drive-2024-1` and `blast-2024-1`, sit at 58,658,866.64 against a 58,658,867.14 cap — fifty cents inside. A reference answer tuned to half a dollar inside a binding constraint is correct under the stated rules but leaves no margin, and the whole reward zeroes on any cap breach.
4. `CON-PUBLIC-HOLDOUT` (medium): `freeze_holdout` carries `applicability: not_applicable` with the reason "original instance derived from no named public evaluation set; graded outcomes come from tapes filed 2026-08 to 2026-10." The narrow ground is defensible — this is not a named benchmark — but the holdout is nonetheless real public record. `provenance.yaml` itself lists eighteen hidden-outcome filings, the 2026-07, 2026-08 and 2026-09 ABS-EE Exhibit 102 periods for each of the six offer pools, every one with a live `sec.gov` URL and a sha256. A model whose training data postdates those filings could have memorised the outcomes that D1 and D2 grade against, and no freeze-date check was run against them despite a freeze-date-table root being registered among the screening roots. `network_mode = "no-network"` blocks live lookup at run time; it does nothing about memorisation. This is the single gap most specific to this bundle's design and the one an auditor should weigh hardest.
5. `G-ENV-SBOM` (medium): a bundle-wide search for `*sbom*`, `*spdx*` and `*cyclonedx*` returns nothing, for either image. This is the one gap both audited bundles share verbatim. Dependency pinning here is otherwise exemplary, which makes the omission easier to close than in bundle 1.
6. `DIAG-NOLANE` (low): every one of the 73 `report.json` files carries `total_tests: 0, passed: 0, failed: 0, errors: 0, test_details: []`, because this harness persists only the blended scalar. The D1, D2 and D3 sub-scores appear nowhere in the trajectory tree. Which criterion plateaued cannot be read off the record; it can only be bounded arithmetically. Since D1 holds weight 70, a perfect D2 and D3 would contribute 0.30, so the observed 0.429 implies D1 captured roughly 0.18 of its 0.70 at best — an inference from the weights, not a recorded field, and labelled as such.
7. `REWARDKIT-OPAQUE` (low): `tests/reward.toml` declares `aggregation = "weighted-mean"` and `tests/Dockerfile:10` vendors the `rewardkit` CLI from a checksum-pinned `harbor-framework/harbor` archive, but that source is not in the bundle. The bundle-local code shows correct infrastructure-versus-agent separation at the `test.sh` and `test_output.py` boundary, and the dependency is reproducible, so this is an evidence-scope gap rather than a defect.
8. `GEN-REVIEW-PENDING` (low): `provenance.yaml` records `generator.origin: "model-authored by the FORGE agent, human review pending"`. The generator that produced the panel, the answer key and the published anchors has not had a human review recorded.
9. `G-CON-RECORD` (low): `provenance.sig` exists while `source_attestation` reports `attestation_digests: "none"`, `signer_identities: "none"` and `status: "attestation-unavailable"`. This is the same contradiction bundle 1 carries, in a stronger record.
10. `NODUP-NARROW` (low): the near-duplicate atom records `screened_against: "in-repo prior bundles under samples/"` with `screened_count: 5`. The screen passed comfortably, but five bundles is a narrow corpus and the result does not speak to similarity against anything outside this repository.
11. `PROBE-FLAT` (low): 60 of 73 submissions scored exactly 0.422 and the whole run spanned only 0.387 to 0.429. The run ended `timed_out: true` after `resume_count: 11`, and the recorded cumulative cost of USD 14.676048600000009 covers eleven of twelve agent segments, so true spend is higher by an unrecorded amount.

## Difficulty evidence (author-side, not signed)

`claude-opus-5-5`, session `e5bf903a-c3b8-42b0-83a3-c96e86476c3b`, single turn, 43,200 s, judge on a local container, auto-eval interval 1,800 s, `max_submissions` 400.

| Probe                         | Submissions            | Best  | Passes |
| ----------------------------- | ---------------------- | ----- | ------ |
| 2026-10-30 `opus-5-5/run_1` | 73 (50 agent, 23 auto) | 0.429 | 0      |

Started `2026-10-30T01:07:05`. `best_pass_rate` is 0.0 on all 73. Best 0.429 at `agent-48`, submission `db4cd33ea7da`. Worst 0.387 at `agent-24`. No submission scored zero — every one was valid and landed between 0.387 and 0.429.

| Channel     | n  | Min   | Max   | Mean   | Zeros |
| ----------- | -- | ----- | ----- | ------ | ----- |
| `agent-N` | 50 | 0.387 | 0.429 | 0.4187 | 0     |
| `auto-N`  | 23 | 0.408 | 0.422 | 0.4205 | 0     |
| all         | 73 | 0.387 | 0.429 | 0.4193 | 0     |

Unlike bundle 1, both channels hit the same judge with the same scoring code and differ only in who triggered the call, so neither is independent of the other.

The progression is essentially flat. The agent opened at 0.408, reached 0.422 by `agent-9`, and stayed there: 60 of 73 submissions scored exactly 0.422, and the single best deviation improved the plateau by 0.007, a 1.6 percent relative gain, at the forty-eighth of fifty agent attempts. The last fourteen auto ticks are all locked at 0.422. `agent-49` and `agent-50`, the final two submissions, regressed to 0.422 and 0.415, so the run ended below its own best.

The run was infrastructure-disturbed but not infrastructure-broken. Runtime 43,199.378047943115 s with `timed_out: true`, killed 0.6 s short of the configured ceiling. `resume_count: 11`, meaning twelve agent-process segments, with durations 25,353.8, 1,016.4, 2,712.8, 2,090.2, 654.2, 710.4, 2,232.7, 1,332.7, 1,431.6, 1,340.9 and 1,083.5 s before a final roughly 3,240 s segment killed mid-task. No 401 and no crash traceback appears anywhere; `bridge.log` records five transient `upstream drop` warnings clustered between 11:30:24 and 11:54:18, retried and recovered, with submissions continuing normally afterwards. `install_output.txt` holds only a benign `npm warn EBADENGINE` for Node 20.18.0 against a `>=22.0.0` requirement.

Cost is a lower bound. `agent_output.txt` carries eleven `"type":"result"` events, one per cleanly exited segment, rising monotonically to `total_cost_usd: 14.676048600000009` with `outputTokens: 119850`, `thinkingTokens: 29051`, `cacheReadInputTokens: 51445963` and `cacheCreationInputTokens: 248415`. The twelfth segment was killed before emitting its own result, so true spend exceeds USD 14.676049 by an unrecorded amount. No other cost field exists anywhere in the trajectory.

Read against the published anchors, 0.429 places the agent inside the band but nowhere near its top, and the band's top is unattainable by construction. The flatness is the signal worth recording: twelve hours and fifty genuine attempts moved the score by 0.021 from the first submission, which is consistent with either a genuinely hard problem or an early-saturating one. One run cannot tell them apart, and the absent lane-level diagnostics remove the obvious way to find out.

---

## Cross-bundle findings

Five gaps are shared, and they indicate process rather than bundle-specific authoring.

| Code                     | Bundles | Severity | Note                                                                                                          |
| ------------------------ | ------- | -------- | ------------------------------------------------------------------------------------------------------------- |
| `discrimination-unrun` | both    | medium   | Neither ships `solution/alternates/`; bundle 2 declares `discrimination_weight = 1.0` while shipping none |
| `pilot-unsigned`       | both    | medium   | Both judges run locally at `host.docker.internal`; neither has a third-party attestation                    |
| `G-ENV-SBOM`           | both    | medium   | No SBOM in either bundle, for any image                                                                       |
| `G-CON-RECORD`         | both    | low      | Both ship a `provenance.sig` while the record itself reports unsigned or attestation-unavailable            |
| `README-ABSENT`        | both    | low      | Neither bundle has a `README.md`, and neither uuid appears in the repository reconcile tables               |

The repository reconcile page is behind by two bundles. It reports "Bundles 5 of 30" and lists five uuids, while six bundle directories plus `images/` are resident. Both audited bundles are missing from its Evidence status and Dataset structure tables.

The two bundles' strengths are complementary, and each is the other's remedy. Bundle 2 demonstrates the provenance posture bundle 1 lacks: filled canary slots, executed screening with registered roots and digests, a recorded null-floor run, hash-locked dependencies, digest-pinned bases and non-root users in both images. Bundle 1 demonstrates the verification posture bundle 2 lacks: an exact-endpoint control ladder with `oracle` at 100.0, a fifty-predicate selftest, and factorial independence measured to 1e-14. Neither bundle should be placed until it borrows the other's discipline.

## Collective escalations

- HOLD is not final for either bundle. Both stay where they are until their medium gaps close; neither needs a successor, because no lane fired.
- Do not use 60.3467 or 0.429 as client pass rates. Both are single author-side rollouts on locally hosted judges, and both runs timed out.
- Bundle 1's `G-RUB-POSTHOC` is the gap most likely to escalate there. The floors are arithmetically correct and self-disclosed, so they are not a scorer defect today. If a signed pilot shows the installed floors move an informed agent's total beyond the rubric lane's tolerance, or if the `ANCHOR-REPLAY` discrepancy resolves against the recorded cash and report metrics that two floors derive from, the rubric lane would fire and a successor would be owed. `ANCHOR-ARCHIVE-ABSENT` compounds it, because the calibration cannot be re-derived from bundle contents.
- Bundle 2's `CON-PUBLIC-HOLDOUT` is the gap most likely to escalate there. The hidden window is real public SEC record, already filed, with URLs and digests in the bundle. If a freeze-date check against those eighteen filings shows a graded model's training cutoff postdates them, the contamination lane would fire, the bundle would be retained, and a successor would be owed.
- Bundle 2's `RUBRIC-HINDSIGHT-CEILING` does not escalate on its own but caps interpretation permanently: no attainable submission approaches 1.0, so any reporting of this task's reward must state the achievable band rather than the nominal 0 to 1 scale.

## To clear the hold

### Both bundles

- Author three alternate solutions each under `solution/alternates/` and run the discrimination lane. For bundle 2 the eleven routes already named in `TRUTH.md` are the obvious candidates and only need shipping as runnable code.
- Run a signed pilot against an attested judge rather than a local container, on infrastructure that will not time out or drop mid-run, and record cost for the whole run.
- Commit SBOMs for every image in both bundles.
- Reconcile each `provenance.sig` against its record, so a present signature and an unsigned or attestation-unavailable status no longer contradict each other.
- Add a `README.md` to each bundle and regenerate the repository reconcile tables to include both uuids.

### `98ab6785` additionally

Medium, required before placement:

- Settle the floor provenance: re-derive the four floors from controls measured before any agent run, or record the post-hoc selection as an accepted policy with operator sign-off, since the manifest currently labels it "not independent difficulty evidence."
- Restore a usable band on cash timing and large loss, or record why a competent public-only method earning 0 and 1.41 of 20 there is intended.
- Pin the `apt-get` package versions.

Low, can follow placement:

- Rewrite `NOTES.md`, `RUNG_FEASIBILITY.md` and `task.toml` to describe the shipped digests and the shipped rollout, and rerun the selftest so its image assertion covers the resolved manifest rather than tag-only placeholders.
- Establish the cause of the 33.878 against 37.421 replay discrepancy without adjusting the scorer.
- Bring the `refine-runs/opus-5/` anchor archive into the bundle, or re-anchor on a record that is present.
- Pin both `FROM python:3.11-slim` lines by digest.
- Document or remove the agent image's passwordless sudo, and add a `USER` drop to the judge image.
- Give `grounding.yaml` either YAML content or a `.json` name.

### `e51c34a1` additionally

Medium, required before placement:

- Run the freeze-date check against the eighteen hidden-outcome EDGAR filings using the freeze-date-table root already registered in `provenance.yaml`, and either record `freeze_holdout` as a pass or state the graded models whose cutoffs precede 2026-08.
- Publish the achievable reward band alongside the nominal scale, or re-anchor D1 and D2 on an attainable public-information reference so the upper half of the scale carries signal.
- Clear `generator.origin` from "human review pending" to a reviewed state.

Low, can follow placement:

- Persist the D1, D2 and D3 sub-scores per submission so lane-level plateaus can be diagnosed without re-running `rewardkit` against a submission tarball.
- Vendor `rewardkit` into a pinned layer so the verifier build makes no network call, or document that `tests/Dockerfile:10` is a build-time checksum-pinned tooling fetch distinct from the runtime no-network guarantee.
- Drop `litellm`, `openai` and `boto3` from `tests/requirements.txt`, which the judge never imports.
- Widen the near-duplicate screen beyond five in-repo bundles.
- Expand `solution/grounding.yaml` past its seven-line stub, and add a selftest and measurement tree so the bundle's design predicates are verifiable in-bundle as they are in `98ab6785`.

## Flag legend

| Flag   | Meaning                                                               |
| ------ | --------------------------------------------------------------------- |
| fired  | The lane found a defect at this digest; retains the bundle            |
| gap    | The lane could not run or could not decide; caps at HOLD              |
| medium | A gap that must close before the bundle can be placed                 |
| low    | A gap that can close after placement                                  |
| clean  | The lane ran and found nothing                                        |
| hold   | Not final; the bundle waits for its gaps to close and is not retained |
