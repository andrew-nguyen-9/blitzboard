# v7 parking and post-v6 integration plan

v7 stays parked until C06 identifies one final accepted v6 land SHA. No v7 branch should be
rebased onto an intermediate C02/C03/C04 candidate.

## Existing v7 work inventory

| Unit | Branch/worktree | Current state | v6 overlap |
|---|---|---|---|
| manual-draft resilience | `v7/manual-resilience` | committed at `9d5a7bd` (two commits) | high: modifies `DraftWarRoom.tsx`, a C04 production surface |
| league-rules schema reconciliation | `v7/schema-reconcile` | committed at `e491eca` (two commits) | low file overlap, but its migration/docs must describe the final v6 league shape |
| draft-day runbook/freshness/smoke checks | `v7/draft-runbook`, `.worktrees/v7-codex` | uncommitted files on the main-based branch | low direct overlap; runbook references the eventual approved release |

The v7 work is based on main commit `4081ce7733cd4f19744d354b5f19068e63007212`,
not on v6. Preserve these branches and the uncommitted runbook work as-is until v6 lands.

## Post-C06 procedure

1. Record the final v6 land SHA and verify main contains it. Create a fresh v7 integration
   branch/worktree from that exact SHA; do not reuse the dirty main checkout.
2. Rebase or cherry-pick schema reconciliation first (`d9d94dc`, then `e491eca`). Reconcile
   the migration and architecture text against the final v6 league-config/bench-shape schema.
3. Rebase or cherry-pick manual resilience next (`c43aa72`, then `9d5a7bd`). Resolve
   `DraftWarRoom.tsx` semantically: retain all v6 scoring, structured explanations, evidence
   state, and browser-cost behavior while adding v7 persistence/edit/restore behavior.
4. Commit the runbook/freshness/smoke unit on its own branch before transfer. Then apply it
   after the two committed v7 units and update release-SHA/route assumptions to the combined
   tree rather than the old main checkout.
5. After each unit, run its focused tests plus the v6 regression gates it touches. After all
   three, run the full repository DoD and perform a new independent integration review.

## Required semantic checks

- Manual restore must preserve the final v6 league configuration and player-value wire units.
- Pick replacement must not duplicate drafted players or bypass v6 roster legality.
- Restored drafts must reproduce the same v6 recommendation/explanation output for identical
  board state and evidence artifacts.
- Schema reconciliation must preserve pipeline compatibility until an explicitly tested
  migration removes the legacy shape.
- Draft freshness must validate the final materialized player values and must not expose a
  service-role secret to the frontend.
- Runbook commands committed to the repository must use `$HOME`/`~`, never a user-specific
  absolute path.

## Stop conditions

Do not integrate v7 if C05 is failed/inconclusive without an adjudicated shipped v6 policy, C06
is not `PASS`, the v7 runbook worktree is dirty without an owned commit, or the fresh v7
integration tree cannot preserve both v6 and v7 tests. C05 preparation commit `82b7705...` and
its synthetic receipts are not a C05 verdict; v7 remains parked until the authoritative result
and C06 audit exist.
