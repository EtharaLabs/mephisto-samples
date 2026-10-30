# Operator handoff: unsealed, hardened five-method draft; new pilot required

## New scoring version: baseline-anchored lane floors

This is a NEW, STRICTER BAR, not merely an extension of reopening's rationale. Reopening's unchanged 1/3 floor removes credit for a degenerate all-positive guess at 20% prevalence. Chain-ladder and copy-forward are legitimate actuarial methods. Zero severity, zero mass and constant ranking already correctly earned zero under the old formulas; the agent's prior positive credit was earned. The new rule moves from "beat nothing" to "beat a named competent reference method", retaining raw metrics, five equal weights, coverage placement and every target. No baseline, reference, generator or data is weakened or perturbed.

Full-precision floors from the pre-change measured summary are severity 0.8635424166399702, reporting 0.784706166733507, cash 0.7887383677353506 (all chain_ladder), and large loss 0.5251815431467007 (copy_forward). In particular cash is not 0.788740. These are the best textbook-control metrics in those lanes, not optimized thresholds chosen to land the agent just below 0.50. Nevertheless the selection of this scoring policy occurred AFTER seeing the Opus plateau and the operator's score goal, and is post-hoc calibration.

The public instruction publishes the rescaling formula, the named baseline for each lane, coverage handling, and the zero-credit consequence of matching or underperforming the baseline. The four numeric calibration values are withheld to avoid publishing private evaluation aggregates; reopening's already-public 1/3 remains. The judge's metric/points feedback can reveal a floor algebraically for a positive-credit submission, so this is not a secrecy guarantee. No per-record target or private method recipe is disclosed.

The recorded rv2 agent-45 judge report has score 76.3475107155616 under its original rules; its report and cash coverage are 0.93 and 0.96, already incorporated in the distribution metrics. Do not multiply that coverage a second time. The trajectory shows an initial 46.18 score, later lane improvements and the documented long plateau; the run README also records an approximately 85-minute authentication outage. Rescaling the supplied rounded metrics gives 33.878439126442636/100. This is honest ONLY as retrospective excess-over-baseline credit, not as the score the agent earned under the rules it saw, a newly demonstrated failure, or proof that a new informed agent will remain below 0.50. Cash's zero new credit means it did not beat chain-ladder, not that its forecast had no skill. A new disclosed-rule pilot is required; no Docker or sforge was run here.

Important reproduction discrepancy: the separate local `python3 -B solution/anchor_study.py measure --archive ...` execution scored the archived agent-45 JSON at 37.42119487625333/100. Reporting metric/coverage were 0.929028708013897/0.97 rather than the recorded judge's 0.8908915183617553/0.93; cash metric/coverage were 0.7259982873483335/0.92 rather than 0.7581878550843415/0.96. Severity, reopening and large-loss metrics matched the recorded report. The archive SHA-256 and full result are retained in `anchors.json`. Do not describe 33.88 as an exact archive replay: it is a calculation from the recorded metrics. The coverage discrepancy's cause has not been established; runtime or artifact differences require separate investigation, not a silent adjustment of the scorer. The successful selftest ran under Python 3.14.3, and was not rerun after success.

Strict empty < copy_forward < chain_ladder < public_reference < oracle is no longer meaningful: chain-ladder anchors three lanes exactly, has F1 zero (line-constant hazards tie at percentile 0.5, below 0.8), and large-loss correlation below the copy-forward anchor. Copy-forward retains a small reopening excess. Replace that ordering with exact endpoints, every non-reference control below public_reference below oracle, all floors strictly below one, and a named record requiring each textbook baseline to earn less than 1 point of 100 (approximately zero, not exactly zero). Independence, all factorial/additivity/headroom checks and nonzero exit on design failure remain mandatory. Do not restore ordering by weakening controls or changing weights.

