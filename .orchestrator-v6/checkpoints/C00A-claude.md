# C00A-claude — C00 BLOCK corrections (production)

## Identity

- responds to: `.worktrees/v6-review/.orchestrator-v6/checkpoints/C00-codex.md` (verdict BLOCK on commit `1954c902`)
- base of corrections: `1954c90227367e81f31df0fd70e68d005bb15751` (C00 commit)
- branch: `v6/bench-portfolio`; correction commit SHA is the commit containing this file
- git identity: Andrew; no assistant attribution
- date: 2026-08-26
- scope honored: only the four required corrections; no C01 implementation, no merge/push, no reviewer-owned files touched

## Correction 1 — `npm test` exits zero without hiding failures

**Cause (verified):** the auto-draft simulation test files are long synchronous CPU-bound blocks
(`testTimeout: 60000` was already raised for them). With no worker cap, vitest 3.2.6 (forks pool,
tinypool 1.1.1, node v26.0.0) runs 8 fork workers on 8 cores; the fully saturated event loops starve
the worker↔main birpc channel past its 60s ceiling, and the runner records
`Error: [vitest-worker]: Timeout calling "onTaskUpdate"` AFTER every assertion has passed → exit 1.

**Minimal harness correction:** `maxWorkers: 4` in `vitest.config.ts` (comment in file records the
cause). No test skipped, masked, filtered, or retried; reporter and `"test": "vitest run"` script
untouched.

**Evidence:** failing 2× at 8 workers (exit 1, 441 passed); green 2× at `--maxWorkers=4` then 1× via
plain `npm test` after the config change — `52 files / 441 tests passed, exit 0`, wall time 60.4s
(vs ~110–120s saturated). Typecheck and lint re-run clean (same single pre-existing
`useEspnSync.ts` exhaustive-deps warning).

## Correction 2 — both bye consumers mapped

`outcome-map.md` outcome 1 now names both shipped defective consumers:

- `frontend/lib/draftAI.ts:247` `byeCover` — counts distinct same-position starter byes; ignores the
  candidate's own bye and roster-slot eligibility; weighted into bench value at `draftAI.ts:307`.
- `frontend/lib/benchScore.ts:197` `byeCoverage` — scalar starter-bye compare; no slot eligibility;
  shared bye still credits 0.25.

Declared C01 plan (mapping only, no implementation yet): consolidate both onto one public
candidate-aware max-matched weekly coverage implementation consumed by both call sites, with tests
proving no divergent copy survives. The carried-forward risk list names both symbols.

## Correction 3 — `promotion-v2.json`

`.orchestrator-v6/experiments/promotion-v2.json` added; **v1 preserved byte-identical**
(sha256 `020047cd9c88b08a72efc95eac30d7f018022c10084d1135e4287dcb8e036d7f` re-verified after write).

Retained from v1 unchanged: arms, CRN pairing `[board, seat, season, seed]`, base seeds
`[2026082601..04]`, thresholds (started-points CI95 lower > 0; mandatory-slice tolerance 0.0; H2H
≥ −0.005; playoff/championship ≥ −0.002), blocked slice `t14-2qb-std-te0.5-b4-ir1`, metrics, and all
failure interpretations.

Newly frozen exact configuration:

- **board corpus:** pool = `season_eval.build_players(year, league_id)` over `fixtures/seasons/<year>.json`;
  initial board sorted by `(-projection, player_id)`; both arms draft from the identical board.
  All three season files + `fixtures/league_matrix.json` frozen by sha256 in the manifest.
- **board seeds:** draft rng = `default_rng(base_seed + 303)` (`season_eval._DRAFT_STREAM`); one base
  seed drives draft, injury, availability, and waiver randomness; identical in both arms.
- **seat set:** all seats `0..teams-1`; policy mix `("static_proxy","vorp_adp","engine_msv")` cycled
  then seed-shuffled; the same permutation in both arms (mirrored half-league per
  `value/roster_shape.measure`), every seat a matched pair.
- **scoring configs:** `std/half/ppr` × TE premium `{0.0, 0.5}`, as encoded per row in the frozen
  `league_matrix.json`.
- **mandatory league IDs:** exact enumeration of all 216 rows in the mandatory grid
  (teams {10,12,14} × {1qb,superflex,2qb} × {std,half,ppr} × TE {0.0,0.5} × bench {4,8} × IR {0,1});
  blocked slice verified present.

**Justified amendments (recorded in the manifest):** v1's seasons 2021–2025 (+2020 held out) are
unexecutable at the frozen baseline — `fixtures/seasons/` contains exactly 2018, 2021, 2024, and the
contract mandates local/free compute with no paid data. v2 therefore preregisters seasons
`[2021, 2024]` with `[2018]` held out, all frozen by hash. Adding corpus years later requires a v3
amendment; results never replace preregistration.

## Owned diff of the correction commit

- `frontend/vitest.config.ts` (maxWorkers + cause comment) — only production-tree file touched
- `.orchestrator-v6/experiments/promotion-v2.json` (new)
- `.orchestrator-v6/outcome-map.md` (outcome 1 + risk list amended)
- `.orchestrator-v6/state.md` (phase C00A, attempt 2)
- `.orchestrator-v6/checkpoints/C00A-claude.md` (this file)

`C00-claude.md` and `promotion-v1.json` unmodified (immutability preserved).

## Verification commands

- `cd frontend && npm test` → 52 files / 441 tests passed, exit 0 (three green runs post-fix)
- `cd frontend && npm run typecheck && npm run lint` → pass (pre-existing warning only)
- `shasum -a 256 .orchestrator-v6/experiments/promotion-v1.json` → `020047cd…36d7f`
- `python3 -c "import json; m=json.load(open('.orchestrator-v6/experiments/promotion-v2.json')); print(len(m['mandatory_league_ids']))"` → 216

## Next

Awaiting independent C00 re-review. C01 remains not started.
