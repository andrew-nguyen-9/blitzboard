# v2 Phases — Overview

Dependency-ordered. Each phase opens a branch, runs its segments (sub-branches), and finishes
with the 8-step ritual (`docs/workflow/GIT_WORKFLOW.md`). Versioning: `v[phase].[segment].[task]`.

| Phase | Branch | Name | Requirements | Status |
|-------|--------|------|--------------|--------|
| [v2.0](../../archive/v2/v2.0-foundation.md) | `v2` (+ `v2.0-*`) | Foundation & De-Andrew-ification | #8, workflow, tokens, a11y/motion scaffold | **Shipped (v2.0.0)** |
| [v2.1](../../archive/v2/v2.1-design-homepage.md) | `v2.1-*` | Design System & Homepage revamp | #1 | **Shipped (v2.1.0)** |
| [v2.2](../../archive/v2/v2.2-scoring.md) | `v2.2-*` | Scoring & Value-Engine upgrade | #3 | **Shipped (v2.2.0)** |
| [v2.3](../../archive/v2/v2.3-player-data.md) | `v2.3-*` | Player Data Layer & Players tab | #2 | **Shipped (v2.3.0)** |
| [v2.4](v2.4-draft-logic.md) | `v2.4-*` | Draft Logic redo + Backtesting | #4 | Planned |
| [v2.5](v2.5-auth-security.md) | `v2.5-*` | Auth, Accounts & Security | #5, #7, #9 | Planned |
| [v2.6](v2.6-gated-public-tabs.md) | `v2.6-*` | Gated + Public League/Waivers/Trades | #5, #6 | Planned |
| [v2.7](v2.7-optimization-launch.md) | `v2.7-*` | Optimization & Launch hardening | #7 | Planned |

## Why this order

- **Scoring (v2.2) before Players (v2.3) and Draft (v2.4)** — everything reads the value layer,
  so fix value first.
- **Player data layer (v2.3) before Draft (v2.4)** — the draft board consumes the full,
  efficiently-delivered universe.
- **Auth/Security (v2.5) before the gated tabs (v2.6)** — the secure account + multi-league
  framework must exist before features sit on top of it.
- **Foundation (v2.0) first** — workflow, tokens, a11y/motion scaffolding, and removing
  Andrew-ification unblock and de-risk everything after.
- **Hardening (v2.7) last** — verify the whole surface (perf budgets, threat model) before launch.

## Cross-cutting (applies to every phase)

Design guideline + accessibility + performance budgets + reduced-motion + RLS-on-new-tables +
idempotent pipeline are **acceptance criteria in every segment** (`docs/workflow/DEFINITION_OF_DONE.md`),
not separate phases.

## Tags

Finishing a phase tags `v2.<phase>.0` and cuts a GitHub Release. Patches bump the third digit.
