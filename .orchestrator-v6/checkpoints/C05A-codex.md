# C05A v4-harness authority correction — independent review

Verdict: **BLOCK**

- reviewed producer head: `ce0758bf4b94885d1df580a55cef679c6dd4d1eb`
- base harness checkpoint: `af24062e30c20fd06eb54654968cd89126961a57`
- prior review: `6c63808b02ed8018c11a6f34a65ab25e4ed327ef`

## Accepted corrections

The nine-commit correction is isolated to the planned harness, tests, plan, and checkpoint paths.
Frozen files and accepted policy surfaces are unchanged. The unchanged reviewer authority probe
passes 2/2; the C05A focused correction suite passes 18/18; the combined C05 suite passes 79/79;
the declared Ruff scope, diff check, and clean-tree checks pass.

C05A correctly rejects draft/measurement authority mismatch, freezes authoritative sample inputs,
binds arm names to policy SHAs, recomputes seat-policy assignment, and binds draft receipts to the
v4/exec-v2/effective-v4 identity. Those prior blockers are closed.

## Deterministic blocker — forgeable fit verdict

`write_fit_verdict` unconditionally creates `{"verdict": "pass"}` for any caller-provided file
paths. It checks no receipt schema, authority flag, stage, arm/SHA identity, manifest binding,
measurement identity, complete frozen-frame coverage, pair integrity, numerical fit verdict, or
calibration result. The producer test demonstrates the defect by passing one dummy JSON document
containing only `{"kind": "measurement"}` and then treating the resulting verdict as sufficient
to unlock confirmation.

Hash-pinning arbitrary inputs prevents later mutation but does not prove that fit ran or passed.
This makes the new confirmation gate forgeable and deterministically blocks C05A acceptance.

## Required C05B correction

Keep the accepted C05A authority/binding corrections, but replace the verdict writer with a
validator/recorder that can emit `pass` only from a complete authoritative fit analysis:

- require the exact Cartesian frame: two frozen arms × two fit years × 216 league IDs × four base
  seeds, with one authoritative measurement receipt per cell and no extras or duplicates;
- validate every receipt's stage, authority, arm/SHA, measurement SHA, v4/exec-v2/effective-v4
  hashes, pairing keys, draft-receipt hash, and frozen `n_seasons=8` evidence;
- run or consume a hash-pinned fit analysis through the frozen promotion gates, including mandatory
  slices, hidden regressions, runtime/memory, and the unchanged calibration gate;
- record the actual verdict and refuse to emit `pass` for BLOCK, numerical failure, inconclusive,
  missing, incomplete, or failed-calibration evidence;
- make confirmation validate the fit-analysis receipt and its entire pinned input set;
- add the unchanged reviewer dummy-receipt probe and completeness/pairing/calibration adversarial
  tests, then stop for review.

C05 remains parked and v5 preserved. No authoritative run, policy bridge, new manifest,
calibration reinterpretation, push, merge, or PR is authorized.