`measurements/before_anchors.json` preserves original scorer/manifest/instruction, raw baseline metrics and protected hashes; `anchor_study.py` checks the exact three permitted scorer-line changes and protects all panel, target, generator, solver and transport bytes. `measurements/anchors.json` holds the rounded-input calculation and frozen agent-45 replay. Exact version diffs are `measurements/score.py.anchors.diff`, `scorer_manifest.json.anchors.diff`, and `instruction.md.anchors.diff`. Older hardening/frozen-replay measurements describe earlier scoring versions, not the new bar.

Current method/scoring documentation: `TRUTH.md`, `RUNG_FEASIBILITY.md`, and
`../instruction.md`. Current numeric evidence: `measurements/summary.json`,
`measurements/rung_study.json`, `measurements/selftest.txt`. Previous rejection
evidence is explicitly archived; it does not describe current scoring.
The original five-method version has recorded Opus evidence in
`refine-runs/opus-5/` outside this draft. This hardening has local author-side
measurements and frozen-checkpoint replay only, not a new agent pilot.
See `measurements/before_hardening.json`, `hardening.json`, `frozen_replay.json`
and the exact public-spec diff in `measurements/instruction.diff`.

All authored changes stay inside this draft. No Trinity gates, Docker, sforge,
mint, seal, commit or push. Placeholder image tags remain unresolved; single turn,
43200-second agent timeout, no compose and no steps. Images and real harness
transport remain operator responsibilities and are not locally certified.

## Exact image COPY lists

Work image ONLY (build context: `environment/`):
```dockerfile
COPY --chown=agent:agent attachments/train.jsonl attachments/queries.jsonl /workspace/data/
```

Judge image ONLY:
```dockerfile
COPY tests/test.sh /tests/test.sh
COPY tests/scoring/entrypoint.py /tests/scoring/entrypoint.py
COPY tests/scoring/eval_script.py /tests/scoring/eval_script.py
COPY tests/scoring/score.py /tests/scoring/score.py
COPY tests/scoring/scorer_manifest.json /tests/scoring/scorer_manifest.json
COPY tests/hidden_test_data/outcomes.jsonl /tests/hidden_test_data/outcomes.jsonl
```

Both need stdlib Python only and no network. Working directory `/workspace`;
disable bytecode. Judge creates `/logs/verifier`, runs `/bin/sh /tests/test.sh`,
and writes bare 0–100 `reward.txt` plus `reward.json` and structured stdout markers.
It uses isolated Python and never imports or executes submitted source.
No full-draft COPY, host draft mount, private solution, archived report, generator
configuration or judge layer may enter the normal work image.

Only for an oracle run inject `solution/solve.sh` and self-contained
`solution/reserving_reference.py` into `/solution`, never normal-agent storage.
Run `/bin/sh /solution/solve.sh`; it emits all three declared submission artifacts.
No additional private helper needs to be copied for the oracle.

## Reproduction

From this draft directory:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run --quiet --no-project --with pyyaml==6.0.3 python solution/selftest.py
```

For the public reference CLI, pass `--data-dir environment/attachments` instead of the pre-move `environment` example in its byte-protected docstring. Historical measurement snapshots retain their original path labels; `anchor_study.py` resolves the two relocated datasets and checks their original hashes without rewriting the evidence.

The test regenerates twice and checks byte idempotence and protected noncash hashes,
then runs oracle/baseline scripts and the isolated judge CLI in an in-draft temp
directory. This checks the same scoring executable as `test.sh`, not the literal
container filesystem. `selftest.txt` records stdout including interpreter version.
Design predicates run last and deliberately cause nonzero exit on rejection.
PyYAML 6.0.3 is validation-only; generation and grading require stdlib.

The five predictive weights are 20 each, with no bonuses or accounting padding.
Self-reported record count remains informational. Report the measured ladder
without claiming a target score or 12-hour duration. The public method description
uses aggregate tail proxies and average primary severity, not unavailable
individual large-loss labels or total ultimate-loss dollars.

The earlier hardening preserved quantities, schema, metrics, weights and anchors, but
withholds construction recipes. Reopening prose, process and metric are unchanged.
The retained data change is a settlement-only exposure/workload interaction; its
parameters and rationale are private in `TRUTH.md`. Do not copy this note, any
measurement, or the pre-edit specification snapshot into the work image.
