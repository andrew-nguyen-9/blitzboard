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

### P4 — Waiver Wire Tool + News/Sentiment engine ✅
- ✅ `models/sentiment.py`: `VaderScorer` (NFL lexicon: injury terms negative, usage terms
  positive; phrase normalization) + `PlayerMatcher` (n-gram entity resolution, no bare-name
  false positives). Interface = FinBERT swap point.
- ✅ `news_sentiment.py`: RSS (ESPN/PFT/Yahoo/CBS) + Reddit → `news_articles` (training corpus)
  + blended `trending` (0.55·tanh(add velocity) + 0.45·sentiment − injury penalty).
- ✅ `.github/workflows/sentiment.yml`: 30-min cron gated to 08:00–01:00 + waiver-relevant days.
- ✅ `/waivers` page: FAAB **bid** recommendations (% of remaining budget × trend) + live news pulse.
- Ran live: 139 articles, 67 matched, 205 trending players. selftest covers it.

### P5 — Trade Optimizer ✅
- ✅ `lib/trade.ts`: `findTrades()` — Pareto-improving swaps (both lineups improve), need-aware
  via `fillRoster` (benched depth worth less than a started starter); 1-for-1 / 2-for-1 / 2-for-2,
  ranked by your gain + fairness.
- ✅ `/trades`: pick my team ↔ partner, ranked proposal cards (give/get, both deltas, fairness%).
- ✅ `league_sync.py` mapping fixed via nflverse crosswalk (ESPN id→Sleeper id→our id): 73→179
  rostered players mapped (~15/team). Ran against real Smores 2025 rosters.
- Verified: real Pareto trades found between live rosters (e.g. surplus-QB → needed-RB swap).

### P6 — Creative overhaul (site-wide) ✅
- ✅ **Type revamp**: Bricolage Grotesque (display) + Anton (scoreboard numerals) + Hanken
  Grotesk (body) + JetBrains Mono — replaced Inter/Space Grotesk. New tighter display scale.
- ✅ **Physics 404** (`FootballPit`): draggable footballs, gravity, ball↔ball elastic collisions,
  circle↔AABB collisions vs the live text/button bounding boxes; throw-to-release; reduced-motion static.
- ✅ **Motion toolkit**: `SmoothScroll` (Lenis), `Cursor` (broadcast reticle + contextual label),
  `motion.tsx` (Reveal / SplitText / Magnetic / CountUp), `Marquee` (broadcast ticker), `TiltCard`
  (3D tilt + cursor glare). All honor `prefers-reduced-motion`.
- ✅ Homepage rebuilt: kinetic split-text hero, magnetic CTAs, live ticker, scoreboard CountUp band, tilt-card deck.

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
