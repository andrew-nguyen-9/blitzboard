# C00 independent checkpoint verdict

Verdict: **BLOCK**

Reviewed production commit: `1954c90227367e81f31df0fd70e68d005bb15751`

The producer-blind review was frozen first in `reviews/C00-blind.md` at review commit `5df1b15`.
Claude's rationale and receipts were read only after that record existed.

## Requirement verdicts

| Requirement | Verdict | Evidence |
|---|---|---|
| Exact immutable base | PASS | production and review worktrees derive from `01f01d3c5f9c00a046edd43707db75ce1426c0e8` |
| Separate conflict-free ownership | PASS | production commit adds seven contract/state/receipt paths and no production code; review commit owns only adversarial/state paths |
| Fresh v6 state | PASS | `.orchestrator-v6/` used; v5 `.orchestrator/` unchanged |
| Contract and initial manifest parity | PASS | contract and promotion-v1 files are byte-identical across worktrees; hashes match receipts |
| Baseline artifacts frozen | PASS | fixture hashes are committed; code and shape hashes independently match |
| Known defects reproduced | PASS | both sides confirm scalar bye logic, depth-only contingent inference, fixed overfill, reactive waivers, and legacy shape schema |
| Known v5 regression carried | PASS | blocked `t14-2qb-std-te0.5-b4-ir1` is named with measured negative result |
| Clean repository DoD | **BLOCK** | `npm test` exits 1 reproducibly after passing assertions with `Timeout calling "onTaskUpdate"`; deterministic nonzero gates block under the operating contract |
| Unambiguous C01 ownership/evidence | **BLOCK** | production map assigns only `benchScore.ts::byeCoverage`; the required shipped defect and reviewer tests also target `draftAI.ts::byeCover` |
| Complete experiment freeze | **BLOCK** | promotion v1 says pairing includes `board` but names no board corpus or board seeds, names no seat set, and omits the scoring dimension from mandatory formats; exact executed configurations are therefore not frozen |

## Reconciliation notes

- Claude's corpus results agree with the approved independent rerun. The independent unapproved
  failure was tsx `listen EPERM`; the approved full engine suite passed the same corpus test. This is
  not a repository defect.
- Claude reports 441 frontend tests because the production branch does not contain the eight
  reviewer-owned adversarial tests. The review branch reports 449. This expected ownership
  difference is not a contradiction.
- Independent full results: frontend build/typecheck/lint pass; pipeline 146 pass; engine Ruff pass;
  engine 4,123 pass, 1 skip, 1 expected failure. Production independently reports matching results
  except that its baseline suite has no reviewer xfail.
- `engine-pytest-full.log` exists as an ignored runtime receipt and is not present in production
  commit `1954c902`; its committed summary is adequate for C00, but future immutable experiment
  result artifacts must not rely on ignored logs.

## Required correction before re-review

1. Make the repository's standard `npm test` command exit zero without suppressing, skipping, or
   hiding failed assertions. Record the failure cause and the minimal harness correction.
2. Amend the C01 outcome map to name both production consumers:
   `frontend/lib/draftAI.ts::byeCover` and `frontend/lib/benchScore.ts::byeCoverage`, or document and
   test their consolidation into one public implementation.
3. Create `promotion-v2.json`; do not overwrite v1. Freeze the exact board corpus/board seeds, seat
   set, scoring configurations, and exact mandatory league IDs. Retain all v1 thresholds, seasons,
   common-random-number pairing, blocked slice, and failure interpretations unless a change is
   explicitly justified.
4. Write a new immutable production checkpoint (for example `C00A-claude.md`) referencing the
   correction commit. Do not begin C01 or merge while C00 is blocked.
