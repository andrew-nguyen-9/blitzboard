# Contributing

This repo follows a phase/segment/task workflow. Read these before opening a branch:

1. `docs/workflow/VERSIONING.md` — the `v[phase].[segment].[task]` scheme.
2. `docs/workflow/GIT_WORKFLOW.md` — branch per phase, sub-branch per segment, the per-segment
   loop (build→test→QA→/code-review→commit→push to parent) and the 8-step phase finish.
3. `docs/workflow/DEFINITION_OF_DONE.md` — what "done" means + QA/perf/a11y/security checklists.
4. `CLAUDE.md` — conventions, enabled tooling, and AI-assisted dev guidance.

## TL;DR

- **Never commit to `main` directly.** `main` only receives finished, reviewed phases.
- One phase = one branch (`v2`); one segment = one sub-branch (`v2.3-player-data`) merged back
  to the phase branch via PR; the phase merges to `main` only when whole and verified.
- Every PR uses `.github/PULL_REQUEST_TEMPLATE.md` and meets the Definition of Done.
- Commits/PRs carry **no AI attribution**.
- Accessibility, performance budgets, reduced-motion, and RLS are acceptance criteria, not extras.

## Current work

v2 — see `docs/phases/v2/PHASES_OVERVIEW.md`. v1 (P0–P7) is archived in `docs/archive/v1/`.
