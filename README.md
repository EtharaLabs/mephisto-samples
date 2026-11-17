<p align="center"><img src="images/hero.svg" alt="Mephisto" width="720"></p>

# Mephisto: samples

<p align="center"><b>Five sample task bundles from Mephisto, a Harbor benchmark that measures whether an autonomous agent can reproduce a professional review desk's method from the desk's own ledgers.</b></p>

<p align="center"><a href="#summary"><img src="https://img.shields.io/badge/bundles-5-845EF7" alt="bundles: 5"></a> <a href="#summary"><img src="https://img.shields.io/badge/harbor_schema-1.4-845EF7" alt="harbor schema: 1.4"></a> <a href="#rollouts"><img src="https://img.shields.io/badge/mean_reward-0.5310-845EF7" alt="mean reward: 0.5310"></a></p>

<p align="center"><sub><a href="#abstract">Abstract</a> | <a href="#summary">Summary</a> | <a href="#tasks">Tasks</a> | <a href="#rollouts">Rollouts</a> | <a href="#coverage">Coverage</a> | <a href="#dataset-structure">Dataset structure</a> | <a href="#verification-and-quality-assurance">Verification and quality assurance</a> | <a href="#cite">Cite</a> | <a href="#license">License</a> | <a href="#contact">Contact</a></sub></p>

## Abstract

