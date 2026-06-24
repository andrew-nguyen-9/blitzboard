# Architecture (v2)

> Supersedes `docs/archive/v1/ARCHITECTURE.md`. The **four interfaces are unchanged**; v2
> adds an auth/account layer, a precomputed data-delivery layer, and upgraded engine
> implementations behind the same contracts.

## One-paragraph mental model

A Python pipeline (GitHub Actions cron) pulls players (Sleeper), history (nflverse), and
league data (ESPN/Sleeper) into Supabase, computes **projections as distributions**, runs
them through **league scoring rules** to produce **player value** via a chosen **value
engine** (predictability-discounted VORP or Monte Carlo), and during the waiver window scores
**news sentiment** into a blended **trending** signal. The pipeline then **publishes
precomputed, compressed snapshots** of the value layer to a CDN-cached edge. The Next.js
frontend serves two planes: a **public read plane** (anon, RLS public-read + the snapshots)
and an **authenticated plane** (Auth.js sessions; per-user RLS rows; an encrypted
credential vault for ESPN/Sleeper). The frontend never computes value and never holds the
service-role key.

```
SOURCES        PIPELINE (Python cron)                 SUPABASE                 EDGE/CDN            FRONTEND (Next.js)
───────        ──────────────────────                 ────────                 ────────           ──────────────────
Sleeper ─┐     ingest_players                          players        ┐                            PUBLIC plane (anon)
nflverse ┼───► ingest_history  ─► Projector(dist) ───► projections    │   publish   players-       ├─ Home, Players,
ESPN ────┘     ingest_league       │                   player_value   ├─► snapshot ─► <profile>-    │  public Waivers/Trades
                                   ▼                    leagues        │   (brotli,    <engine>.bin  │
RSS+Reddit ──► sentiment_scorer ─► ValueEngine ───────► league_rules   │   CDN-cached) ──────────────┤
(waiver win)                       (VORP* | MonteCarlo) trending       ┘                            AUTH plane (Auth.js)
                                                        ── auth.users / accounts / user_leagues ──► ├─ My League, gated
                                                        ── credential_vault (encrypted) ──RLS────►  │  Waivers/Trades, Draft
```
`VORP*` = predictability-discounted VORP (v2.2). See `docs/modeling/`.

## Core abstractions (unchanged contracts)

1. **`LeagueRules`** — JSONB scoring + roster config; single source of truth. v2: one row
   *per user-league* (multi-tenant), importable from ESPN/Sleeper. (`docs/security/MULTI_LEAGUE.md`)
2. **`Projector`** — emits **distributions** `{mean, floor, ceiling, stdev, by_stat}` +, new
   in v2, a **predictability score** per player (drives the K/DEF discount).
3. **`ValueEngine`** — `value(players, rules) -> {value, vor, replacement, boom, bust, rank}`.
   v2 implementations: `VorpEngine` (now predictability-discounted, demand-derived
   replacement) and `MonteCarloEngine` (vectorized, shipped in v1 P7). Both batch-precomputed.
4. **`SentimentScorer`** — article → NFL-aware sentiment; VADER now, FinBERT later. Unchanged.

## What v2 adds to the architecture

- **Data-delivery layer** — the pipeline publishes compact, versioned, CDN-cached snapshots
  of the value layer so the frontend never paginates 1000+ rows out of PostgREST. See
  `DATA_TRANSFER.md`. (Fixes the 500-player cap.)
- **Auth/account plane** — Auth.js (Google + email/password) issues sessions; Supabase
  Postgres stores `accounts`, `user_leagues`, and an **encrypted `credential_vault`** for
  ESPN/Sleeper secrets; RLS isolates every row by `auth.uid()`. See `docs/security/`.
- **Two-plane data access** — public reads (player universe, public trending/trade-tester)
  vs. authenticated reads/writes (your leagues, your saved credentials). The gated tabs
  (League, your Waivers, your Trades) live on the auth plane; generic versions live public.

## Conventions (unchanged + v2)

- Server Components default; `"use client"` only for interactivity/animation.
- Public reads via `lib/queries.ts` (null-safe). **Authenticated** reads via
  `lib/queries.auth.ts` behind the session; mutations via server actions/route handlers that
  re-check authz server-side.
- Service-role key = pipeline only. Anon key = public reads (RLS). Session = per-user reads
  (RLS by `auth.uid()`). The browser never sees a privileged key.
- New tables: RLS enabled + explicit policies. Migrations timestamp-prefixed in `db/migrations/`.
