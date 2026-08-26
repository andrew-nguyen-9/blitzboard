# C00A independent correction verdict

Verdict: **BLOCK**

Reviewed production commit: `52ee1c47e69d746510470d179ef3eb7c53367cff`

## Correction verdicts

| Required correction | Verdict | Independent evidence |
|---|---|---|
| Standard `npm test` exits zero | **BLOCK** | plain command passed all 52 files / 441 tests, then reproduced the same `onTaskUpdate` error and exited 1 with `maxWorkers: 4`; duration 90.99s, longest fixture worker 89.54s |
| Both bye consumers mapped/consolidation declared | PASS | diff names `draftAI.ts::byeCover` and `benchScore.ts::byeCoverage`, their call sites, and one-public-implementation C01 plan |
| promotion-v2 exact experiment freeze | PASS | 216 unique IDs exactly equal the canonical matrix filter; four hashes match; blocked slice present; seeds consistent; v1 hash unchanged |
| New immutable correction checkpoint | PASS | `C00A-claude.md` is committed; prior checkpoint and v1 are unchanged |

## Scope and integrity

- The correction diff is bounded to `frontend/vitest.config.ts` and four orchestration records.
- No C01 behavior was implemented.
- Commit author is Andrew and the production worktree is clean.
- `git diff --check` passes.

## Required correction before next review

The harness must remain green under ordinary concurrent local load, because Claude and the reviewer
are intentionally synchronized workers. Replace `maxWorkers: 4` with a demonstrably robust lower
concurrency or isolate the long synchronous draft simulations so they cannot starve worker RPC.
Do not increase or disable the RPC timeout, suppress unhandled errors, skip tests, or weaken
assertions. Run plain `npm test` while another CPU-heavy repository check is active, record exit 0,
and write a new immutable checkpoint such as `C00B-claude.md`. C01 remains blocked.
