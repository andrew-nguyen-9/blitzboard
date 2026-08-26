# C00-claude — baseline and contract (production)

## Identity

- base SHA (immutable baseline): `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- base tree: `56f214a1ba5beeab90dc5820cb82a243bc874a60`
- branch: `v6/bench-portfolio` (neutral name; no vendor/model tokens)
- worktree: `.worktrees/v6-prod`
- head SHA: recorded in the C00 commit itself (this file lands in it); owned diff below
- git identity: `Andrew <284437207+andrew-nguyen-9@users.noreply.github.com>`; no assistant attribution
- date: 2026-08-26

## Owned diff (C00 adds only; zero production code touched)

- `wishlist-v6-bench-portfolio.md` — byte-copy of review contract, sha256 `240c2e5c…21d451`
- `.orchestrator-v6/state.md`, `outcome-map.md`
- `.orchestrator-v6/experiments/promotion-v1.json` — byte-identical to reviewer copy, sha256 `020047cd…36d7f` (preserved unchanged)
- `.orchestrator-v6/receipts/baseline-freeze.txt`, `baseline-fixture-hashes.txt` (23 fixture files), `engine-pytest-full.log`
- `.orchestrator-v6/checkpoints/C00-claude.md` (this file)

## Claims

1. **Baseline verified.** Worktree created from exact SHA; `git rev-parse HEAD` = base SHA; review worktree HEAD equals the same SHA.
2. **Ownership boundaries respected.** Nothing under `.worktrees/v6-review` read-modified; reviewer branch untouched; fresh `.orchestrator-v6/` (v5 `.orchestrator/` not reused).
3. **Promotion manifest frozen.** Copied byte-identical (hash match above); no amendments.
4. **Reviewer findings independently reproduced at code level:**
   - `byeCoverage` (`frontend/lib/benchScore.ts:197`): scalar compare of candidate bye vs same-position starter bye only; no roster-slot/FLEX eligibility; shared bye still credits 0.25 — confirmed.
   - `handcuffValue` (`frontend/lib/benchScore.ts:181`): contingency inferred purely from own-roster positional depth + starter injury status; no team/succession evidence — confirmed.
   - Fixed `DEFAULT_POLICY.overfillDepth` (`frontend/lib/draftAI.ts:133`, used `:405`) sole authority — confirmed.
   - `_run_waivers` (`engine/blitz_engine/simulation/season_eval.py:530`): reactive-only; `break` when `_first_hole` returns None; docstring lists deliberate omissions — confirmed.
   - `fixtures/bench_shape.json`: 16 rows; has `version:1`/`year`/`seed` but NO `schema_version`, NO `source_hash`, no evidence-status or league key — confirmed. Blocked slice `t14-2qb-std-te0.5-b4-ir1` present in rows.

## Verification (exact commands, from `.worktrees/v6-prod`)

| Suite | Command | Result |
|---|---|---|
| frontend deps | `cd frontend && npm ci` | exit 0 |
| frontend build | `cd frontend && npm run build` | pass |
| frontend typecheck | `cd frontend && npm run typecheck` | pass |
| frontend lint | `cd frontend && npm run lint` | pass; 1 pre-existing `react-hooks/exhaustive-deps` warning in `lib/useEspnSync.ts` (matches reviewer) |
| frontend tests | `cd frontend && npm test` | **52 files / 441 tests all pass; vitest EXITS 1** with `Error: [vitest-worker]: Timeout calling "onTaskUpdate"` — reproduced twice (matches reviewer's nonzero exit; reviewer counted 449 assertions, this run reports 441 tests) |
| pipeline | `cd pipeline && /abs/main/pipeline/.venv/bin/python -m pytest -q` | 146 passed (matches reviewer). NOTE: collection ERRORS with `FileNotFoundError: node_modules/.bin/tsx` if frontend `npm ci` has not run in the worktree (`test_backtest_sim_bridge.py`, `test_vault_crossimpl.py` shell out to tsx at import time) |
| engine lint | `cd engine && /abs/venv/python -m ruff check .` | All checks passed |
| engine tests | `cd engine && PYTHONPATH="$PWD" /abs/main/pipeline/.venv/bin/python -m pytest -q` | **4123 passed, 1 skipped, exit 0 — twice** (733.99s, 450.68s; second run logged at `receipts/engine-pytest-full.log`) |

## Failures and open items

1. **Frontend vitest nonzero exit (carried forward).** All tests pass but process exits 1 both runs with `[vitest-worker]: Timeout calling "onTaskUpdate"`. Deterministic-failure policy question for reviewer: harness bug vs blocking failure. DoD scripting must not mask it.
2. **Reviewer's `tests/test_corpus.py` failure NOT reproduced.** Three runs here: isolated `pytest tests/test_corpus.py` → 44 passed (incl. `test_generator_reproduces_one_row_byte_for_byte`, which shells `tsx scripts/gen-golden-drafts.mjs --check` and passed byte-for-byte); two full runs → green. The 1 stable full-run skip is `tests/test_league_sim.py:346` full sweep (`BLITZ_EVAL_FULL=1` gate), expected. Known environmental trap recorded: the corpus generator test silently SKIPS when `frontend/node_modules/.bin/tsx` or `node` is absent from PATH — a run in a worktree without `npm ci`, or a shell without node on PATH, does not exercise it. Hypotheses for reviewer's stopped-run failure: incomplete/absent frontend `node_modules` at test time, or contention with a concurrent frontend run (the generator subprocess has a 600s timeout and runs in `frontend/`). Needs reviewer-side rerun with environment recorded; baseline here is green.
3. **Known v5 regressions carried forward** (also in `outcome-map.md`): `t14-2qb-std-te0.5-b4-ir1` −25.3 pts/season (p=0.0025), guarded by `engine/tests/test_roster_shape.py:241` (`test_derived_numbers_beat_the_v4_hand_set_constants` asserts it stays negative — flipping it positive FAILS the suite until re-measured); reactive-only waivers; fixed overfill; scalar bye credit; depth-only handcuffs; unversioned bench shape; no promoted static-fit candidate.
4. **Secrets/portable-path scan:** no service-role key or hardcoded `/Users/<name>` paths in production sources (grep receipts reproducible from commands in this file).

## Artifacts

- `receipts/baseline-freeze.txt` — base SHA, tree, contract + manifest sha256, freeze timestamp
- `receipts/baseline-fixture-hashes.txt` — sha256 of all 23 `fixtures/` files (incl. `bench_shape.json` `b672610e…d2ee`, 16 golden drafts, seasons)
- `receipts/engine-pytest-full.log` — full engine run tail

## Next work (blocked until independent C00 verdict)

- C01: candidate-aware max-matched weekly slot coverage (no shared-bye credit, slot eligibility); structured contingent-role evidence (RB succession; QB authoritative depth; WR/TE explicit transfer only). No numerical tuning.
- Stop point honored: no merge, no C01 implementation, no push/PR/branch mutation.
