# Roadmap

Carried-forward work. Harvested from each landed cycle's `.orchestrator/` before it is deleted;
read at the start of the next cycle's scoping pass.

## Deferred epics

- **E13 — War-room explainability UI** (deferred out of v5, 2026-08-26). Not built; a later UI pass
  reuses the existing `explain` / `shapley_pick_attribution` surfaces.
- **Standing "Pending activation" backlog**, explicitly out of scope for v5: factor hydrator,
  `/betting` + `/articles` nav links, sitemap, college enrich.

## v5 follow-ups (recorded in PR #112, none blocking)

- `queries.getAvailabilityMap` is never called — nothing populates `ctx.availability` in
  `DraftWarRoom.tsx`, so the published availability surface does not reach the board.
- E8 grid invariants are largely tautological: the same derived bounds constrain the CP-SAT solve
  and re-check its output. The real bite is in the synthetic counter-cases.
- `availability_p` (intelligence) and `p_startable` (v5) are one quantity under two names.

## v6 candidates (from `e14-docs-harvest`)

- **Engine ruff discrepancy**, real and inherited on `main`:
  `(cd engine && ../pipeline/.venv/bin/python -m ruff check blitz_engine/testing/corpus.py tests/test_backtest_metrics.py)`
  → 8 issues. Engine ruff is not on the `CLAUDE.md` DoD line, so this is not a gate violation —
  fix it deliberately, do not inherit it.
- **`xtier.py` has no file to execute** — it exists only as a verbatim paste in
  `docs/design/v5-static-dynamic.md` §8. Committing it under `engine/experiments/` is a cheap win.
- **`MC_VOL_GAIN` was never fitted** — now documented in `docs/modeling/calibration.md` as an
  unvalidated hand-authored number. A doc correction, not a code bug, but it means the projector's
  σ knob has never been calibrated.

## Pending user / infra actions

- **Live Supabase apply of the E2 availability migration** (optional, unticked at v5 land). The unit
  authored and tested the migration and RLS policies locally in `db/migrations/`, and the app builds
  and renders empty states without it, so this defers to deploy. Needed only when the availability
  surface must be live in prod.
