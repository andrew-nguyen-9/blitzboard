# Gameplan — one page

## What we're building
A pipeline-driven NFL fantasy war room: player intelligence + draft assistance (live &
offline) + waiver/trade optimization + real-time news-sentiment trending. **One league
first (mine, on ESPN), architected to open to anyone.** Spun off festival-analyzer infra.

## The spine (everything hangs off this)
1. **Data in** — Sleeper (player universe + trending), nflverse (history), ESPN (my league rules/rosters/draft), RSS+Reddit (news). All via the Python cron pipeline into Supabase.
2. **Compute** — `Projector` turns data into projections *as distributions*; `ValueEngine` (VORP **or** Monte Carlo, user toggle) turns projections × `LeagueRules` into player value; `SentimentScorer` (VADER→FinBERT) + Sleeper add/drop → blended `trending`.
3. **Data out** — Next.js reads it all (anon, read-only). The 7 tools are thin consumers of the value + trending layer. Frontend never writes.

## The seven tools
Homepage · Player Explorer · Draft Simulator (offline/bots) · **Draft Board (live ESPN-sync + offline manual)** · League Overview · Waiver Tool · Trade Optimizer.
Most are different views of the same value layer; the Draft Board is the centerpiece.

## Guiding constraints
- **Manual draft entry is the always-works default; ESPN live-sync is an accelerator on top** (ESPN's feed is the most fragile thing we touch — must degrade gracefully).
- **Build for me, schema for everyone** — no premature multi-tenant auth, but no corners painted.
- **Batch over live** — sentiment scores refresh every 30 min during the waiver window only; "real-time" = 30-min freshness, no live-inference infra.
- **Swap, don't rewrite** — Projector / ValueEngine / SentimentScorer / PickSource are interfaces, so consensus→homegrown, VADER→FinBERT, manual→live are drop-in swaps.
- **Ships with no keys** — app builds and renders empty states before backend exists (inherited pattern).

## Sequence (it's offseason — draft-first)
Foundation → Player Explorer → Draft tools → League Overview → Waiver+Sentiment → Trade → Homepage polish → Monte Carlo swap-in. Full detail in [ROADMAP.md](ROADMAP.md).

## Read next
[DECISIONS.md](DECISIONS.md) (the why) · [ARCHITECTURE.md](ARCHITECTURE.md) (the how) · [DESIGN.md](DESIGN.md) (the look) · [../db/schema.sql](../db/schema.sql) (the data).
