# 2026 intelligence signal gaps

This register distinguishes live-source failures from researched-but-unimplemented signals. An
absent source is unknown coverage, never evidence that an event did not happen.

## Frozen live-baseline gaps

| Signal/table | State at cutoff | Consequence | Required resolution |
|---|---|---|---|
| nflverse injuries / `status_injury_reports` | HTTP 404 for the 2026 release asset | No 2026 practice/game-designation rows | Re-run only after the versioned asset exists; preserve fetch-time semantics where publication time is absent |
| ESPN news / `status_news` | HTTP 403 from the public adapter | No news rows or player resolution measurements | Replace or repair with a documented, permitted adapter; validate shape before writing |
| Official gameday inactives / `status_inactives` | No stable documented no-key adapter | No authoritative 90-minute inactive feed | Add a licensed official adapter with publication time, game/team identity, and fail-loud schema tests |

Weekly rosters and depth charts are available, but they do not close these gaps: they are snapshots,
not injury reports, transaction prose, news, or official inactive declarations.

## Registry coverage

The versioned registry contains 12 cards: two implemented, eight candidates, one blocked, and one
intentionally excluded. Against non-excluded cards, implemented-card coverage is 2/11 (18.2%). Its
1,880 MB storage total is an estimate across the entire proposed registry.

Candidate work remains for transactions, trade scenarios, weather/venue, travel/rest, usage/role,
market context, and coaching/offensive-line/opponent context. Each needs a documented source and
license, point-in-time timestamp semantics, stable identity, missingness behavior, leakage controls,
and tests before it can become implemented.

Public personal context remains zero-weight and shadow-only. Private details, protected traits,
diagnoses, gossip, and inferred mental state are intentionally excluded and must not be collected.

## Promotion and validation gaps

Completed 2026 regular-season outcomes were unavailable at the cutoff, so no walk-forward comparison
or promotion decision is possible. Both models stay shadow-only until shared vintage-safe folds can
measure MAE, RMSE, rank correlation, interval calibration, and top-k decision utility for every
position and league configuration. K and DST require their own evidence rather than borrowed
offensive-player coefficients.

Before closing any gap, add a representative missing/stale/schema-drift fixture, validate the
authoritative consumer, and freeze the source, code, config, seed, and artifact hashes needed for
replay.
