# C03 independent preparation specification

## Outcome and release policy

Prepare executable acceptance evidence for C03. This branch neither changes production behavior nor issues a checkpoint verdict. No push, merge, PR, release, authoritative experiment, or external write is authorized.

## Acceptance criteria

1. The producer enumerates every non-negative integer vector over `QB,RB,WR,TE,K,DST` whose sum equals the active bench budget. It evaluates a composition as a unit; it does not join six separately selected curves.
2. Every vector is checked against actual lineup eligibility. FLEX accepts RB/WR/TE; superflex accepts QB/RB/WR/TE; 2QB has two dedicated QB holes. Portfolio value includes starter bye/fragility coverage, contingency correlation, waiver replaceability, TE premium, bench depth, and IR policy.
3. Mandatory slices include 10/12/14 teams, 1QB/superflex/2QB, four/eight bench slots, TE premium/no premium, and IR/no IR. `t14-2qb-std-te0.5-b4-ir1` stays `unsupported` and blocked unless preregistered evidence independently clears every promotion threshold.
4. Canonical shape schema v2 or later has top-level `schema_version`, `canonical_source_hash`, and `rows`. Every row has an exact canonical `league_config_key`, `evidence_status` in `measured|interpolated|unsupported`, a budget-conserving composition, and soft marginal costs. No hard positional cap is an artifact contract field.
5. The canonical source hash is lowercase SHA-256 of canonical JSON source bytes defined by the producer manifest. A generated browser-safe TypeScript artifact embeds that exact hash and semantically identical rows. Generation/check mode fails on any byte or semantic drift.
6. Interpolated and unsupported rows never claim measured sample counts or measured provenance. Missing/malformed keys, hashes, statuses, compositions, or marginal costs return an explicit degraded result; fallback is a finite soft cost and never rejects a legal candidate solely for position count.
7. Prototype/gate runtime and peak memory are recorded. The intended frontend consumer performs lookup and finite arithmetic only—no simulation, filesystem, crypto, subprocess, or Node-only API in the browser path.

## Definition of done

- Preregistration is frozen before any real experiment.
- Synthetic tests cover every required modeling dimension and contrast complete-vector selection with the old independent-bound approach.
- Current unimplemented artifact requirements are strict expected failures, so an unexpected pass fails review and forces reconciliation.
- All preparation-owned positive tests and the synthetic gate pass deterministically.
