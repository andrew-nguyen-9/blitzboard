# C05C fit-analysis authority — independent review

Verdict: **BLOCK**

- reviewed producer head: `37ed8b361f882abf09f6bdbcedf2ae4e24ca0b23`
- C05B base: `2b0ae60ca2f61623597abf9cccc75a257e55210f`
- prior reviewer BLOCK: `6fc72cb9b7951e8cfee100186364bfe78bd1132c`

## Accepted corrections

C05C closes both C05B report-authority blockers. `write_fit_verdict` no longer accepts a caller
report: it validates the exact 3456-cell fit frame, reconstructs the frozen `ArmRun` pairs, and
calls frozen `evaluate_promotion`. `require_fit_verdict` reloads and revalidates every pinned
measurement, reruns that analysis, compares the canonical report hash, and requires a recomputed
`promote`. The C05B compatibility alias is preserved.

All three prior reviewer probes are byte-for-byte unchanged and pass. The producer focused suite
passes 107/107; producer-authored Ruff scope passes; the full engine suite passes 3858 with 2
skipped; `git diff --check` passes; the frozen paths remain unchanged from the C05B base; and the
producer tree is clean. These corrections are accepted.

## Deterministic blocker

### Caller-authored auxiliary documents still decide promotion

The new writer JSON-loads the caller-supplied deterministic, calibration, and runtime paths and
hashes their bytes, but it never validates their schema, provenance, source authority, or binding
to the accepted run. `_run_fit_analysis` then supplies those unvalidated dictionaries directly to
frozen `evaluate_promotion`. Hash pinning proves retention of the chosen bytes, not that those bytes
are an authoritative receipt.

The independent `test_fit_verdict_never_promotes_fabricated_auxiliary_evidence` probe supplies a
fabricated passing deterministic dictionary, a fabricated already-mapped calibration dictionary,
and an empty runtime dictionary. The public writer emits `verdict: "pass"`. In particular, the
frozen limits gate defaults missing runtime values to zero, so `{}` is interpreted as within both
limits. The probe fails deterministically with `assert 'pass' != 'pass'`.

This bypasses the C05B requirement to consume the actual deterministic, calibration, and
runtime/memory receipts and the frozen prerequisite that calibration promotion depend on a new
accepted passing report. The producer's positive test also demonstrates the gap by fabricating all
three auxiliary inputs rather than proving their authority. Requirements 4, 5, and 6 therefore
remain open at the auxiliary boundary.

## Required C05D correction

Keep the accepted C05C measurement reconstruction and confirmation replay, but make every
auxiliary input mechanically authoritative:

- validate or produce the deterministic receipt from the frozen probes, with required schema,
  tool/run identity, and bindings to the evaluated frame;
- derive calibration evidence from an actual accepted calibration report through the frozen
  adapter, pin its source report and snapshot identities, and prove acceptance; do not admit a bare
  caller-authored already-mapped dictionary;
- require actual finite, nonnegative wall-clock and peak-RSS measurements with tool/run/frame
  bindings; missing keys, `{}`, malformed values, and non-finite values must never pass;
- use one shared auxiliary validator in both writing and confirmation, pin the exact source
  documents, and revalidate them before replay;
- copy the independent C05C auxiliary-authority probe unchanged and add coverage for missing
  runtime keys, fabricated calibration, provenance drift, source drift, and malformed values.

C05 remains parked and v5 preserved. No authoritative run, policy bridge, manifest change,
calibration reinterpretation, merge, PR, or push is authorized.
