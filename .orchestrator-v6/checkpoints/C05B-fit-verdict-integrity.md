# C05B — fit-verdict integrity (PROVISIONAL — one item deferred, see below)

Append-only. Bounded correction of the reviewer BLOCK at `b7de57fc78678f251b24bd695b08ed3331f11c04`,
which accepted the C05A authority/frozen-frame/arm-SHA/seat-policy/v4-binding corrections but blocked
the fit-verdict for rubber-stamping `pass`. No frozen file edited; nothing authoritative run.

- producer branch: `v6/c05b-fit-verdict-integrity`, based on `ce0758b` (C05A head)
- reviewer BLOCK source: `b7de57f` (NOT yet transferred — see Deferred)

## ⚠ Deferred (blocked on transfer)

Req 8's **"copy the reviewer dummy-receipt probe unchanged from `b7de57f`"** is NOT done: commit
`b7de57f` is not on origin, not local, and not in Downloads. It must be pushed to origin by the
reviewer laptop, after which the probe is copied byte-for-byte and this checkpoint is finalized as
immutable. Everything else below is complete. The producer-side adversarial probes (completeness,
duplicate, pairing, numerical-failure, calibration-failure) are authored here; only the reviewer's
own probe is missing.

## Scientific disposition (unchanged)

C05 remains **parked**, v5 **preserved**. The frozen engine arms are identical over the whole matrix,
so `evaluate_promotion` yields `preserve_v5` by construction — which is exactly why the fit-verdict
must (and now does) refuse to emit `pass`. No authoritative run, policy bridge, new manifest,
calibration reinterpretation, merge, or PR.

## Requirement → fix → test

| Req | Fix (all in `harness_v4.py`) | Test |
|---|---|---|
| 1 | `write_fit_verdict` no longer writes an unconditional `pass`; verdict is derived | `test_write_fit_verdict_records_preserve_v5_not_pass`, `..._passes_only_on_promote` |
| 2 | `expected_fit_cells` (3456) + `assert_complete_fit_frame` — no missing/duplicate/off-frame | `test_expected_fit_cells_is_3456`, `test_frame_refuses_incomplete`, `..._duplicate_cell` |
| 3 | `validate_fit_measurement_receipt` — authority, fit stage, arm/SHA, measurement SHA, v4/exec-v2/effective-v4 hashes, pairing keys, draft-receipt hash, n_seasons=8 | `test_receipt_refusals` (8 params), `..._arm_policy_mismatch`, `..._missing_pairing_key`, `..._offframe_league` |
| 4 | `validate_fit_analysis_receipt` — consumes a hash-pinned `PromotionReport` from the frozen gates; verifies `report_hash`, fit/authoritative, `n_pairs=1728`, complete pinned input set | `test_fit_analysis_valid_returns_verdict`, `..._bad_report_hash`, `..._wrong_n_pairs`, `..._mismatched_pinned_set` |
| 5 | verdict = `pass` iff report verdict == `promote`; else the frozen-gate verdict | `test_write_fit_verdict_passes_only_on_promote` |
| 6 | missing/failed evidence never becomes pass; incomplete frame refuses | `test_write_fit_verdict_records_preserve_v5_not_pass`, `..._refuses_incomplete_frame` |
| 7 | `require_fit_verdict` re-validates the embedded fit-analysis receipt + complete pinned input set on confirm | `test_confirm_refuses_preserve_v5_fit`, `test_write_fit_verdict_passes_only_on_promote` (confirm admits) |
| 8 | producer-side adversarial probes added; **reviewer dummy-receipt probe deferred** (see above) | this file's suite |
| 9 | frozen files + accepted C05A corrections byte-for-byte | `shasum -c` below |

`evaluate_promotion` / `report_hash` / `calibration_gate` (gates.py) are consumed, not reimplemented.
`measure_arm` additively stamps `n_seasons` + `effective_v4_manifest_sha256` (needed by req 3).

## Verification

- Focused suite: **52 passed** — harness_v4 + C05A-accepted + C05B integrity + reviewer authority
  probe (2/2), `C05_PROD_ROOT` set.
- Frozen files byte-for-byte preserved (`shasum -c` OK): manifests, `execution.py`, `runner.py`,
  `manifest.py`, `gates.py`, `stats.py`, `season_eval.py`. Frozen diff empty.
- Only additive changes vs `ce0758b`: `harness_v4.py`, the C05B test, the C05A test (2 superseded
  auto-pass fit-verdict tests moved here), this checkpoint, and the plan.
- Frozen Ruff scope: all checks passed.
- Full engine regression: recorded on completion (see commit trailer / session log).

## Still blocked (unchanged)

Authoritative fit/confirmation remains prohibited pending: transfer of `b7de57f` + verbatim probe
copy, independent re-review PASS of C05B, and a NEW accepted calibration report (the failed C02
report stands). Stopped here for re-review. No merge/PR.
