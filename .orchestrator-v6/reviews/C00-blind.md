# C00 producer-blind independent review

Status frozen before reading any Claude rationale: **INCONCLUSIVE**.

## Identity and scope

- Baseline: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`.
- Reviewed predecessor: `c2968ed02047370329b0cc64683e60a3358afffa`.
- The intervening 25 paths are the separately merged intelligence subsystem and do not overlap the
  v6 bench surfaces.
- Review branch changes are limited to the v6 operating contract, fresh orchestration state,
  independent runner, and new adversarial tests. No production file is edited.

## Requirement evidence

| C00 requirement | Independent status | Evidence |
|---|---|---|
| Immutable post-pruning base | proven | both v6 worktrees start at the SHA above |
| Separate worktrees | proven | `.worktrees/v6-prod` and `.worktrees/v6-review` |
| Fresh state | proven for review; production pending | `.orchestrator-v6/`; v5 `.orchestrator/` untouched |
| Eight-outcome ownership map | proven for review; production pending | `outcome-map.md` |
| Promotion preregistration | proven for review; production pending | `experiments/promotion-v1.json` |
| Same-bye defect | proven | strict desired assertion fails under `it.fails` |
| Missing-bye/FLEX/superflex gaps | proven | three strict desired assertions fail under `it.fails` |
| Broad handcuff behavior | proven | unrelated WR and RB injury sensitivity assertions fail |
| Fixed overfill authority | proven | exact v4 dictionary and config-insensitive penalty assertions |
| Reactive-only waiver limitation | proven | strict pytest expected failure for healthy-lineup upgrade |
| Known v5 risks carried | proven for review; production pending | `outcome-map.md` names blocked 14-team 2QB slice and failed fits |
| Clean baseline DoD | contradicted | Vitest worker RPC error reproduced twice after 449/449 pass |

## Frozen artifact observations

- `frontend/lib/draftAI.ts`: `6b223e646eb335711692faf70b1810e8e9a1a65fb514ccab46856bfdd3c108f1`
- `frontend/lib/benchScore.ts`: `3fee427889b85160b8061d8acdde0865d5d5b4238b10538d5afe2aed14e25f9f`
- `engine/blitz_engine/simulation/season_eval.py`:
  `40e92b88b5a30d033c1f0b415909ad3da9d889f86ed8c01d78eefb59b6fa5fa9`
- `fixtures/bench_shape.json`: `b672610e291aa97f5be7853c16c2e53db201f74638257acc40e7c129c46ad2ee`
- Shape fixture has 16 rows and top-level `version`, but no `schema_version` or `source_hash`.

## Exact verification

- `bash scripts/v6-independent-gate.sh`: 8 frontend tests passed; 1 strict pytest xfail.
- `npm run typecheck`: passed.
- `npm run lint`: passed with the pre-existing `lib/useEspnSync.ts:56` hook warning.
- `npm test`, twice: 53 files and 449 tests passed, then worker RPC timeout; exit 1.
- `npm run build`, with configured font network access: passed.
- `PYTHONPATH=engine ../../pipeline/.venv/bin/python -m pytest pipeline`, with local IPC access:
  146 passed.
- Engine Ruff plus full pytest, with local IPC access: Ruff passed; 4,123 passed, 1 skipped,
  1 expected failure in 741.54 seconds.
- The unapproved engine attempt's corpus failure was reproduced as tsx `listen EPERM`; it passed in
  the approved run and is environmental, not golden drift.

## Blind conclusion

The required defects, ownership split, baseline SHA, and independent experimental contract are
reproducible. C00 cannot receive `PASS` until the production checkpoint exists and the clean-base
gate either exits green or explicitly resolves the repeatable Vitest worker error without masking
assertion failures. No C01 production merge is authorized by this review.
