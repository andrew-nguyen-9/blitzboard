# C02C-claude — canonical OP/SFLX slot-alias correction

## Identity and scope

- base: `15a501f443d7b62fe875758ab96c7198d96c8240` (reviewed C02B production head)
- review responded to: `C02B-codex.md` at review commit `9352aef` (verdict: BLOCK)
- supplemental evidence preserved by reviewer at `3ab7df6`; original reproduction
  commit `4407e4c`
- branch: `v6/bench-portfolio`; head is the commit containing this record
- scope: canonical shared-engine `OP`/`SFLX` eligibility and evaluator flexible-slot
  ordering only. No cost, budget, calibration, coefficient, C03, integration, merge,
  push, or unrelated behavior change.

The production worktree was clean at the required base before work. No lock or
active-process indicator showed another producer operating in `.worktrees/v6-prod`.

## Append-only preregistration

`waiver-realism-v5.json` was committed alone at
`73aaa3bc407b49b79de037901eb265d6fb96929a` before any behavior edit. Its SHA-256 is
`9ee1febe2a156d2c95a9f7bca3408937fa914810a7efb978f809f531ba8b4915`.

V5 freezes the shared canonical table:

- dedicated QB/RB/WR/TE/K/DST slots accept only their nominal position;
- FLEX accepts RB/WR/TE;
- SUPERFLEX, canonical ESPN OP, and SFLX are exact aliases accepting QB/RB/WR/TE;
- K/DST are rejected by every flexible offensive slot;
- all dedicated slots fill before flexible slots and aliases.

Waiver-realism v1-v4 are byte-preserved.

## Production correction

The shared `value.mcts.slot_positions` resolver now maps both `OP` and `SFLX` to
the existing SUPERFLEX eligibility set. This fixes every consumer of the shared
resolver (including the season evaluator, policy, CLI, and RL paths) without a
waiver-only branch.

The older CP-SAT roster-solver predicate now recognizes the same alias set. The
season evaluator's deterministic `_SLOT_ORDER` lists OP and SFLX with FLEX and
SUPERFLEX after every dedicated position, so flexible slots continue to absorb
only remaining bodies.

## Tests

Production coverage proves:

- each of QB/RB/WR/TE is accepted identically by SUPERFLEX, OP, and SFLX;
- K/DST are rejected identically by all three;
- dedicated QB fills before each flexible alias;
- the shared resolver and roster solver expose the same alias semantics.

The supplemental OP test ran unchanged from the reproduction worktree against
C02C production code and passed. Both earlier reviewer suites also ran unchanged.

## Verification

- unchanged supplemental + primary + remote reviewer suites: **10 passed**
- focused production waiver/MCTS/roster-solver suites: **69 passed**
- Ruff over `blitz_engine` and `tests`: clean
- full engine suite: **4165 passed, 1 skipped** in 367.78 seconds
- pipeline suite: **157 passed** in 8.46 seconds
- `git diff --check`: clean

The first sandboxed engine run produced **4164 passed, 1 failed, 1 skipped** only
because the golden-draft test's tsx process was denied permission to create its
local IPC socket. The identical full suite rerun with local IPC permission produced
the clean result above. Pipeline required the same local IPC permission and passed.

## Preservation

Git blob comparisons against `15a501f` confirm that waiver manifests v1-v4,
`C02-claude.md`, `C02A-claude.md`, `C02B-claude.md`, and all prior calibration
inputs/results are unchanged. No player-value coefficient, threshold disposition,
waiver cost, move allowance, counter, or season-cap rule changed.

## Stop

Stopping for independent C02C re-review. No integration, C03 production, push,
merge, or PR was performed.
