# Git Workflow — phases, segments, tasks

The branching model maps 1:1 to the `v[phase].[segment].[task]` versioning. It mirrors how
a disciplined team ships: short-lived segment branches off a phase branch, reviewed and
merged continuously, with the phase landing on `main` only when whole and verified.

```
main ──────────────────────────────●──────────────────► (tags: v2.0.0, v2.1.0, …)
        \                          ↑ merge phase when DONE
         v2 (phase branch) ──●──●──●──────────────►
              \    ↑ push segment to parent (phase)
               v2.3-player-data (segment sub-branch) ──[tasks]──► review ─┘
```

## Starting a phase

1. From an up-to-date `main`: open the phase branch `git switch -c v2`.
2. Read the phase doc (`docs/phases/v2/v2.<n>-*.md`). It lists the segments and tasks.
3. Push the phase branch so it's visible: `git push -u origin v2`.

## Working a segment (the inner loop)

For each segment `v2.<s>`:

1. **Branch** — from the phase branch: `git switch -c v2.<s>-<slug>`.
2. **Build** — implement the segment's tasks (`v2.<s>.1`, `v2.<s>.2`, …). One task = one
   focused commit, message `v2.<s>.<t> <scope>: <summary>`.
3. **Test** — unit/integration tests for new logic; `npm run build` + `tsc --noEmit`;
   pipeline `selftest.py` where touched.
4. **QA** — manual pass against the segment's acceptance criteria + the cross-cutting QA
   checklist (`DEFINITION_OF_DONE.md`): responsive, reduced-motion, a11y, empty states.
5. **`/code-review`** — run the code-review skill on the segment diff; resolve findings.
6. **Commit** — finalize; ensure the tree is clean.
7. **Push to parent** — open a PR from `v2.<s>-<slug>` → `v2` (the phase branch), get it
   green, merge. Delete the segment sub-branch.

Segments merge into the phase branch continuously, so the phase branch always reflects
"everything done so far this phase."

## Finishing a phase (the outer ritual — all 8 steps)

When every segment of a phase is merged into the phase branch:

| # | Step | What it means |
|---|------|---------------|
| a | **QA testing** | Full-phase QA pass: every acceptance criterion across all segments, on mobile + desktop, light/dark, reduced-motion, keyboard-only. |
| b | **`/code-review`** | Run code-review on the whole phase diff (`main...v2`). Resolve everything. |
| c | **Commit** | Final cleanup commit on the phase branch. |
| d | **Merge to `main`** | PR `v2` → `main`; squash-or-merge per repo policy; tag `v2.<phase>.0`; GitHub Release. |
| e | **Delete old branches** | Delete the phase branch and any stragglers locally + remote. |
| f | **Review all documentation** | Re-read every doc touched; fix drift so docs match what shipped. |
| g | **Consolidate & archive phase docs** | Move the phase plan + notes into `docs/archive/v2/` with an "as-shipped" delta; update `PHASES_OVERVIEW.md` status. |
| h | **Brainstorming file** | Write `docs/brainstorming/v2.<phase>-ideas.md`: fixes, features, and ideas that surfaced during the phase, for the backlog. |

## Rules

- **Never commit to `main` directly.** `main` only receives finished, reviewed phases.
- **No interactive git** (`-i`) in this environment.
- Commit/push only when the work and review say it's ready.
- Keep segment branches short-lived (days, not weeks) — if a segment sprawls, split it.
- Commit messages and PR bodies carry **no AI attribution** (global rule).
- PRs use the template in `.github/PULL_REQUEST_TEMPLATE.md`.
