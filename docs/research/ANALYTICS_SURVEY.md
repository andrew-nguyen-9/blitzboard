# Analytics Survey — what pro football analytics measure, and what BlitzBoard applies (E2)

A committed research doc: the metrics professional fantasy/football analysts rely
on, which ones BlitzBoard computes given a **free-data-only** policy (nflverse,
public Sleeper/ESPN, CollegeFootballData), and — honestly — which ones we *cannot*
compute yet and why. This is the reference behind the per-player "Advanced
Analytics" panel (`frontend/components/PlayerAnalytics.tsx`) and the
`CollegeProspectFactor` (`pipeline/models/factors/college.py`).

## 1. What pro analytics actually measure

Modern football analytics splits into **volume**, **efficiency**, **usage /
opportunity**, and **context**:

| Family | Representative metrics | What it captures |
|--------|------------------------|------------------|
| Volume | targets, carries, snaps, routes run, pass attempts | raw opportunity — the #1 fantasy predictor |
| Efficiency | yards per route run (YPRR), yards per target (YPT), yards per carry (YPC), aDOT (avg depth of target), catch rate, EPA/play, success rate, YAC | how much a player does *with* each opportunity |
| Usage / role | target share, air-yards share, WOPR (weighted opportunity rating), snap share, red-zone touches, route participation | share of the team's scoring opportunity |
| Context | strength of schedule, pace / plays per game (PROE), offensive-line quality, game script, weather, Vegas team totals | the environment the opportunity happens in |
| Predictive / stable | EPA, YPRR, target share, aDOT are *stickier* season-to-season than TDs or yards, which regress hard | separates skill from noise |

**EPA (Expected Points Added)** — the play-value currency of modern analysis:
the change in a drive's expected points from one play, credited to the players
involved. **Route-level data (YPRR, route participation, aDOT)** is the gold
standard for receivers because it isolates a player from team pass volume. **Snap
share** is the usage backbone for every position.

## 2. What BlitzBoard computes today (free data)

Derived from the per-season `stats` jsonb already in `player_stats_history`
(nflverse counting stats) — **no new paid feed**. Surfaced per player and rendered
in the detail-page Advanced Analytics panel; E8 renders the same keys as optional
Player Explorer columns.

| Metric (key) | Definition | Family | Free-data note |
|--------------|------------|--------|----------------|
| Scrimmage Y/G (`scrim_ypg`) | (rush + receiving yards) ÷ games | volume | total offensive workload |
| Yards per carry (`ypc`) | rushing yards ÷ carries | efficiency | rushing efficiency, volume-independent |
| Yards per reception (`ypr`) | receiving yards ÷ receptions | efficiency | catch depth/quality |
| Yards per target (`ypt`) | receiving yards ÷ targets | efficiency | **free-data proxy for aDOT × catch quality** (we lack air yards) |
| Catch % (`catch_pct`) | receptions ÷ targets | efficiency/role | hands + role reliability |
| TD per opportunity (`td_per_opp`) | scrimmage TDs ÷ (carries + targets) | scoring | red-zone role / scoring efficiency (regresses — read with care) |
| Pass Y/G (`pass_ypg`) | passing yards ÷ games | volume (QB) | quarterback passing volume |
| TD:INT (`td_int`) | passing TDs ÷ interceptions | efficiency (QB) | decision quality |

Plus **target share** (already on the career table) — the single most predictive
free receiving-usage metric.

**College prospect score** (`prospect_score` ∈ [0, 1], 0.5 neutral) — condensed by
`ingest/college_ingest.py` from CFBD season production (scrimmage yards + TDs,
blended 70/30, normalized to a strong-season ceiling). Feeds
`CollegeProspectFactor`, which shades a **rookie's** flat-prior projection by up to
±12%. Degrades to identity when there is no college context.

**Multi-position value** (`pipeline/models/multipos.py`) — a player eligible at
more than one slot (e.g. RB+WR) is worth *more at the scarcer slot*: VORP is
computed per eligible position and the primary slot is the highest-VOR one. Not a
pro metric per se, but the correct way to value cross-eligible players.

## 3. What we do NOT compute yet, and why

| Metric | Why not (free-data limit) |
|--------|---------------------------|
| YPRR, route participation, aDOT (true) | require charted route/air-yards data (PFF/Next Gen Stats) — paid / licensed |
| EPA, success rate, PROE | derivable from nflverse play-by-play, but need a play-by-play ingest + model we have not built (candidate for a later phase) |
| Snap share, red-zone touches | snap counts are in nflverse but not yet in our season-aggregate jsonb; would need a snap-count ingest |
| WOPR / air-yards share | needs air yards (charted) |
| College dominator rating / breakout age | needs team totals + player birth dates to compute properly; current `prospect_score` is a **counting-stat heuristic**, documented as such, not a true dominator |
| Strength of schedule / Vegas totals | betting lines land via E5's odds adapter; SoS needs a schedule + opponent-defense model |

### Free-tier provenance
- **nflverse** (`nfl_data_py`): free, public; the historical counting stats above.
- **Sleeper**: free, keyless; player universe + `fantasy_positions` (multi-position).
- **CollegeFootballData**: free **user key** (`CFBD_API_KEY`), rate-limited on the
  free tier — backfill by season, cache; the whole college step degrades to a no-op
  with no key (F2 contract). See `docs/architecture/DATA_SOURCES.md` §College stats.

## 4. Guiding principle

Prefer **stable, opportunity-based** signals (target share, YPT, YPC, usage) over
**noisy outcome** signals (raw TDs), because the former predict next season and the
latter regress. Every metric here is honest about being a *free-data proxy* where
it stands in for a charted pro metric — we would rather ship a documented proxy than
imply we have data we do not.
