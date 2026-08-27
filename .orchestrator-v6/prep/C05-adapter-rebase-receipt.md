# C05 adapter — rebase onto accepted C02 (2026-08-26)

Executed per `C05-adapter-rebase-plan.md` after Andrew's acceptance notice: C02 accepted at
production head `417af276dd4438d8a35f38d08bfc26206044925e` (review commit `f2a1537`).

## What was done

1. Removed the old disposable worktree/branch (old tips `82b7705`→`e9b9f7a`/`a79af01`/`996125e`
   preserved on their original refs; the C05 manifest commit `82b7705` is untouched and its
   `promotion-v3.json` remains byte-identical, sha256 `bbb24160…6bd941ab`).
2. Recreated `v6/c05-c02-adapter` at `.worktrees/v6-c05-c02-adapter` from `417af276`.
3. `git cherry-pick 82b7705 a79af01 996125e` → `a3227c5`, `5b89614`, `2c35ddb`. Zero conflicts
   (new-files-only diffs, as the plan predicted); no C05 path claimed by C02.

## Semantics check at the accepted head

- `per_season` netting formula unchanged (`season_pts − waiver_cost × (emerg + upside)`;
  `waiver_cost` default 0.0, now also a decision gate — a claim executes only when its expected
  remaining-horizon gain repays the cost). Adapter mapping unaffected; `INTERFACE_MISMATCHES`
  item 2 wording still accurate, so no follow-up text commit was needed.
- `SeasonEvalResult` paired families (`per_season_h2h`/`per_season_playoff`/`per_season_champ`,
  `playoff_rate`/`champ_rate`) unchanged; `calibration/report.json` present and still maps.
- Board-corpus fixture hashes still verify against `promotion-v3.json` (asserted by the test
  suite), so no v4 amendment is forced by the accepted tree.

## Verification (from `engine/`, worktree-safe form)

- `PYTHONPATH="$PWD" <main pipeline venv>/python -m pytest tests/test_promotion.py
  tests/test_promotion_adapter.py -q` → **37 passed** (26 C05 self-tests + 11 adapter tests,
  all synthetic/non-authoritative; includes the real accepted calibration report still failing
  the frozen calibration gate — provisional-era conservative behaviour carries over unchanged).
- `ruff check blitz_engine/promotion tests/test_promotion*.py` → clean.

## Still blocked (unchanged)

No combined candidate SHA frozen, no `promotion-v3-exec-v1.json`, no authoritative promotion —
all await C03 and C04 PASS.
