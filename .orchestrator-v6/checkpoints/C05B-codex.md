# C05B fit-verdict integrity — independent review

Verdict: **BLOCK**

- reviewed producer head: `2b0ae60ca2f61623597abf9cccc75a257e55210f`
- C05A base: `ce0758bf4b94885d1df580a55cef679c6dd4d1eb`
- prior reviewer BLOCK: `b7de57fc78678f251b24bd695b08ed3331f11c04`

## Accepted corrections

The correction is isolated to the planned harness, tests, plan, and checkpoint paths. Frozen
manifests, `execution.py`, `runner.py`, `manifest.py`, `gates.py`, `stats.py`, and
`season_eval.py` remain byte-for-byte unchanged. The original reviewer dummy-receipt probe is
copied unchanged and passes. The producer focused suite passes 53/53, producer-authored Ruff scope
passes, the full engine suite passes 3852 with 2 skipped, and the producer tree is clean.

The new measurement validator proves authority, fit stage, frozen arm/SHA identity, measurement
SHA, v4/exec-v2/effective-v4 bindings, pairing keys, draft-receipt hash, `n_seasons=8`, and the
frozen cell coordinates. `assert_complete_fit_frame` rejects missing, duplicate, and off-frame
measurement cells before the producer writer records a verdict. These portions are accepted.

## Deterministic blockers

### 1. Caller-authored fit analysis still forges `promote`

`validate_fit_analysis_receipt` checks only a caller-computed hash plus `stage`, `authoritative`,
`n_pairs`, the effective-manifest hash, the caller's pinned-hash set, and the verdict token. It does
not prove that `evaluate_promotion` produced the report, require the frozen report schema, inspect
the gate set, or bind calibration, deterministic, runtime/memory, mandatory-slice, hidden-regression,
and numerical evidence.

The producer's own positive test constructs a five-field report with `gates: []`, computes
`report_hash` over that caller-authored dict, changes `verdict` to `promote`, and demonstrates that
`write_fit_verdict` emits `pass` and `require_fit_verdict` admits confirmation. Hashing arbitrary
caller input proves only that the same arbitrary input was retained.

The independent `test_fit_analysis_refuses_self_hashed_caller_authored_promote` probe supplies the
complete 3456-hash input cardinality with that forged report. It fails because no `ExecutionError`
is raised. Requirements 4, 5, and 6 remain open.

### 2. Confirmation admits a one-file hand-written pass record

`require_fit_verdict` rehashes whatever paths appear in `fit_receipt_sha256`, but it never parses
those documents, calls `validate_fit_measurement_receipt`, or calls `assert_complete_fit_frame`.
It also accepts the embedded caller-authored fit analysis above. A hand-written `fit-verdict.json`
can therefore pin one arbitrary JSON file, carry the forged `promote` report, and unlock
confirmation.

The independent `test_confirmation_refuses_one_file_forged_pass` probe demonstrates this bypass.
It fails because `require_fit_verdict` returns the forged pass record. Requirement 7 remains open.

## Required C05C correction

Keep the accepted complete-frame and per-measurement validation, but remove caller-authored report
content as authority:

- reconstruct the two frozen `ArmRun` values for every validated cell, pair them with the frozen
  pairing path, and call frozen `evaluate_promotion` for authoritative fit analysis;
- load and hash-pin the actual deterministic, calibration, and runtime/memory receipts consumed by
  that call; missing or invalid auxiliary evidence must never promote;
- record the canonical report and its hash only after that mechanical evaluation;
- make confirmation reload every pinned measurement, revalidate the exact complete frame, rerun the
  same analysis from all pinned inputs, compare the canonical report hash, and require `promote`;
- copy the two independent C05B probes unchanged and add adversarial coverage for missing gates,
  forged verdicts, incomplete confirmation inputs, auxiliary-receipt drift, and failed calibration.

C05 remains parked and v5 preserved. No authoritative run, policy bridge, manifest change,
calibration reinterpretation, merge, PR, or push is authorized.
