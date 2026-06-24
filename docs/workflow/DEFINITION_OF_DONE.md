# Definition of Done + QA & Code-Review Checklists

A task/segment/phase is **done** only when it passes the relevant checklist below. "It
builds" is not done.

## Per-task DoD

- [ ] Implements exactly its acceptance criterion; no scope creep.
- [ ] `npm run build` and `tsc --noEmit` pass with no new errors/warnings.
- [ ] New logic has tests (unit for pure functions, integration for data paths).
- [ ] Pipeline scripts touched are **idempotent** and re-runnable; `selftest.py` passes.
- [ ] No secrets in the client bundle; no service-role key reachable from the browser.
- [ ] Commit message follows `v2.<s>.<t> <scope>: <summary>`, no AI attribution.

## Per-segment QA checklist (cross-cutting, every UI segment)

- [ ] **Responsive**: works 320px → 1920px; no overflow, no clipped numbers in cells, no
      visible container/hero seams. Test 360 (mobile), 768 (tablet), 1280, 1920.
- [ ] **Reduced motion**: every animation has a static fallback under
      `prefers-reduced-motion: reduce`.
- [ ] **Accessibility**: keyboard-navigable, visible focus rings, semantic landmarks,
      `aria` where needed, contrast ≥ WCAG AA (AAA for body text where feasible),
      color is never the only signal (colorblind-safe). See `docs/design-system/ACCESSIBILITY.md`.
- [ ] **Themes**: correct in light, dark, and system; accent-derived tokens hold up.
- [ ] **Empty/loading/error states**: render gracefully with no backend / no keys.
- [ ] **Performance**: no layout shift (CLS≈0), interactions < 100ms, animations 60fps.

## Per-phase verification (the 8-step finish, abbreviated)

QA (full phase) → `/code-review` (full diff) → commit → merge to `main` + tag → delete
branches → review all docs → archive phase docs → write brainstorming file. Full detail in
`GIT_WORKFLOW.md`.

## Code-review focus (what `/code-review` must check)

- Correctness & edge cases; error propagation (no silent failures).
- Security: input validation, authz on every protected path, no secret leakage, RLS
  coverage on new tables (`docs/security/SECURITY.md`).
- Performance: query shape (no N+1), payload size, render cost.
- Maintainability: small focused units, clear boundaries, no dead code, no premature
  abstraction (ponytail lens — is there a simpler one-liner?).
- Tests: meaningful assertions, edge cases, not coupled to implementation details.
- Project standards: matches conventions in `CLAUDE.md` and the design system.

## Performance budgets (enforced from v2.1 on)

| Metric | Budget |
|--------|--------|
| LCP (mobile, 4G) | ≤ 2.5s |
| CLS | ≤ 0.05 |
| INP | ≤ 200ms |
| JS shipped to homepage | ≤ 180KB gzip |
| Players-tab initial payload | ≤ 60KB (compact list; details lazy) |
| Lighthouse (Perf/A11y/Best-Practices) | ≥ 95 each |
