# Decisions — v4 bench-optimization cycle (2026-07-15)

Harvested from the `v4-bench-optimization` orchestrating cycle (7 epics, block-release /
no ship-without; PR #109 → main). One line per unit's load-bearing decision; the
`.orchestrator/` scratch these came from is not retained (git history is the archive).
Durable data/architecture gotchas are collected at the end.

## E1 — player_trends + trends_compute

- `player_trends` table + `trends_compute.py`. Weekly `stats` JSON keys read: `targets`, `carries`, `target_share`, `routes_run` (E2's new col; absent → `routes_run` 0.0, `routes_trend` 0.5). opportunity = targets + carries.
- Trend window: last **4** weekly rows of latest season vs whole-season avg. Metric = `0.5 + 0.5*(recent-season)/(recent+season)` in [0,1], 0.5 neutral.
- QB `starting_prob`/`job_security` from `metadata.depth_chart_order` (1→0.90/0.85, 2→0.30/0.35, ≥3→0.08/0.15) × injury haircut; non-QB / no order → 0.5.

## E2 — offensive snap% + routes-run ingest

- Free nflverse exposes offensive snap share but **no per-player routes count** → `routes_run` stores offensive snaps as the opportunity proxy (documented in code). `STAT_COLS` keys are exactly `offense_snap_pct`, `routes_run` — match E1's reader.
- Reliability guard = `@retry_api` live pull that auto-vendors `.nflverse_cache/snap_routes.parquet` (gitignored, CI-cache marker pattern) and reads it when live is down. Block-release: the ingest is a hard requirement, made reliable rather than degraded.

## E3 — static 2026-27 schedule module

- `frontend/lib/schedule2026.ts` E4-facing signatures: `opponentFor`, `remainingSchedule`, `playoffOpponents` (wks 15–17), `scheduleStrength(team, weeks, defRatings?)`, `playoffSchedule(player, defRatings?)`, `byeWeekFor`.
- `scheduleStrength`: easiness = `1-rating` (lower rating = tougher); byes skipped; `defRatings` **defaulted neutral 0.5**, `covered=0` (pipeline defense NOT published to frontend). Pass a 0..1 per-team map to activate.

## E4 — superflex bench score

- superflex score = `base(0-100) × mult` clamped 100 (QB premium saturates). `WeeklyFlexValue`=0 for non-flex QB/K/DST (structural, not degraded). `defRatings` unset → `PlayoffSchedule`/`Schedule` degrade to neutral. Pure, no DB calls; reuses `draftAI.proj`, `schedule2026.playoffSchedule`, `leagueConfig.rulesFromConfig`.

## E5 — fold bench scoring into auto-draft bench arm

- Bounded **multiplicative** tilt (not additive) keeps the bench arm ~same magnitude so it never overtakes the starter arm.

## E6 — war-room Bench panel

- Mount = `BenchPanel`; trends read = `queries.getPlayerTrends(ids?)`. E7 wires `getPlayerTrends` into `app/draft/page.tsx` → `DraftWarRoom trends=`.

## E7 — backtest (verify-only)

- No product code; full-draft superflex sim asserting ideal bench composition.

## Durable gotchas

- `depth_chart_order` lives in the players `metadata` JSON, **not a column** (E1).
- `pfr_id`→`gsis` crosswalk ~66% overall coverage (higher for skill positions); unmatched snap rows dropped, not fabricated. `.nflverse_cache/` gitignored → production parquet not committed, regenerated first live run (E2).
- Neutral-site (intl) games → `home:null` both sides (not home); bye = `opponent:"BYE"` (E3).
- Circular import `draftAI`↔`benchScore` is safe (both used only inside functions, never top-level) (E5).
- `player_trends` has no `target_share` column → `BenchTrends.target_share` stays undefined (E6).

cost: run ≈ Σ subagent ~800k tok (builders + integ) vs est ~1.09M — under est.
process: all 7 units first-pass green; no ⛔, no conflicts, no fix-mode re-dispatches. E2 needed one SendMessage (mid-work stop); done-note header reformats on E1/E3.
