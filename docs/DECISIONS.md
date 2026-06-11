# Locked Decisions

Captured from the pre-build design interview. Each is a decision we committed to,
with the reasoning, so future-us doesn't relitigate settled questions.

---

### D1 — Player data backbone: layered, not single-source
- **Sleeper API** → canonical player universe + trending adds/drops. Free, public, no auth, reliable.
- **nflverse / `nfl_data_py`** → historical stats & play-by-play. Feeds our own projection model.
- **ESPN Fantasy API** → league rules, team lineups, draft feed, league-specific news. Read-only *enrichment*, never the player backbone.
- **Paid APIs (FantasyPros/Sportradar)** → deferred behind placeholder env keys.

**Why:** Sleeper is the only free, reliable, no-auth full universe. ESPN is fragile and league-scoped, so it can't be the spine.

---

### D2 — News & sentiment engine
- **Sources:** RSS feeds (ESPN, Rotoworld/NBC, Yahoo, PFF, beat writers) + Reddit (r/fantasyfootball). Both free, cron-pollable.
- **X/Twitter:** deferred (expensive, locked down) behind a placeholder key.
- **Trending signal = narrative (news sentiment) blended with behavior (Sleeper hard adds/drops).**

**Why:** Free sources fit the existing pipeline pattern; blending narrative with real add/drop numbers is more honest than either alone.

---

### D3 — Sentiment model: self-hosted, NFL-tailored, batch-scored
- Build our own **VADER → FinBERT-style** scorer, NFL-tuned, **not** the Claude API.
- **v1 = VADER + NFL lexicon** (weights for "questionable", "ruled out", "bell-cow", "handcuff", "snap count", etc.) running *inside* the GitHub Action — no model hosting needed.
- Every article seen is archived to a `news_articles` table → **this becomes our training corpus**.
- Later: fine-tuned FinBERT swapped behind the same `SentimentScorer` interface (served via HF Inference Endpoint, placeholder key stubbed).
- **Batch scoring only:** refreshed every **30 min, 8am–1am**, **only on waiver-relevant days** (configurable window: Tue→Wed waiver run + game days). Dormant otherwise.

**Why:** No live-inference infra exists in the stack; batch scoring during the waiver window is when it actually matters and keeps cost ~zero. "Real-time" = 30-min freshness.

---

### D4 — League connection: my league now, multi-tenant-ready
- **v1 = one ESPN league** (my own). Cookies (`espn_s2` + `SWID`) + `league_id` in pipeline `.env`.
- Schema is **multi-tenant-ready**: `leagues` table + `settings` JSONB; a `league_credentials` table that *later* gets per-user rows + RLS.
- **No Supabase Auth / no credentials-paste UI in v1.**

**Why:** Build for the real user (me) without prematurely building multi-tenant auth, but don't paint the schema into a corner.

---

### D5 — Value engines: two, behind a toggle
- **`VorpEngine`** — deterministic value-over-replacement. projections × league rules → VOR. Fast, transparent.
- **`MonteCarloEngine`** — simulates N-thousand drafts/seasons (projection distributions + opponent behavior + ADP noise) → expected value + boom/bust range.
- **UI toggle** flips which engine feeds draft/trade/waiver tools.
- Both **batch-precomputed** in the pipeline and cached in Supabase → instant toggle in the frontend.
- **Consequence:** the `Projector` must emit **distributions (mean + floor/ceiling/stdev)**, not point estimates, so Monte Carlo isn't blocked later.

**Why:** VORP is what wins most drafts and is cheap; Monte Carlo captures scarcity runs and risk. Letting the user choose is a real differentiator.

---

### D6 — Projections: a 3-input ENSEMBLE behind one `Projector`
Blend three independent signals into one ensemble projection (mean + distribution):
1. **Regression model** — trained on `nfl_data_py` history (target share, snap %, efficiency, team context).
2. **Heuristic model** — prior-season production adjusted for **age curve + role/depth-chart change**.
3. **Consensus piggyback** — others' rankings/ADP/projections (FantasyPros ECR, FFC ADP, ESPN's own projections). See [DATA_SOURCES.md](DATA_SOURCES.md).

- **Ensemble mean** = weighted blend (weights tunable, start ≈ equal). **Distribution
  (floor/ceiling/σ)** derived from *disagreement across the three* + historical positional
  variance → feeds Monte Carlo directly.
- All three are `Projector` implementations summed by an `EnsembleProjector`; weights live in config so we can re-tune or drop a source.
- `projections` table already stores `source` per row → we keep each input *and* the ensemble, so we can audit which signal drove a value.
- **Superflex-aware:** consensus inputs must be the **superflex/2QB ranking variants** where available (standard rankings misprice QBs for this league — see D9).

**Why:** No single projection source is trustworthy. An ensemble that blends our own math
with the crowd is more robust, and disagreement between sources is itself a useful risk signal.

---

### D7 — Live vs Offline draft = one board, two pick-input adapters
- **Live tool** = auto-sync to the real online draft (poll the feed; board updates as picks land). **Target platform: ESPN.**
- **Offline tool** = manual board for in-person drafts (tap each pick as the room calls it). No feed to sync.
- Both drive the **same `ValueEngine`** best-available recompute. They differ only in pick-input source.
- **ESPN live-draft feed is the most fragile thing we touch.** So: **manual board is the default code path; ESPN sync is an accelerator layered on top.** When the feed stalls, the tool drops straight into the manual offline board (user enters picks).
- **Sleeper auto-sync** is technically first-class-easy (public draft API) and worth building as the reliable reference path even though my draft is on ESPN.
- **Hosted multiplayer draft room = OUT of scope** (that's rebuilding Sleeper).

**Why:** A broken ESPN feed mid-draft must be a minor annoyance, not a disaster. Manual-first guarantees the tool always works.

---

### D8 — Build order: draft-first, in-season tools later
It is **June 2026 (offseason)**. Draft tools matter in Aug/Sept; waiver/trade matter Sept+.
Most sections are different views of the same `ValueEngine` + player DB.

Order: Foundation → Player Explorer → Draft tools → League Overview → Waiver + Sentiment → Trade → Homepage polish → Monte Carlo swap-in. (See [ROADMAP.md](ROADMAP.md).)

Unbuilt sections render **graceful "coming soon" empty states** (inherited pattern from festival-analyzer).

---

---

### D9 — League rules locked: "Smores 2025" (superflex half-PPR) ✅
Full ruleset captured in [LEAGUE_RULES.md](LEAGUE_RULES.md) + seeded in
[../db/seed_league_smores.sql](../db/seed_league_smores.sql). 12-team, 0.5 PPR, snake.

**Critical modeling consequence:** the **OP (Offensive Player Utility) slot accepts a QB →
this is effectively a SUPERFLEX league.** Replacement-level QB sits ~24th, not ~12th. The
`ValueEngine` derives replacement baselines from *league-wide slot demand* (never hardcoded
1-QB assumptions); Monte Carlo opponent models reflect QB-hungry drafting. Also: distance-based
kicker scoring and a yardage-allowed D/ST component need position-specific projection treatment;
FAAB means the waiver tool recommends **bid amounts**, not just priority.

**Why:** Getting the superflex replacement level right is the difference between useful and
misleading draft values for this specific league.

---

## Still open (revisit before/while building)
- **Design art direction** — direction proposed in [DESIGN.md](DESIGN.md); confirm the "broadcast instrument-panel × dark athletic luxury" theme and the accent-color system.
- ~~Scoring profile specifics~~ — **CLOSED, see D9.**
- **Own-projection model method** — regression vs. simple prior-season+age/role; decide when we start D6's homegrown half.
