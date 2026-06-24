# v1.0.0 — Archived Planning Record

This folder is the **frozen v1.0.0 record**. Everything the project was before the v2
restructure lives here, unchanged, as the historical "why." It is not maintained — v2
supersedes it. Read it for context; do not edit it.

## What v1 was

A pipeline-driven NFL fantasy war room, built for one ESPN league ("Smores 2025",
superflex half-PPR), architected to open to anyone later. Next.js 15 + Supabase +
Python cron pipeline. Shipped P0–P7: foundation, Player Explorer, draft tools (manual +
Sleeper/ESPN sync), League Overview, Waiver+Sentiment, Trade Optimizer, creative
overhaul, and a vectorized Monte Carlo engine.

| File | What it captured |
|------|------------------|
| [GAMEPLAN.md](GAMEPLAN.md) | The one-page plan |
| [DECISIONS.md](DECISIONS.md) | Locked decisions D1–D9 (the "why") |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The four core interfaces + data flow |
| [DATA_SOURCES.md](DATA_SOURCES.md) | Sleeper / nflverse / ESPN / RSS+Reddit |
| [DESIGN.md](DESIGN.md) | "Broadcast Deck" art direction |
| [ROADMAP.md](ROADMAP.md) | P0–P7 phased build |
| [LEAGUE_RULES.md](LEAGUE_RULES.md) | Smores 2025 ruleset (superflex, distance-K, yardage-D/ST) |

## What carries forward into v2 (still load-bearing)

- The **four interfaces** — `LeagueRules`, `Projector` (distributions), `ValueEngine`
  (VORP / Monte Carlo), `SentimentScorer` — remain the spine.
- **Decisions D1–D9** remain in force except where a v2 ADR explicitly supersedes them.
  See [../../decisions/DECISIONS_V2.md](../../decisions/DECISIONS_V2.md).
- **LEAGUE_RULES.md** (superflex/OP-slot, distance-based K, yardage D/ST) is unchanged and
  still drives every value computation.

## What v2 changes (and where it's documented)

Homepage + Players revamp, scoring/value-engine upgrade (K/DEF), draft-logic redo with
backtesting, authenticated accounts + multi-league, public waivers/trades, security
hardening, and a new design system. See [../../phases/v2/PHASES_OVERVIEW.md](../../phases/v2/PHASES_OVERVIEW.md).
