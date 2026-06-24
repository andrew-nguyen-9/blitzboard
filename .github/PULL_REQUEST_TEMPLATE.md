<!-- Title format: v2.<segment>.<task> <scope>: <summary>  e.g. "v2.3.2 players: keyset pagination" -->

## What & why
<!-- One paragraph. Link the phase doc: docs/phases/v2/v2.<n>-*.md -->

Version: `v2.__.__`  ·  Phase: `docs/phases/v2/____.md`  ·  Branch: `v2.__-____` → `v2`

## Changes
-

## Definition of Done (check what applies — see docs/workflow/DEFINITION_OF_DONE.md)
- [ ] Builds clean: `npm run build` + `tsc --noEmit`
- [ ] Tests added/updated and passing; pipeline `selftest.py` green (if touched)
- [ ] Responsive 360/768/1280/1920; **no clipped numerals**, no hero/container seams
- [ ] `prefers-reduced-motion` fallback for any animation
- [ ] Accessibility: keyboard, focus, semantics, contrast (AA), color not the only signal (axe clean)
- [ ] Themes correct: light / dark / system
- [ ] Empty / loading / error states render with no backend/keys
- [ ] Security: RLS on new tables, authz on mutations, no secrets in client bundle
- [ ] Perf budget met (Lighthouse ≥ 95; payloads within budget)
- [ ] `/code-review` run; findings resolved
- [ ] No AI attribution in commits/PR

## QA notes / screenshots
<!-- How you verified; before/after for UI. -->
