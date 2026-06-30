# Suggested Commands

All frontend commands run from `frontend/` (no root package.json). Platform: Darwin (macOS) — standard zsh; no platform-specific overrides needed.

## Frontend (cd frontend)
- `npm install` — install deps (npm; package-lock.json).
- `npm run dev` — Next dev server.
- `npm run build` — `next build` (DoD gate).
- `npm run typecheck` — `tsc --noEmit` (DoD gate).
- `npm run lint` — `next lint`.
- `npm test` — `vitest run` (one-shot); `npm run test:watch` — watch.
- `npm run audit:bundle` — `node scripts/audit-bundle.mjs` (no-secrets-in-bundle check).

## Pipeline (cd pipeline)
- `pip install -r requirements.txt`
- `python selftest.py` — idempotency/self-test (DoD gate for touched scripts).
- `python player_ingest.py [--trending]`
- `python history_ingest.py --seasons "2022 2023 2024"`
- `python value_engine_run.py --engine vorp` (or montecarlo)
- `python publish_snapshot.py --engines vorp`
- `python calibration_check.py`

## DB
- Migrations: SQL files in `db/migrations/`, timestamp+version prefixed (e.g. `20260626_v2.5.4_*.sql`). Apply via Supabase.

## RTK
- Shell commands auto-rewritten through `rtk` via hook (0 overhead). `rtk gain` for token savings.
