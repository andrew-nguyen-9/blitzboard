# Conventions

(Source: `CLAUDE.md`, `docs/workflow/`, `docs/design-system/`.)

## Architecture
- Server Components default; `"use client"` ONLY for interactivity/animation.
- All public Supabase reads in `frontend/lib/queries.ts`; client null-safe (offline/no-keys → empty states). Authenticated reads in `lib/queries.auth.ts`.
- Service-role key = pipeline only; anon = public reads. App must build & render empty states with NO keys ("ship with no keys").

## Data & security
- New tables: RLS enabled with explicit policies; authenticated rows isolated per `auth.uid()`.
- Migrations: `db/migrations/`, timestamp+version-prefixed (`YYYYMMDD_vX.Y.Z_name.sql`).
- No secrets in client bundle; service-role key never reachable from browser.

## UI / design
- Every animation honors `prefers-reduced-motion: reduce` with a static fallback (helpers in `lib/reducedMotion.ts`).
- Design tokens: OKLCH CSS custom properties swapped by `data-theme` (light/dark/system).
- a11y: keyboard-nav, visible focus, semantic landmarks, contrast ≥ WCAG AA, color never the only signal. Responsive 320→1920px.

## Code style (ponytail minimalism)
- Prefer the platform/stdlib primitive (`<input type="date">`, CSS, DB constraint) over a dependency. No abstraction with one implementation; shortest working diff; reuse existing helpers before writing new.

## Workflow
- Versioning `v[phase].[segment].[task]` (e.g. `v2.3.2`). Branch per phase (`v2`, `v3`); sub-branch per segment, push to parent phase branch. Never work on `main`; never commit/push unless task says so.
- No AI attribution in any git artifact (commits, PRs, branches).
- See `docs/workflow/VERSIONING.md`, `GIT_WORKFLOW.md`, `DEFINITION_OF_DONE.md`.
