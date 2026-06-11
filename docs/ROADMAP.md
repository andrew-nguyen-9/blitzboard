# Roadmap

Draft-first ordering (it's **June 2026, offseason** — draft tools matter Aug/Sept,
waiver/trade matter Sept+). Each phase ships something usable. Unbuilt sections render
graceful "coming soon" empty states.

```
Jun ───────── Jul ───────── Aug ───────── Sep ───────── Oct+
P0 Foundation
   P1 Player Explorer
        P2 Draft tools ████ (must be solid by late Aug)
              P3 League Overview
                    P4 Waiver + Sentiment ████ (season start)
                          P5 Trade Optimizer
   P6 Homepage shell early ─────────────────► polish last
                                P7 Monte Carlo swap-in
```

### P0 — Foundation *(unblocks everything; no UI value yet)*
- Repo scaffold off festival-analyzer (Next.js 15 + Supabase + pipeline skeleton).
- `db/schema.sql`: players, history, projections, player_value, leagues, league_rules, news, trending.
- `LeagueRules` config (my league seeded) + `Projector` + `ValueEngine` interfaces.
- `player_ingest.py` (Sleeper) + `history_ingest.py` (nflverse). `.env.example` with all placeholder keys.

### P1 — Player Explorer ✅ *(proves the data spine end-to-end)*
- ✅ Searchable/sortable/filterable player DB with VORP values (PlayerTable).
- ✅ Instrument-style player **detail pages** (team logo, value dial, distribution, history sparkline).
- ✅ Real projectors: ensemble (heuristic + regression + consensus) for offense; dedicated
  KickerProjector / DefenseProjector for K & D/ST; GSIS id-mapping for history join.
- ✅ `value_engine_run.py` orchestrator writes projections + superflex-aware VORP values.

### P2 — Draft tools *(August priority — the centerpiece)* — IN PROGRESS
- ✅ Offline manual board (DraftRoom): snake tracking, superflex roster fill, positional
  scarcity, recent-picks ticker, undo/reset — the universal, always-works path.
- ✅ Draft simulator ("Sim to my pick": bots draft best-available-by-need via VORP).
- ✅ Sleeper live-sync (the reliable reference path): server proxy routes + polling hook
  (`useSleeperSync`) + pick mapping by sleeper_id; Manual⇄Sleeper toggle; stall → "switch to
  manual (keep picks)" fallback per D7. *Built & building; not yet exercised vs a live draft
  feed (offseason — no active drafts / draft_id to poll).*
- ✅ ESPN live-sync (best-effort): /api/espn/draft proxy (cookie auth from server env) +
  `useEspnSync` + `mapEspnPicks` (by espn_id, snake-derived team); 3-way Manual/Sleeper/ESPN
  toggle; same "switch to manual (keep picks)" fallback on stall. *Unverified vs a live ESPN
  feed (offseason + needs real cookies) — built & building.*

### P3 — League Overview ✅ (pending live ESPN run)
- ✅ `league_sync.py` (espn-api, cookie auth) → `leagues` + `rosters` (with standings + ESPN ids).
- ✅ `/league` page: standings table (record, PF/PA bars, division) via `getLeagueOverview`.
- ✅ `rosters` schema extended (espn_team_id, standings, abbrev/logo/division).
- ⬜ Live run needs ESPN_S2/SWID cookies + `python league_sync.py` (offseason data will be sparse).

### P4 — Waiver Wire Tool + News/Sentiment engine *(season start)*
- `news_sentiment.py` (RSS + Reddit + VADER NFL lexicon), waiver-window cron.
- `news_articles` archiving begins (training corpus).
- Trending = sentiment ⊕ Sleeper add/drop. Waiver ranking = marginal value to my roster × trending.

### P5 — Trade Optimizer
- Pareto-improving swap finder across rosters using league scoring + positional need.

### P6 — Homepage *(shell early for nav; cinematic polish last)*
- Creative-dev "Broadcast Deck" hero + scroll story tying the tools together.

### P7 — Monte Carlo engine
- `MonteCarloEngine` swapped behind `ValueEngine`; UI toggle VORP ⇄ Monte Carlo.
- Requires `Projector` already emitting distributions (built in P0).

### Later / opportunistic
- Multi-tenant: per-user ESPN credentials + Supabase Auth + RLS rows + rules editor.
- Homegrown FinBERT trained on accumulated corpus → swap behind `SentimentScorer`.
- Paid projections (FantasyPros/Sportradar) behind already-stubbed keys.
- X/Twitter source.

## Definition of done per phase
Ships to Vercel, builds with no keys (offline empty states), pipeline script idempotent &
re-runnable, RLS public-read on new tables, respects `prefers-reduced-motion`.
