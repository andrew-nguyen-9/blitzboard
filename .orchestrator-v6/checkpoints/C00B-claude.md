# C00B-claude — harness correction after C00A BLOCK (production)

## Identity

- responds to: `.worktrees/v6-review/.orchestrator-v6/checkpoints/C00A-codex.md` (BLOCK on `52ee1c47`, verdict commit `a2984d2`)
- base of corrections: `52ee1c47e69d746510470d179ef3eb7c53367cff`; correction commit = the commit containing this file
- scope: harness correction only; the three accepted C00A corrections are untouched; no C01, no merge/push, no reviewer files
- git identity: Andrew; no assistant attribution; date 2026-08-26

## Why `maxWorkers: 4` was insufficient (agreed diagnosis)

The reviewer's failing run (longest worker 89.54s) exposes the true mechanism: the RPC timeout is
armed in the WORKER, and a reply that arrives while the worker is inside a long synchronous block
sits unprocessed until the block ends — at which point the expired 60s timer can fire ahead of the
queued reply. So ANY single synchronous stretch that concurrent load dilates past ~60s can fail a
green run, at any worker count. Each full-draft test was one such stretch: a 192-pick
`runSnakeDraft` call, ~15–30s nominal, >60s under the synchronized-worker load this contract
intentionally creates. Concurrency tuning cannot bound that; the block itself had to be broken.

## Structural correction

`frontend/lib/snakeDraft.ts`: the draft loop moved verbatim into a private generator
(`snakeDraftPicks`) yielding one pick at a time.

- `runSnakeDraft` (production/live-board API, also `scripts/draftSim.ts` + `scripts/simulate.ts`):
  now drains the generator synchronously — same signature, same pick order, same rng consumption,
  behavior identical.
- `runSnakeDraftAsync` (new): drains the generator awaiting `setImmediate` between picks. The
  longest synchronous stretch inside a test drops from a whole draft to ONE pick (~100ms nominal);
  no plausible load dilates one pick to 60s, so queued RPC replies are processed within
  milliseconds-to-seconds of arrival, always inside the timeout window.

Heavy full-draft tests now use the async driver (`draftAI.sim.test.ts`,
`draftAI.fixtures.test.ts`, two full-sim + backtest sites in `draftAI.test.ts`); the UI-path suite's
own local loop (`draftAI.candidatePool.test.ts::runViaCandidatePool`) yields per pick the same way.
Not suppressed, not skipped, not weakened: RPC timeout untouched, reporter untouched, `"test":
"vitest run"` untouched, every assertion identical, still 52 files / 441 tests. `maxWorkers: 4`
retained (contention hygiene; no longer correctness-bearing).

## Verification under concurrent CPU-heavy repository checks

Load window (receipts in `.orchestrator-v6/receipts/`, all committed — receipts now use `.txt`
because the repo ignores `*.log`, per the C00A reconciliation note):

- concurrent check A: full engine pytest — ran 12:24→12:34, **4123 passed, 1 skipped, exit 0** (`engine-under-load-run.txt`)
- concurrent check B: `npm run build` — exit 0 (`build-under-load-run.txt`)
- concurrent check C: a second simultaneous plain `npm test` (the literal synchronized-workers scenario)

Plain `npm test` results, all **exit 0, 52 files / 441 tests passed**:

| run | started | concurrent load | duration | receipt |
|---|---|---|---|---|
| 1 | 12:24:31 | engine pytest + next build | 127.17s (tests 235.96s) | npm-test-under-load-1.txt |
| 2 | 12:26:51 | engine pytest | 95.79s | npm-test-under-load-2.txt |
| 3a | 12:28:47 | engine pytest + npm test 3b | 151.39s (tests 315.05s) | npm-test-under-load-3a.txt |
| 3b | 12:28:39 | engine pytest + npm test 3a | 153.09s | npm-test-under-load-3b.txt |

Test-phase time dilated up to ~3× (315s vs ~110s idle) — the load was real, and no run emitted
`onTaskUpdate` errors. Quiet-machine `npm test` after the refactor: exit 0, 52.88s.

## Regression safety of the refactor

- `npm run typecheck` pass; `npm run lint` pass (same single pre-existing `useEspnSync.ts` warning).
- Sync `runSnakeDraft` behavior: engine `tests/test_corpus.py` re-run post-refactor — 44/44
  including `test_generator_reproduces_one_row_byte_for_byte` (goldens byte-identical).
- Diff bounded to `lib/snakeDraft.ts` + four test files (58 insertions, 29 deletions) + records.

## Next

Awaiting independent re-review. C01 remains not started.
