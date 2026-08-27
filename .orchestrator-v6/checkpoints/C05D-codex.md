# C05D auxiliary authority — independent review

Verdict: **BLOCK**

- reviewed producer head: `36d395aefb4bb4683e9e8d7186d65c7f6fbbda47`
- C05C base: `37ed8b361f882abf09f6bdbcedf2ae4e24ca0b23`
- prior reviewer BLOCK: `25074738980d5e5589b46a02a02f28ee5513b826`

## Accepted corrections

C05D closes the empty-runtime fail-open path. One shared validator is called during both verdict
writing and confirmation replay; runtime receipts now require finite, nonnegative wall-clock and
peak-RSS values, so `{}`, missing keys, wrong types, negative values, and non-finite values are
dropped to absent. Confirmation also recomputes and checks the fit-frame fingerprint before replay.

All four prior reviewer probes are byte-for-byte unchanged and their six tests pass. The focused
promotion/C05 suite passes 125/125; producer-authored Ruff scope passes; the full engine suite passes
3876 with 2 skipped; `git diff --check` passes; the frozen paths remain unchanged from the C05C
base; and the producer tree is clean. These corrections are accepted.

## Deterministic blockers

### 1. Caller-mutated calibration authority produces and confirms `pass`

`write_fit_verdict` accepts the mutable caller-supplied `effective` dictionary as protocol
authority. `validate_auxiliary` reads `accepted_report_sha256` from that dictionary, then compares
only the caller's claimed receipt field to the same string. It never proves that `effective` is the
canonical hash-loaded frozen value and never hashes the embedded calibration `report` against the
claimed accepted-report identity.

The independent `test_fit_verdict_refuses_caller_added_calibration_authority` probe starts from the
real frozen effective value, adds an accepted-report token in memory, constructs the complete 3456
fit cells bound to that mutated value, and supplies fabricated deterministic, runtime, calibration,
and tooling content. The public writer emits `pass` / `promote`; a bounded confirmation replay also
returns `pass`. The checkpoint claim that promotion is mechanically unreachable is therefore false
at the public trust boundary.

### 2. A truthy caller value is treated as mechanical provenance

`_aux_bound` checks only `bool(doc.get("produced_by_tooling"))`. Any nonempty string or dictionary
passes. The producer's own positive fixtures institutionalize this by treating
`{"tooling_head": "abc"}` as valid provenance; no tooling head, clean-tree state, execution-module
hash, effective-manifest hash, probe output, or measurement source is mechanically verified.

The independent `test_auxiliary_refuses_caller_fabricated_tooling_provenance` probe supplies a
complete but fabricated provenance object. Both deterministic and runtime receipts are admitted.
Hashing the surrounding JSON still proves retention, not production authority.

## Required C05E correction

Use the shortest safe path while C05 is parked:

- remove the speculative calibration-admission branch and always drop calibration until an
  independently frozen, loader-bound accepted-report identity exists; do not add a policy bridge or
  change a manifest;
- do not let a caller-mutated `effective` dictionary create authority: load the canonical frozen
  chain internally or re-load and compare it before any verdict or confirmation decision;
- do not admit deterministic or runtime evidence based on provenance-shaped caller fields; either
  produce and bind those receipts mechanically in the harness or keep them absent until such a
  producer exists;
- if a later authorized phase admits calibration, hash the exact source report bytes, derive the
  gate input through the frozen adapter, and bind the accepted identity to that hash;
- copy the independent C05D probe unchanged and cover fabricated full provenance, mutated effective
  state, calibration report/hash mismatch, and confirmation replay.

C05 remains parked and v5 preserved. No authoritative run, policy bridge, manifest change,
calibration reinterpretation, merge, PR, or push is authorized.
