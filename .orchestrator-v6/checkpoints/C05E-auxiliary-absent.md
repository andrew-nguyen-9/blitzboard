# C05E — auxiliary absent — producer checkpoint

Append-only. Minimal correction of the reviewer BLOCK at
`181188f84718fe6033dc1ce85216fc056e075d86` (`C05D-codex.md`). C05D validated auxiliary receipts
against caller-shaped fields, which are not authority; C05E takes the shortest safe path while C05 is
parked: admit no caller auxiliary document at all. No frozen file edited; nothing authoritative run.

- producer branch: `v6/c05e-auxiliary-absent`, based on `36d395a` (C05D head)
- reviewer BLOCK source: `181188f`
- reviewer probe `test_v6_c05d_auxiliary_provenance_adversarial.py` copied byte-for-byte and passes
  unchanged

## Scientific disposition (unchanged)

C05 remains **parked**, v5 **preserved**. No auxiliary evidence is mechanically generated from
canonical frozen state yet, so all auxiliary inputs stay absent; the frozen gates read absence as
missing (calibration ⇒ numerical_fail), so promotion is mechanically unreachable and the fit verdict
never emits `pass`. No authoritative run, policy bridge, manifest change, calibration
reinterpretation, merge, PR, or push.

## Reviewer blocker → fix

`validate_auxiliary(effective, frame_sha, *, deterministic, calibration, runtime)` now returns
`{deterministic: None, calibration: None, runtime: None}` unconditionally. It admits nothing from a
caller document:

- **P0 (caller-mutated `effective` + fabricated calibration ⇒ pass):** the speculative
  calibration-admission branch (which read `accepted_report_sha256` from the mutable `effective` and
  compared only caller-claimed fields) is removed. Calibration is always absent — the frozen
  manifest freezes the calibration SOURCE identity but no accepted-REPORT identity, so nothing can
  prove acceptance. `effective` is no longer read as an authority source here, so mutating it creates
  no authority.
- **P1 (truthy `produced_by_tooling` accepted as provenance):** deterministic/runtime receipts are
  no longer admitted on provenance-shaped caller fields. A fabricated-but-complete provenance object
  is just more caller bytes; hashing them proves retention, not production authority.

`write_fit_verdict` and `require_fit_verdict` still compute and (confirm) re-verify the fit-frame
fingerprint and still feed the validated auxiliary (now always all-absent) to the frozen
`evaluate_promotion`. When a later authorized phase adds a mechanical producer (deterministic probes,
a measured runtime receipt, a loader-bound accepted calibration-report identity), evidence is
admitted here against its frozen-generated identity — not caller-shaped fields.

## Requirement → test

| Requirement | Test |
|---|---|
| fabricated full provenance never admitted | reviewer `test_auxiliary_refuses_caller_fabricated_tooling_provenance` |
| caller-mutated effective + fabricated calibration never `pass` (write + confirm) | reviewer `test_fit_verdict_refuses_caller_added_calibration_authority` |
| no caller deterministic/runtime admitted | `test_v6_c05d_auxiliary_authority.py::test_deterministic_is_never_admitted_from_caller`, `..._runtime_is_never_admitted_from_caller`, all `..._unauthoritative_is_dropped` params |
| calibration never admitted | `..._calibration_bare_dictionary_is_never_admitted` |
| confirmation revalidates + replays | `..._confirm_refuses_forged_pass_by_rerun`, `..._missing_measurement`, `..._auxiliary_drift`, `..._frame_fingerprint_drift` |
| unbound aux never promotes (writer) | `test_v6_c05c_fit_analysis_authority.py::test_identical_arms_never_pass`, `..._failed_calibration_never_promotes` |

`evaluate_promotion` / `report_hash` / `calibration_gate` (gates.py) are consumed, not reimplemented.

## Verification

- All promotion + every C05 test file: **127 passed** (`C05_PROD_ROOT` set) — incl. all five reviewer
  probes byte-for-byte.
- Frozen files byte-for-byte preserved (`shasum -c` OK): manifests, `execution.py`, `runner.py`,
  `manifest.py`, `gates.py`, `stats.py`, `season_eval.py`. Frozen diff empty. Accepted C05A–D
  behaviour intact.
- Only changes vs `36d395a`: `harness_v4.py` (validate_auxiliary reduced to admit-nothing; dead
  `_aux_bound`/`_finite_nonneg`/`math` removed), the reviewer probe (copied), and two C05D
  aux-validator tests inverted to assert absence.
- Producer-authored Ruff scope clean.
- Full engine regression: recorded on completion (session log).

## Still blocked (unchanged)

Authoritative fit/confirmation remains prohibited pending independent re-review PASS of C05E and a
NEW accepted calibration report (the failed C02 report stands). Held locally for review; no
push/merge/PR per the reviewer boundary.
