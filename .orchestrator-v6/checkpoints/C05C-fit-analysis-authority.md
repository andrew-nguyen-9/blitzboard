# C05C — fit-analysis authority — producer checkpoint

Append-only. Bounded correction of the reviewer BLOCK at
`6fc72cb9b7951e8cfee100186364bfe78bd1132c` (`C05B-codex.md`), which accepted C05B's complete-frame
and per-measurement validation but blocked the fit analysis for trusting caller-authored report
content. No frozen file edited; nothing authoritative run.

- producer branch: `v6/c05c-fit-analysis-authority`, based on `2b0ae60` (C05B head)
- reviewer BLOCK source: `6fc72cb`
- reviewer probe `test_v6_c05b_fit_analysis_adversarial.py` copied byte-for-byte (sha256
  `45e8abe1db228d34af2cb2aa73d74dffb51eb127e7ee6f5b7b9b7bc332b1a137`) and passes unchanged

## Scientific disposition (unchanged)

C05 remains **parked**, v5 **preserved**. The frozen engine arms are identical over the whole matrix,
so the mechanically-produced `evaluate_promotion` report yields `preserve_v5` (zero started-points
evidence) — the fit verdict cannot and does not emit `pass`. No authoritative run, policy bridge,
manifest change, calibration reinterpretation, merge, PR, or push.

## Reviewer blocker → fix → test

### Blocker 1 — caller-authored fit analysis could forge `promote`
`validate_fit_analysis_receipt` no longer trusts a caller-computed hash + verdict token. The embedded
report must carry the complete frozen gate schema (`deterministic_checks`, `started_points_aggregate`,
`hidden_regression_rule`, `h2h_win_rate`, `playoff_proxy`, `championship_proxy`, `calibration_gates`,
`limits`) and a verdict the frozen rule re-derives from those gate statuses; a `gates: []` or partial
report, or a verdict inconsistent with its gates, is refused. Tests: reviewer
`test_fit_analysis_refuses_self_hashed_caller_authored_promote`, plus
`test_validate_refuses_missing_core_gate`, `test_validate_refuses_verdict_inconsistent_with_gates`.

### Blocker 2 — confirmation admitted a one-file hand-written pass
`write_fit_verdict` now **produces** the report mechanically: it reconstructs the frozen
`(candidate, control)` `ArmRun` pairs from the validated frame and calls the frozen
`evaluate_promotion` with hash-pinned deterministic / calibration / runtime evidence — no caller
report is accepted. `pass` is emitted only on a computed `promote`; missing/invalid auxiliary evidence
never promotes. `require_fit_verdict` reloads every pinned measurement, re-asserts the exact complete
frame, re-verifies the pinned auxiliary receipts, **reruns** the analysis from all pinned inputs,
compares the canonical report hash, and requires `promote`. Tests: reviewer
`test_confirmation_refuses_one_file_forged_pass`, plus `test_promote_frame_passes_and_confirm_admits`,
`test_identical_arms_never_pass`, `test_failed_calibration_never_promotes`,
`test_confirm_refuses_missing_measurement`, `test_confirm_refuses_auxiliary_drift`,
`test_confirm_refuses_recorded_hash_tamper`.

`evaluate_promotion` / `report_hash` / `calibration_gate` (gates.py) are consumed, not reimplemented.

## Verification

- Focused C05 harness suite: **107 passed** (`C05_PROD_ROOT` set, every `test_v6_c05*` file) —
  promotion + adapter + execution + harness_v4 + C05A-accepted + C05B integrity + all three reviewer
  probes (`test_v6_c05_harness_authority_adversarial`, `test_v6_c05b_fit_analysis_adversarial`,
  `test_v6_c05a_fit_verdict_adversarial`) + C05C authority + the three C05 freeze-adversarial probes.
- Accepted C05B reviewer probe `test_v6_c05a_fit_verdict_adversarial.py` (dummy receipt) kept green:
  `write_fit_verdict` retains the C05B `fit_measure_paths` alias. The full engine regression, not the
  focused subset, caught the missed file — fixed and re-verified.
- Frozen files byte-for-byte preserved (`shasum -c` OK): manifests, `execution.py`, `runner.py`,
  `manifest.py`, `gates.py`, `stats.py`, `season_eval.py`. Frozen diff empty. Accepted C05A/C05B
  behaviour intact.
- Only additive/edited changes vs `2b0ae60`: `harness_v4.py`, the reviewer probe (copied), the C05C
  test, and the C05B test (superseded caller-report integration removed; per-receipt/frame/validate
  coverage kept).
- Producer-authored Ruff scope clean (the byte-identical reviewer probe is excluded to preserve its
  source-commit import grouping).
- Full engine regression: recorded on completion (session log).

## Still blocked (unchanged)

Authoritative fit/confirmation remains prohibited pending independent re-review PASS of C05C and a NEW
accepted calibration report (the failed C02 report stands). Stopped here for re-review. Per the
reviewer checkpoint, **no push/merge/PR is authorized** — the branch is held locally for durable
review.
