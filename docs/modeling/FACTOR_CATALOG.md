# Factor Catalog (E3) — free-derivable projection factors

Every projection factor that free public data can support, brainstormed and
scored. Each row records its **data source**, **free-tier limit**, whether it is
**implemented**, and its **backtest verdict**. This is the companion to the
protocol in [`FACTOR_CONTRACT.md`](./FACTOR_CONTRACT.md); the implemented factors
live as DISJOINT files under `pipeline/models/factors/` and are auto-discovered.

## The two invariants (why this is safe to ship)

1. **No data → neutral, never a crash.** Every factor reads its inputs from
   `ctx.metadata` (hydrated by `pipeline/ingest/context_ingest.py`) and returns
   its identity (`1.0` / `0.0`) when the input is absent. Historical-backtest
   players carry no context metadata, so the factors are true no-ops there → the
   models backtest does **not** regress. Proven by
   `pipeline/tests/test_factor_backtest.py`.
2. **Clamped effects.** Every multiplier is bounded to a gentle band, so one
   game's weather or an extreme pace can never dominate a season projection.

## Backtest verdict legend

- **NEUTRAL (no regression)** — verified byte-identical projections vs. `factors=[]`
  on context-free players (the historical state). Implemented + safe; the lift
  switches on only once live context is ingested.
- **HELPS** — moves the projection in the documented direction when fed real
  context; direction + clamp verified by unit assertions.
- **BRAINSTORMED** — free-derivable but not yet implemented (rationale noted).

Every implemented E3 factor is today **NEUTRAL (no regression)** against the frozen
historical backtest *and* **HELPS (correct, bounded direction)** when fed context —
the two are not in tension: neutral = no historical metadata; helps = with metadata.

## Implemented — `models/factors/environment.py`

| Factor (class) | Kind | Positions | Signal | Source | Free-tier limit | Verdict |
|---|---|---|---|---|---|---|
| `WeatherPassingFactor` | mult | QB/WR/TE | cold + wind + precip suppress passing (floor 0.85) | Open-Meteo forecast | keyless; non-commercial ≤10k calls/day | NEUTRAL + HELPS |
| `WeatherRushingFactor` | mult | RB | bad passing weather nudges run script (≤+4%) | Open-Meteo forecast | keyless; ≤10k/day | NEUTRAL + HELPS |
| `KickingConditionsFactor` | mult | K | wind/cold hurt, Denver altitude helps | Open-Meteo + static `STADIUMS` elevation | keyless / static | NEUTRAL + HELPS |
| `DomeBoostFactor` | mult | QB/WR/TE | indoor games remove weather variance (+2%) | static `STADIUMS` dome flag | static (no API) | NEUTRAL + HELPS |

`STADIUMS` (dome / elevation / lat-lon per canonical team) is public static data —
no API, no key. It is the shared venue source `context_ingest` imports.

## Implemented — `models/factors/scheme.py`

| Factor (class) | Kind | Positions | Signal | Source | Free-tier limit | Verdict |
|---|---|---|---|---|---|---|
| `TeamPaceFactor` | mult | QB/RB/WR/TE | fast pace → more plays → more volume (±6%) | nflverse PBP (plays/game) | free, no key | NEUTRAL + HELPS |
| `PassRateFactor` | mult | QB/RB/WR/TE | pass-heavy lifts catchers, trims RB rush (±5%) | nflverse PBP (pass rate) | free, no key | NEUTRAL + HELPS |

## Brainstormed — free-derivable, not yet implemented

| Idea | Would source from | Free-tier | Why deferred |
|---|---|---|---|
| Vegas game total / spread → volume & script | The Odds API | key-gated (`ODDS_API_KEY`, F2) | needs the F2 odds adapter live; strong once keyed |
| Defense-vs-position matchup (points allowed by pos) | nflverse PBP | free | needs a season of opponent aggregates; heavier compute |
| Snap-share / depth-chart role | nflverse / Sleeper depth | free | volatile week-to-week; risks double-counting projector volume |
| Home/away & travel (time-zone, short week) | schedule (static) | free | small effect; schedule join not wired here |
| Coaching / OC change uncertainty | manual / news | free-ish | qualitative; better as a variance widener than a mean shift |
| Rookie / age curve | roster (`age`, `years_exp` in ctx) | free (already on ctx) | overlaps E2 college factor; leave to that unit |
| Grass vs turf, roof-open probability | static + forecast | free | marginal; folded conceptually into dome flag |

## The ingest + artifact (E9b handoff)

`pipeline/ingest/context_ingest.py` is an **F2-style keyless adapter**
(`WeatherContextAdapter`, Open-Meteo) plus pure builders. It emits
`pipeline/artifacts/context_report.json`:

```jsonc
{
  "generated_at": "2026-07-09T00:00:00+00:00",
  "season": 2025, "week": 3,
  "source": "open-meteo (keyless…) + static stadium table",
  "degraded": false,
  "teams": {
    "DEN": {
      "venue": {"dome": false, "elev": 5280, "lat": 39.74, "lon": -105.02},
      "metadata": {                       // ← drops straight onto FactorContext.metadata
        "venue_team": "DEN",
        "weather": {"temp_f": 34, "wind_mph": 12, "precip": false, "indoor": false}
      }
    }
    // …all 32 teams, always present
  }
}
```

- **E9b (Articles)** reads this artifact to publish the war-room environmental /
  context brief (auto-generated, no AI in the loop).
- A future hydrator merges `teams[code].metadata` onto each player's row so the
  factors above act in production; until then they stay neutral by construction.
- **Cron:** the `Ingest environmental/team context (E3/backtest)` step in
  `.github/workflows/etl_daily.yml` runs it daily, `continue-on-error` +
  degrade-safe, before projections.
