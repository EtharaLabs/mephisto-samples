<p align="center"><img src="images/hero.svg" alt="Mephisto" width="720"></p>

# Mephisto: samples

<p align="center"><b>The samples lane: 5 of 30 Harbor task bundles.</b></p>

<p align="center"><a href="#summary"><img src="https://img.shields.io/badge/bundles-5_of_30-845EF7" alt="bundles: 5 of 30"></a> <a href="#evidence-status"><img src="https://img.shields.io/badge/sealed-0-845EF7" alt="sealed: 0"></a> <a href="#difficulty-tiers"><img src="https://img.shields.io/badge/difficulty-measured-845EF7" alt="difficulty: measured"></a></p>

<p align="center"><sub><a href="#abstract">Abstract</a> | <a href="#summary">Summary</a> | <a href="#difficulty-tiers">Difficulty tiers</a> | <a href="#evidence-status">Evidence status</a> | <a href="#coverage">Coverage</a> | <a href="#dataset-structure">Dataset structure</a> | <a href="#verification-and-quality-assurance">Verification and quality assurance</a> | <a href="#reproduction">Reproduction</a> | <a href="#cite">Cite</a> | <a href="#license">License</a> | <a href="#contact">Contact</a></sub></p>

## Abstract

The curated lane of this corpus: at most 30 Harbor task bundles, every anchor seated first and every other bundle in seal order. Bundles past that ceiling live in `delivery/`.

Each bundle is one Harbor task in a directory named by its content-derived uuid5, so the name doubles as an integrity check. This page is rendered from the resident bundles on every reconcile; a value a bundle does not carry reads `absent`, and the page never fills one in.

## Summary

| Property | Value |
| --- | --- |
| Bundles | 5 of 30 |
| Sealed | 0 of 5 |
| Registrations | unregistered (5) |
| Audit verdicts | none (5) |
| Harbor schema | 1.4 (4), absent (1) |

## Difficulty tiers

Difficulty is measured by the signed pilot alone and never declared in a bundle, so this page states no tier a bundle claims.

## Evidence status

The verdict is the audit outcome recorded at the sealed digest, and `none` means no verdict has landed for that digest yet. Only an authoring run removes a bundle from this lane, so removal waits for the next one.

| uuid | Verdict | Sealed digest | Stream |
| --- | --- | --- | --- |
| 5cb28005-2b9a-5520-b4f8-de58beb5640d | none | absent | none |
| 60cab9e2-ae65-5e56-b113-0b1d40e33558 | none | absent | none |
| 9c463536-e514-5a50-9ff6-81ad513bae32 | none | absent | none |
| d3cd6658-d997-5f26-89e3-97e5443046b4 | none | absent | none |
| e5d63160-7e3a-5d55-bab1-a887c9e97be3 | none | absent | none |

## Coverage

| Keyword | Bundles |
| --- | --- |
| finance | 5 |
| professional-knowledge-work | 5 |
| sec-xbrl-fundamental-panel | 2 |
| bank-regulatory-capital | 1 |
| capital-structure-trajectory | 1 |
| cross-sectional-momentum | 1 |
| cross-sectional-panel-forecasting | 1 |
| earnings-cycle-adaptive | 1 |
| fed-policy-phase-labeling | 1 |
| fomc-cadence-adaptive | 1 |
| funding-condition-adaptive | 1 |
| leverage-projection-book | 1 |
| macro-regime-adaptive | 1 |
| rate-cycle-adaptive | 1 |
| rates-positioning-book | 1 |
| short-end-cash-allocation | 1 |
| treasury-bill-liquidity | 1 |

## Dataset structure

| Bundle | Task | Keywords | Registration | Sealed at | Tier |
| --- | --- | --- | --- | --- | --- |
| [`5cb28005-2b9a-5520-b4f8-de58beb5640d`](5cb28005-2b9a-5520-b4f8-de58beb5640d/) | `edgebench/sec_fundamental_momentum_calibration` | cross-sectional-momentum, earnings-cycle-adaptive, finance, professional-knowledge-work, sec-xbrl-fundamental-panel | unregistered | unsealed | - |
| [`60cab9e2-ae65-5e56-b113-0b1d40e33558`](60cab9e2-ae65-5e56-b113-0b1d40e33558/) | `edgebench/fed_funds_regime_positioning_book` | fed-policy-phase-labeling, finance, fomc-cadence-adaptive, professional-knowledge-work, rates-positioning-book | unregistered | unsealed | - |
| [`9c463536-e514-5a50-9ff6-81ad513bae32`](9c463536-e514-5a50-9ff6-81ad513bae32/) | `edgebench/treasury_liquidity_provisioning_book` | finance, funding-condition-adaptive, professional-knowledge-work, short-end-cash-allocation, treasury-bill-liquidity | unregistered | unsealed | - |
| [`d3cd6658-d997-5f26-89e3-97e5443046b4`](d3cd6658-d997-5f26-89e3-97e5443046b4/) | `edgebench/sec_leverage_trajectory_projection_book` | capital-structure-trajectory, finance, leverage-projection-book, professional-knowledge-work, rate-cycle-adaptive, sec-xbrl-fundamental-panel | unregistered | unsealed | - |
| [`e5d63160-7e3a-5d55-bab1-a887c9e97be3`](e5d63160-7e3a-5d55-bab1-a887c9e97be3/) | `edgebench/fdic_bank_capital_projection_book` | bank-regulatory-capital, cross-sectional-panel-forecasting, finance, macro-regime-adaptive, professional-knowledge-work | unregistered | unsealed | - |

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#131a33","primaryTextColor":"#e8ecff","primaryBorderColor":"#845EF7","lineColor":"#22d3ee","fontFamily":"monospace"}}}%%
flowchart LR
    bundle["&lt;uuid&gt;/"]
    bundle --> n0["task.toml<br/>runner manifest"]
    bundle --> n1["instruction.md<br/>objective the agent reads"]
    bundle --> n2["environment/<br/>agent sandbox image"]
    bundle --> n3["tests/<br/>verifier, hidden from the agent"]
    bundle --> n4["solution/<br/>private oracle"]
    bundle --> n5["README.md"]
    bundle --> n6["trajectory/"]
```

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#131a33","primaryTextColor":"#e8ecff","primaryBorderColor":"#845EF7","lineColor":"#22d3ee","fontFamily":"monospace"}}}%%
flowchart LR
    staging["staging/"]
    staging --> samples["samples/<br/>5 of 30"]
    samples --> delivery["delivery/<br/>0 of 10000"]
    delivery --> stock["stock/<br/>0 of 10000"]
```

## Verification and quality assurance

Each bundle's signed provenance carrier holds its screening roots, screening instant, and absolute expiry. Placement moves that carrier into the private derivation set, which this page never reads, so reconcile lists no root it cannot verify here.

## Reproduction

Each bundle directory is a complete Harbor task: `task.toml` is the runner manifest, `instruction.md` the objective, `environment/` the sandbox image, and `tests/` the verifier. Point a Harbor runner at one bundle directory to reproduce it; `solution/` stays private.

## Cite

```bibtex
@misc{mephistosamples,
  title = {Mephisto: samples}
}
```

## License

Released under the [MIT License](LICENSE). © 2026 Ethara.AI.

## Contact

[Ethara AI on GitHub](https://github.com/Ethara-Ai), [SECURITY.md](SECURITY.md) for a private report, and [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution route.
