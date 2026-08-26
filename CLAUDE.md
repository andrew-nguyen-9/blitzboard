# CLAUDE.md — Repo dev instructions (Claude Code)

Project-specific guidance for AI-assisted development of BlitzBoard.
Global rules in `~/.claude/CLAUDE.md` still apply (notably: **no AI attribution** in any
git artifact). This file adds the project's workflow, conventions, and tooling.

## What this project is (v2)

A pipeline-driven NFL fantasy war room. Next.js 15 (App Router) + Supabase (Postgres) +
Python cron pipeline. v1 (P0–P7) is archived under `docs/archive/v1/`; v2 shipped through
v2.7.0 (`docs/phases/v2/PHASES_OVERVIEW.md`); v3 has landed on `main`. The spine is four interfaces:
`LeagueRules`, `Projector`, `ValueEngine`, `SentimentScorer` (`docs/architecture/ARCHITECTURE.md`).

## The workflow (non-negotiable)

Versioning is `v[phase].[segment].[task]` → `v2.3.2`. Read `docs/workflow/VERSIONING.md`
and `docs/workflow/GIT_WORKFLOW.md` before starting any work. In short:

- A **phase** opens a branch (`v2`, `v3`, …).
- A **segment** opens a sub-branch off the phase branch; you complete its tasks, build,
  test, QA, run `/code-review`, commit, and push to the **parent (phase) branch**.
- A **phase finishes** with: QA → `/code-review` → commit → merge to `main` → delete old
  branches → review all docs → consolidate & archive the phase docs → write a brainstorming
  file of ideas that surfaced. See `docs/workflow/DEFINITION_OF_DONE.md`.

Never commit or push unless the task says so. Never work directly on `main`.

## Tooling / plugins enabled for this repo

These are part of the v2 dev workflow. They are token/quality multipliers — use them.

| Plugin | Role | When it applies |
|--------|------|-----------------|
| **RTK** (Rust Token Killer) | Shell-command proxy; rewrites `git status` → `rtk git status` etc. via hook (0 overhead). 60–90% token savings on dev ops. | Always on (hook-driven). Use `rtk gain` to check savings. |
| **ponytail** | Code-minimalism skill — "the senior dev who replaces 50 lines with one." ~54% less code, keeps every safety guard. | Invoke before/while writing any non-trivial component or model code. Prefer the platform primitive (`<input type="date">`) over a dependency. |
| **caveman** | Compresses *conversational* output ~75%, keeps technical accuracy. | **Chat/status replies only.** Do NOT apply to written docs, code comments, commit messages, or PR bodies — those stay clear and complete. Conflicts with the active explanatory/learning output style, which wins for teaching moments. |
| **superpowers** (brainstorming, writing-plans, TDD, systematic-debugging) | Process discipline. | Brainstorm before planning; write a plan before implementing; TDD for model/scoring code; systematic-debugging for bugs. |
| **playwright** | Live UI/design study + E2E. | Design research (done for v2 — see `mocks/v2-research/`), visual QA, accessibility checks. |
| **chrome-devtools / lighthouse** | Perf + Core Web Vitals audits. | v2.1 homepage perf, v2.7 hardening. |
| **supabase / context7 / vercel** | DB ops, current library docs, deploy. | Auth/data work (v2.5), fetching up-to-date API docs, deploys. |

## Conventions (inherited + v2)

- Frontend: Server Components by default; `"use client"` only for interactivity/animation.
- All Supabase reads in `frontend/lib/queries.ts`; client is null-safe (offline → empty states).
- Service-role key = pipeline only; anon key = public reads, enforced by RLS. **Authenticated
  user data is RLS-isolated per `auth.uid()`** (v2.5+).
- New tables: RLS enabled, explicit policies. Migrations in `db/migrations/`, timestamp-prefixed.
- Every animation honors `prefers-reduced-motion` with a static fallback.
- Design tokens are OKLCH CSS custom properties swapped by `data-theme` (see `docs/design-system/`).
- Ship with no keys: the app builds and renders empty states before any backend exists.

## Definition of done (per task)

Builds clean (`npm run build`, `tsc --noEmit`), respects reduced-motion, RLS on new tables,
pipeline scripts idempotent, accessibility checks pass, no secrets in client bundles.
Full checklist: `docs/workflow/DEFINITION_OF_DONE.md`.

<!-- Canonical machine-greppable lines (orchestrator GATE 1 + cleaning). Prose above is the human detail. -->
DoD: (cd frontend && npm run build && npm run typecheck && npm run lint && npm test) && (cd pipeline && ./.venv/bin/python -m pytest) && (cd engine && ../pipeline/.venv/bin/python -m pytest)
DoD-note: use pipeline/.venv (Python 3.12, jax/torch/numpyro + blitz_engine editable); Homebrew python3 is 3.14 and will NOT work; pipeline/ must never import jax/torch (keeps free GH-Actions cron alive)
DoD-note: WORKTREE, load-bearing — in a LINKED git worktree the venv's *editable* blitz_engine resolves to the MAIN checkout, so `cd engine && pytest` collects the worktree's tests but imports MAIN's code — you can green-light code that is not yours. Always run `(cd engine && PYTHONPATH="$PWD" /abs/path/to/blitzboard/pipeline/.venv/bin/python -m pytest)`; `../pipeline/.venv` does not exist in a linked worktree (gitignored), use the absolute main-checkout path. Frontend: run `npm ci` in the worktree's `frontend/` first (node_modules is not shared). See `docs/modeling/experiments.md` §0.
Secrets: frontend `.env.local` (anon key = public reads, RLS-enforced); pipeline via GitHub Actions secrets / Supabase vault; service-role key = pipeline only, never in client bundle
Branches: per-unit `v5/<unit>` off `integration`; local-merge into `integration` during waves, land via one PR `integration`→`main` (main is branch-protected); block-release (a unit that can't meet DoD blocks, never ships degraded)
