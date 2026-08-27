# C05D — auxiliary authority — producer checkpoint

Append-only. Bounded correction of the reviewer BLOCK at
`25074738980d5e5589b46a02a02f28ee5513b826` (`C05C-codex.md`), which accepted C05C's measurement
reconstruction and confirmation replay but blocked the auxiliary boundary: `write_fit_verdict`
hash-pinned caller-provided deterministic/calibration/runtime JSON without validating its authority,
so fabricated evidence plus an empty `{}` runtime produced `verdict: "pass"`. No frozen file edited;
nothing authoritative run.

- producer branch: `v6/c05d-auxiliary-authority`, based on `37ed8b3` (C05C head)
- reviewer BLOCK source: `25074738`
- reviewer probe `test_v6_c05c_auxiliary_authority_adversarial.py` copied byte-for-byte
  (sha256 `cd4e8c62ae2124743b6e0c79a33a27385b6f7a7d4d79b67a0d298ba38049bb30`) and passes unchanged

## Scientific disposition (unchanged)

C05 remains **parked**, v5 **preserved**. Because the frozen manifest freezes no accepted calibration
**report** identity (the C02 report failed; `missing_report_interpretation` is numerical_fail), no
caller dictionary can prove calibration acceptance — so promotion is mechanically unreachable and the
fit verdict cannot emit `pass`. No authoritative run, policy bridge, manifest change, calibration
reinterpretation, merge, PR, or push.

## Reviewer blocker → fix

`validate_auxiliary(effective, frame_sha, *, deterministic, calibration, runtime)` — one shared
validator used by both writing and confirmation — admits an auxiliary receipt only if it is
well-formed, of the correct `kind`, bound to the frozen protocol (`effective_v4_manifest_sha256`)
AND to this exact fit frame (`fit_frame_sha256` = fingerprint of the sorted measurement hashes), and
carries mechanical `produced_by_tooling` provenance. Anything else is dropped to **absent**, which
the frozen gates can never promote (byte-hash pinning proves retention, not authority):

- **runtime**: requires finite, nonnegative `wall_clock_hours` and `peak_rss_gib`. `{}`, missing
  keys, non-finite, negative, and wrong-type values are dropped — so the frozen limits gate can no
  longer read a zero default as within-limits.
- **deterministic**: requires `invariants_pass` true and no leakage/nondeterminism.
- **calibration**: never admitted from a caller dictionary (no frozen accepted-report identity to
  bind to). The source-identity checks are in place for the day an accepted report is frozen.

`write_fit_verdict` computes the frame fingerprint, validates aux, and feeds only authoritative
evidence to `evaluate_promotion`; it records `fit_frame_sha256`. `require_fit_verdict` recomputes and
re-verifies the fingerprint, re-verifies the pinned aux bytes, then **revalidates** aux authority
before the replay — a forged `pass` record with fabricated aux is refused because the recomputed
report is not `promote`.

## Requirement → test

| Requirement | Tests (`test_v6_c05d_auxiliary_authority.py` unless noted) |
|---|---|
| runtime provenance/schema; missing never passes | `test_runtime_valid_is_kept`, `test_runtime_unauthoritative_is_dropped` (6 params), `test_runtime_missing_keys_never_default_to_pass` |
| deterministic provenance/schema | `test_deterministic_valid_is_kept`, `test_deterministic_unauthoritative_is_dropped` (6 params) |
| calibration acceptance required | `test_calibration_bare_dictionary_is_never_admitted` |
| fabricated aux never promotes (writer) | reviewer `test_fit_verdict_never_promotes_fabricated_auxiliary_evidence` |
| shared validator + revalidate before replay | `test_confirm_refuses_forged_pass_by_rerun`, `..._missing_measurement`, `..._auxiliary_drift`, `..._frame_fingerprint_drift` |
| unbound aux never promotes | `test_v6_c05c_fit_analysis_authority.py::test_identical_arms_never_pass`, `..._failed_calibration_never_promotes` |

`evaluate_promotion` / `report_hash` / `calibration_gate` (gates.py) are consumed, not reimplemented.

## Verification

- All promotion + every C05 test file: **125 passed** (`C05_PROD_ROOT` set) — incl. all reviewer
  probes byte-for-byte.
- Frozen files byte-for-byte preserved (`shasum -c` OK): manifests, `execution.py`, `runner.py`,
  `manifest.py`, `gates.py`, `stats.py`, `season_eval.py`. Frozen diff empty. Accepted C05A/B/C
  behaviour intact.
- Only additive/edited changes vs `37ed8b3`: `harness_v4.py`, the reviewer probe (copied), the C05D
  test, and the C05C test (fabrication-based promote/confirm tests replaced — that fabrication was
  the hole).
- Producer-authored Ruff scope clean.
- Full engine regression: recorded on completion (session log).

## Still blocked (unchanged)

Authoritative fit/confirmation remains prohibited pending independent re-review PASS of C05D and a
NEW accepted calibration report (the failed C02 report stands). Held locally for review; no
push/merge/PR per the reviewer boundary.
