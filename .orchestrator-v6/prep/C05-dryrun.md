# C05 prep — verification commands and NON-AUTHORITATIVE dry-run results (2026-08-26)

Everything below ran in `.worktrees/v6-c05-prep` at base `b81541c` using the worktree-safe engine
form (worktree `PYTHONPATH`, main-checkout venv). **No result here is promotion evidence**; the
receipt file itself carries `"label": "SYNTHETIC / NON-AUTHORITATIVE — cannot justify shipping"`.

## Exact commands (from `.worktrees/v6-c05-prep/engine`)

| Step | Command | Result |
|---|---|---|
| focused tests | `PYTHONPATH="$PWD" /Users/andrew/Documents/GitHub/blitzboard/pipeline/.venv/bin/python -m pytest tests/test_promotion.py -q` | **26 passed** |
| lint (new code) | `.../.venv/bin/python -m ruff check blitz_engine/promotion tests/test_promotion.py` | All checks passed |
| suite collection | `PYTHONPATH="$PWD" .../.venv/bin/python -m pytest --collect-only -q` | 4150 collected (4124 pre-existing + 26 new; no collection errors) |
| dry run | `PYTHONPATH="$PWD" .../.venv/bin/python -m blitz_engine.promotion.dryrun ../.orchestrator-v6/prep` | OK — wrote `C05-dryrun-receipt.json` |

(`.../.venv` = `/Users/andrew/Documents/GitHub/blitzboard/pipeline/.venv`. Portable form:
`$HOME/Documents/GitHub/blitzboard/pipeline/.venv`.)

## Synthetic dry run (fabricated pairs, all 24 mandatory slices, fit + held-out confirm)

- fit verdict `promote`, confirm verdict `promote`, final `promote` — **stamped non-authoritative**
  (`authoritative: false`, synthetic data can never be authoritative).
- repeated analysis byte-stable: `byte_stable: true`; report hashes recorded in the receipt.

## Null dry run (REAL evaluator, identical arms, common random numbers)

- rows `t14-2qb-std-te0.5-b4-ir1` and `t10-1qb-std-te0.0-b4-ir0`, year 2021, base seed
  2026082601, `n_seasons=2` (declared protocol deviation, dry run only).
- determinism: one arm executed twice, byte-identical (`assert_deterministic` passed).
- CRN: every paired per-season matrix identical across arms → all deltas exactly zero.
- verdict `preserve_v5` (zero evidence is inconclusive and does not promote) — exactly the
  preregistered interpretation.
- runtime receipt: wall ≈ 8.8 s, peak RSS ≈ 0.16 GiB — far inside the frozen limits
  (12 h / 8 GiB), giving a first free-local-compute anchor for the full 216-row sweep.

## Self-test coverage (tests/test_promotion.py, all synthetic)

clear promotion passes; aggregate win + one regressing mandatory slice fails; H2H and
playoff/championship lower-bound violations fail; zero/inconclusive started-points evidence never
promotes; missing playoff proxies (C02 dependency) gate to `preserve_v5`; mismatched
boards/seeds/seats/eval-seed-derivation and identical arms raise `PairingError` before any
statistic; held-out 2018 in the fit stage raises `HeldOutLeakError` and the confirm stage refuses
fit years; authoritative mode refuses a null candidate SHA; missing/failing calibration reports
fail; limit violations fail; leakage/invariant failures BLOCK; repeated analyses are
byte-identical; `ArmRun` round-trips through JSON; manifest hash/board-corpus verification against
the repo fixtures passes.
