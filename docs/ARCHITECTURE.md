# Architecture

## The one-paragraph mental model

A Python pipeline (GitHub Actions cron) pulls players (Sleeper), history (nflverse),
and league data (ESPN) into Supabase. It computes **projections** (as distributions),
runs them through the user's **league scoring rules** to produce **player value** via one
of two interchangeable **value engines** (VORP or Monte Carlo), and during the waiver
window it scores **news sentiment** to produce a blended **trending** signal. The Next.js
frontend reads everything (anon, read-only) and presents seven tools — all of which are
thin consumers of the same value + trending data. Nothing in the frontend writes to the DB.

```
SOURCES            PIPELINE (Python, cron)              SUPABASE            FRONTEND (Next.js)
─────────          ───────────────────────             ────────            ──────────────────
Sleeper    ─┐      ingest_players                       players       ┐
nflverse   ─┼────► ingest_history     ──► Projector ──► projections   │
ESPN       ─┘      ingest_league           (dist.)      leagues       ├──► anon read ──► 7 tools
                                                         league_rules  │     (Player Explorer,
RSS+Reddit ──────► sentiment_scorer ──┐                  player_value  │      Draft, Waiver,
(waiver window)    (VADER→FinBERT)    ├─► trending ────► trending      │      Trade, Overview,
Sleeper trending ─────────────────────┘                  news_articles ┘      Simulator, Home)
                   value_engine (VORP | MonteCarlo) ──► player_value
```

## Core abstractions (the whole design hinges on these four interfaces)

### 1. `LeagueRules` — single source of truth for scoring
A JSONB config: scoring weights (pass/rush/rec yds, TDs, PPR value, bonuses), roster slots
(QB/RB/WR/TE/FLEX/K/DEF/bench), league size, waiver type. **Everything downstream reads
this.** v1 = my league hardcoded; later = per-user editable row. Drives projections→points
conversion for every tool.

### 2. `Projector` — emits projections as *distributions*
```
project(player, season, week?) -> { mean, floor, ceiling, stdev, by_stat: {...} }
```
Implementations: `ConsensusProjector` (borrowed/ADP-derived) and `HomegrownProjector`
(nflverse regression). **Must emit distribution, not a point** — Monte Carlo depends on it.

### 3. `ValueEngine` — projections + rules → player value
```
value(players, league_rules) -> { player_id: { value, vor, replacement, boom, bust, rank } }
```
- `VorpEngine` — deterministic value-over-replacement-baseline.
- `MonteCarloEngine` — simulates N drafts/seasons → expected value + boom/bust range.

Both precomputed in the pipeline, cached in `player_value` keyed by `(engine, scoring_profile)`.
UI toggle just selects which cached set to read. **Draft / Trade / Waiver tools are all
thin consumers of this** — they never compute value themselves.

### 4. `SentimentScorer` — article text → NFL-aware sentiment
```
score(article) -> { player_id, sentiment: -1..1, injury_flag, opportunity_flag, summary }
```
- v1 `VaderScorer` (NFL-tuned lexicon, runs in the Action).
- later `FinbertScorer` (fine-tuned, HF endpoint).
Same interface → drop-in swap. Output blends with Sleeper add/drop deltas → `trending`.

## Pick-input adapters (draft tool)
The draft board is one component fed by a `PickSource`:
- `EspnLiveSource` — polls ESPN draft feed (best-effort, fragile).
- `SleeperLiveSource` — polls Sleeper draft API (reliable reference path).
- `ManualSource` — user taps picks (in-person board; also the universal fallback).
Feed stall → automatically fall back to `ManualSource` on the same board.

## Pipeline scripts (mirror festival-analyzer conventions)
All accept `--league`/`--season`; tenacity retries; rich console; dotenv secrets; idempotent upserts.

| Script | Source → Table |
|--------|----------------|
| `player_ingest.py` | Sleeper → `players`, `trending_raw` |
| `history_ingest.py` | nflverse → `player_stats_history` |
| `projector.py` | history/consensus → `projections` |
| `value_engine.py` | projections × rules → `player_value` (per engine) |
| `league_sync.py` | ESPN → `leagues`, `rosters`, `league_rules` |
| `news_sentiment.py` | RSS+Reddit → `news_articles`, `trending` (waiver-window cron) |

## Conventions inherited from festival-analyzer
- Frontend: Server Components by default; `"use client"` only for interactivity.
- All Supabase queries in `lib/queries.ts`; client is null-safe (offline mode renders empty states).
- Service-role key = pipeline only; anon key = frontend public reads, enforced by RLS.
- New tables: RLS enabled + public-read policy. Migrations in `db/migrations/` timestamp-prefixed.
- Theme accent derived at runtime (here: league/team accent color, mirroring festival `accent_color`).
