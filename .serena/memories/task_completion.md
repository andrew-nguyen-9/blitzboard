# Task Completion (Definition of Done)

Source: `docs/workflow/DEFINITION_OF_DONE.md`. "It builds" is NOT done.

## Per-task gate
- Implements exactly its acceptance criterion; no scope creep.
- `npm run build` AND `npm run typecheck` (`tsc --noEmit`) pass, no new errors/warnings (run from `frontend/`).
- `npm test` (vitest) green; new logic has tests (unit for pure fns, integration for data paths).
- Touched pipeline scripts are idempotent/re-runnable; `python selftest.py` passes.
- No secrets in client bundle; no service-role key reachable from browser (`npm run audit:bundle`).
- New tables: RLS enabled + explicit policies.
- Commit msg `v2.<s>.<t> <scope>: <summary>`, NO AI attribution. Only commit/push if task says so.

## Per-UI-segment QA (cross-cutting)
- Responsive 320→1920 (test 360/768/1280/1920), no overflow/clipped cells.
- Reduced-motion static fallback on every animation.
- a11y: keyboard, focus rings, landmarks, aria, contrast ≥ WCAG AA, color not sole signal.
- Themes correct in light/dark/system.
- Empty/loading/error states render with no backend/keys.
- Perf: CLS≈0, interactions <100ms, 60fps animations. Budgets: LCP ≤2.5s (mobile/4G), CLS ≤0.05.

## Per-phase finish (8-step)
QA full phase → `/code-review` full diff → commit → merge to `main` + tag → delete branches → review all docs → archive phase docs → write brainstorming file.
