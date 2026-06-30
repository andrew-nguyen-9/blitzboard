# Core (graph root)

BlitzBoard: pipeline-driven NFL fantasy war room. Next.js 15 App Router frontend + Python ETL/model pipeline + Supabase Postgres. v1 (P0-P7) archived under `docs/archive/v1/`; building v2/v3. Spine = 4 interfaces: `LeagueRules`, `Projector`, `ValueEngine`, `SentimentScorer` (`docs/architecture/ARCHITECTURE.md`).

## Source map
- `frontend/` — Next.js app
  - `app/` — App Router routes: page, layout, draft/, trades/, players/, waivers/, league/, login/, signup/, auth/, api/, actions/ (server actions), kit/ (design kit). middleware.ts at frontend root.
  - `components/` — incl. `RiveInstrument.tsx` (Rive animation wrapper).
  - `lib/` — all logic. Key files:
    - `queries.ts` — ALL public (anon) Supabase reads, null-safe.
    - `queries.auth.ts` — authenticated reads (per-user RLS).
    - `leagueRules.ts` — LeagueRules scoring/roster config.
    - `crypto/vault.ts` — encrypted credential vault (ESPN/Sleeper secrets).
    - `auth/` — gate.ts, gate.server.ts, prefs.ts, redirect.ts, cookies.ts.
    - `supabase/` — server.ts, middleware.ts (SSR clients).
    - scoring/draft: score.ts, tiers.ts, draft.ts, draftAI.ts, snakeDraft.ts, faab.ts, trade.ts, analysis.ts, viz.ts; importers: espnDraft.ts, sleeperDraft.ts, leagueImport.ts.
    - reducedMotion.ts, gsap.ts, lenis.ts (animation).
- `pipeline/` — Python cron ETL/models. Entrypoints: `player_ingest.py`, `history_ingest.py`, `league_sync.py`, `news_sentiment.py`, `value_engine_run.py` (--engine vorp|montecarlo), `publish_snapshot.py`, `calibration_check.py`. Support: `common.py`, `vault.py`, `selftest.py`. Subdirs: models/, backtest/, tests/.
- `db/` — `schema.sql`, `seed_league_example.sql`, `migrations/` (timestamp+version prefixed, e.g. `20260626_v2.5.4_multi_league.sql`).
- `.github/workflows/` — `ci.yml`, `etl_daily.yml` (cron: setup-python 3.11 → player_ingest → history_ingest → value_engine_run → publish_snapshot).
- `mocks/` — design research (`mocks/v2-research/`).
- `docs/` — architecture/, workflow/, phases/, design-system/, security/, modeling/, archive/v1/.

## Project-wide invariants
- Server Components default; `"use client"` only for interactivity/animation.
- ALL public Supabase reads go through `frontend/lib/queries.ts`; client is null-safe → offline/no-keys renders empty states (app builds & renders with zero keys).
- Service-role key = pipeline ONLY (never reachable from browser); anon key = public reads. RLS isolates authenticated rows per `auth.uid()`.
- Data delivery: pipeline publishes compressed CDN-cached snapshots of the value layer; frontend never computes value, never paginates 1000+ rows out of PostgREST.
- Two planes: public read (anon + snapshots) vs authenticated (Auth.js sessions, per-user RLS, encrypted vault).

## Further memories
- Stack/tooling/package manager: `mem:tech_stack`.
- Dev/build/test/pipeline commands: `mem:suggested_commands`.
- Coding conventions (RLS, migrations, motion, tokens, minimalism): `mem:conventions`.
- Definition of Done / per-task gate: `mem:task_completion`.