Mephisto is a benchmark of agentic tasks in [Harbor](https://github.com/laude-institute/harbor) format, built to measure method imitation rather than recall. It targets [EdgeBench](https://arxiv.org/abs/2607.05155) (arXiv:2607.05155). Each bundle hands the agent a finance operations desk's raw ledgers and asks it to reproduce the record that desk publishes for a set of queried entity-periods. Six named lanes are scored independently, and each lane carries a floor measured from a competent one-shot method, so reward accrues only where the agent beats that method rather than for merely emitting well-formed output.

Every bundle runs in an offline container, with `no-network` set for the agent, the environment, and the verifier alike. Each carries a private reference solution, 560 held-out truth rows the agent never sees, deterministic per-lane scoring with no LLM judge, and a bounded continuous reward from 0 to 1 aggregated as a weighted mean over the six lanes.

This repository holds the five-bundle sample. All five are back-office and middle-office review desks: receivables finance, transfer pricing, fund administration NAV oversight, trade finance documentary credit examination, and dealer floorplan finance. Every ledger is produced by a deterministic synthetic generator named in the bundle's own provenance, and every register covers 360 entities with 560 queried entity-periods, so no bundle rewards retrieval of a real-world source.

## Summary

| Property | Value |
| --- | --- |
| Bundles | 5 |
| Domain | Finance operations review (method imitation from desk ledgers) |
| Format | Harbor task, schema 1.4 |
| Platforms | linux/amd64, linux/arm64 |
| Scored lanes per bundle | 6 |
| Reward | `bounded_continuous`, 0 to 1, weighted mean over lanes |
| Agent timeout | 12 h per bundle |
| Data license | CC0-1.0 |
| Agent | Claude Code with `claude-opus-5-5` |
| Runs per bundle | 1 |
| Mean best reward | 0.5310 |

## Tasks

| Task | Desk | Objective | Entity |
| --- | --- | --- | --- |
| [`04fb6ba7`](04fb6ba7-d838-59da-b07d-6b683edd47a1/) | Receivables finance | Reproduce a supply-chain finance desk's monthly surveillance record across six competence-floored lanes: dilution reserve, collection profile, dispute flag, recovery tier, availability rank and loss reserve. | Obligor |
| [`0e08e615`](0e08e615-419f-5444-b3d7-5357f7c59733/) | Transfer pricing | Reproduce a multinational group's intercompany settlement review across six competence-floored lanes: adjustment magnitude, allocation key profile, challenge flag, method tier, review rank and uncertain tax reserve. | Entity pair |
| [`19dc92c2`](19dc92c2-7f44-5ee4-b4c6-5a09e38758e0/) | Fund administration | Reproduce a fund administrator's NAV oversight record across six competence-floored lanes: NAV break magnitude, fee accrual profile, restatement flag, pricing source tier, oversight rank and expense reserve. | Fund |
| [`2f2bb3bd`](2f2bb3bd-1f76-53b4-b9ab-3a11acfc300b/) | Trade finance | Reproduce a documentary credit desk's examination record across six competence-floored lanes: discrepancy count, discrepancy class profile, refusal flag, tenor tier, examiner priority rank and charge reserve. | Beneficiary |
| [`fc330da8`](fc330da8-c1f7-53fc-8c50-b5da77e9b985/) | Floorplan finance | Reproduce a dealer floorplan desk's monthly surveillance record across six competence-floored lanes: aging reserve, turn profile, sold-out-of-trust flag, variance tier, headroom rank and loss reserve. | Dealer |

## Rollouts

Each bundle was run once with Claude Code on `claude-opus-5-5` and scored by the bundle's own verifier. Every run reached the 12 hour agent timeout, and no run produced a passing round, so these rollouts record difficulty evidence rather than reference solutions. Rollouts are stored in each bundle's `rollouts/opus-5-5/`.

| Task | Best reward | Rounds | Best round | Agent submissions | Agent time |
| --- | ---: | ---: | --- | ---: | ---: |
| [`04fb6ba7-d838-59da-b07d-6b683edd47a1`](04fb6ba7-d838-59da-b07d-6b683edd47a1/rollouts/opus-5-5/) | 0.4578 | 782 | agent-634 | 639 | 12 h |
| [`0e08e615-419f-5444-b3d7-5357f7c59733`](0e08e615-419f-5444-b3d7-5357f7c59733/rollouts/opus-5-5/) | 0.6588 | 420 | agent-273 | 277 | 12 h |
| [`19dc92c2-7f44-5ee4-b4c6-5a09e38758e0`](19dc92c2-7f44-5ee4-b4c6-5a09e38758e0/rollouts/opus-5-5/) | 0.5022 | 980 | agent-835 | 837 | 12 h |
| [`2f2bb3bd-1f76-53b4-b9ab-3a11acfc300b`](2f2bb3bd-1f76-53b4-b9ab-3a11acfc300b/rollouts/opus-5-5/) | 0.5608 | 935 | agent-753 | 792 | 12 h |
| [`fc330da8-c1f7-53fc-8c50-b5da77e9b985`](fc330da8-c1f7-53fc-8c50-b5da77e9b985/rollouts/opus-5-5/) | 0.4753 | 785 | agent-757 | 762 | 12 h |
| **mean** | **0.5310** | **780** | | **661** | **12 h** |

Each rollout folder holds the run as the harness recorded it:

| Path | Contents |
| --- | --- |
| `agent_prompt.md` | Harness preamble and the bundle's instruction as the agent received it |
| `agent_output.txt` | Agent transcript for the whole run |
| `run_history.json`, `evolve_state.json` | Per-round history and harness state |
| `final_result.json` | Agent, model, round counts, runtime, and best score |
| `final_archive.tar.gz` | Workspace archive at the end of the run |
| `submissions/<round>/` | Per-round `report.json`, `test_output.txt`, `eval.sh`, `run_instance.log`, `allowed_files.txt`, and `submission.tar.gz` |

## Coverage

| Keyword | Bundles |
| --- | --- |
| finance | 5 |
| method-imitation | 5 |
| professional-knowledge-work | 5 |
| synthetic | 5 |
| portfolio-surveillance | 2 |
| dealer-lending | 1 |
| document-examination | 1 |
| documentary-credit | 1 |
| floorplan-finance | 1 |
| fund-administration | 1 |
| intercompany-settlement | 1 |
| inventory-finance | 1 |
| letter-of-credit | 1 |
| nav-oversight | 1 |
| receivables-finance | 1 |
| supply-chain-finance | 1 |
| trade-finance | 1 |
| transfer-pricing | 1 |

## Dataset structure

Each bundle is one Harbor task in a directory named by its content-derived uuid5, so the name doubles as an integrity check.

| Task | Keywords |
| --- | --- |
| [`04fb6ba7-d838-59da-b07d-6b683edd47a1`](04fb6ba7-d838-59da-b07d-6b683edd47a1/) | finance, method-imitation, portfolio-surveillance, professional-knowledge-work, receivables-finance, supply-chain-finance, synthetic |
| [`0e08e615-419f-5444-b3d7-5357f7c59733`](0e08e615-419f-5444-b3d7-5357f7c59733/) | finance, intercompany-settlement, method-imitation, professional-knowledge-work, synthetic, transfer-pricing |
| [`19dc92c2-7f44-5ee4-b4c6-5a09e38758e0`](19dc92c2-7f44-5ee4-b4c6-5a09e38758e0/) | finance, fund-administration, method-imitation, nav-oversight, professional-knowledge-work, synthetic |
| [`2f2bb3bd-1f76-53b4-b9ab-3a11acfc300b`](2f2bb3bd-1f76-53b4-b9ab-3a11acfc300b/) | document-examination, documentary-credit, finance, letter-of-credit, method-imitation, professional-knowledge-work, synthetic, trade-finance |
| [`fc330da8-c1f7-53fc-8c50-b5da77e9b985`](fc330da8-c1f7-53fc-8c50-b5da77e9b985/) | dealer-lending, finance, floorplan-finance, inventory-finance, method-imitation, portfolio-surveillance, professional-knowledge-work, synthetic |

```
<uuid>/
├── task.toml         runner manifest
├── instruction.md    objective the agent reads
├── environment/      offline sandbox image, with the desk's ledgers in workspace/
├── tests/            verifier and held-out truth, hidden from the agent
├── solution/         private reference solution and measured lane floors
└── rollouts/
    └── opus-5-5/     agent model
        ├── final_result.json, agent_output.txt, run_history.json
        └── submissions/<round>/
```

## Verification and quality assurance

The verifier travels with the bundle and never reaches the agent. `tests/hidden/truth.jsonl` holds 560 held-out rows in every bundle, `tests/scoring/` carries `eval.py`, `score.py` and a `scorer_manifest.json` naming the scored lanes, and `tests/reward.toml` declares a single weighted-mean reward over them.

Scoring is per lane rather than all-or-nothing, and every bundle uses the same six-lane shape: one profile, one flag, one tier, one cross-sectional rank, and two value lanes such as a reserve, magnitude or count.

Each lane carries a measured competence floor. `solution/measure_floors.py` fits a competent one-shot method per lane and records the result in `solution/floors.json`, and every manifest sets `null_floor = 0.0`, so a submission earns credit only where it beats that method.

The scorer is exercised against more than one implementation shape. `solution/checks/test_scorer.py` carries the scorer self-tests, and `solution/alternates/` holds rewrites of the same method: a class facade in all five bundles, split modules in four, and a renamed single module in three. A scorer that silently depended on the reference file layout would not survive them.

Data provenance is declared in `task.toml`: all five set `origin = "original"` and `source_kind = "synthetic"`, and name the deterministic generator and its inputs under `[upstream_provenance]`.

## Cite

```bibtex
@misc{mephisto2026,
  title        = {Mephisto: A Method-Imitation Benchmark for Professional Knowledge Work},
  author       = {{Ethara.AI}},
  year         = {2026}
}
```

## License

Released under the MIT License. © 2026 Ethara.AI.

## Contact

Mephisto is built by [Ethara.AI](https://github.com/Ethara-Ai).

Copyright (c) 2026 Green Rider Technology LLP (Ethara AI). All rights reserved.
