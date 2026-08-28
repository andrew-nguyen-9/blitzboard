# C05 — v4 harness implementation checkpoint (2026-08-27, for independent harness review)

Append-only. Authorized by the exec-v2 freeze PASS (reviewer commit `5a25d98…`); implements ONLY
the protocol frozen by `promotion-v4.json` (sha256 `47af2905…`) + `promotion-v4-exec-v2.json`
(sha256 `7e88b090…`). Every frozen manifest/addendum/result and all accepted policy code
re-verified byte-for-byte; no authoritative fit or confirmation ran; no push/merge/PR.

## Commits

- `44ec16b` — `engine/blitz_engine/promotion/harness_v4.py` + 12 adversarial tests +
  byte-identical exec-v2 reviewer probe (sha256 `e06097b1…`).
- receipts commit (this record's commit) — non-authoritative v4 rehearsal receipts under
  `prep/c05-v4-rehearsal/` produced from committed clean head `44ec16b4348efc237686847f8a577af6d96a290c`.

## What the harness enforces mechanically

- Frozen-chain loading: v3 → v3-exec-v1 → v4 → v4-exec-v1 → v4-exec-v2, every file hash-pinned
  and every supersession hash link verified before anything is trusted.
- Stage 1 (draft): arm checkout HEAD verified against the frozen arm SHA; subprocess payload
  pins in-checkout import resolution (editable finder stripped, hard-asserted); write-once
  receipts under `draft/fit` / `draft/confirm`; `HeldOutGuard` before any work.
- Stage 2 (measure): measurement checkout HEAD must equal the frozen measurement SHA and all
  seven frozen file hashes must verify; exec-v2 roster rules enforced BEFORE the evaluator runs
  (exact per-seat size, board membership, global drafted-id uniqueness, eval-seed derivation,
  league/seat sanity; the undrafted board complement is the shared free-agent pool
  `evaluate_rosters` constructs by definition); write-once receipts under `measure/fit` /
  `measure/confirm` embedding the ArmRun, the draft receipt's sha256, and tooling provenance.
- Tooling provenance on every receipt: mechanically derived clean committed head containing the
  harness, execution-module sha256, effective-manifest sha256.

## Verification

- Adversarial refusal tests: 12 (tampered chain files; wrong measurement HEAD; measurement file
  drift and missing file; roster size; duplicate drafted ids; off-board ids; seat-count and
  league mismatch; wrong eval seed; non-draft receipt; held-out year in fit; fit year in
  confirm; tooling tree refused as measurement checkout).
- Full C05 suite from the committed head: **61 passed** (37 v3-era + 6 execution + 1 provenance
  + 13 harness + 4 reviewer probes — first, second, v4-exec-v2 probes byte-identical and
  unchanged, incl. `test_v6_c05_v4_exec_v2_freeze.py` sha256 `e06097b1…`).
- Frozen Ruff command (exec-v2 `blocker_3_ruff_gate`) passes, plus `harness_v4.py` and
  `test_promotion_harness_v4.py`; the reviewer-owned second probe remains excluded with its
  recorded E501.
- `git diff --check` clean per commit; tree clean at stop.

## Non-authoritative two-stage rehearsal (receipts in `prep/c05-v4-rehearsal/`)

Slice `t10-1qb-std-te0.0-b4-ir0` / 2021 / seed 2026082601 / n_seasons=1 (declared deviation):

- draft receipts from REAL verified checkouts: v5 `01f01d3c`, candidate `7b3fd735`; identical
  board `d5a2eca5…` (CRN holds); roster validation passed.
- BOTH rosters measured only through the frozen common evaluator at `7b3fd735` (file hashes
  verified) — **both arms now carry playoff AND championship samples**, the v4 design goal.
- measurement determinism: candidate receipt measured twice, ArmRun byte-identical.
- provenance: every receipt records tooling head `44ec16b…`, module sha256 `8e4c9787…`,
  effective-manifest sha256 `61f3a70a…`, clean tree.

## MATERIAL FINDING for the harness review (not resolved here — protocol-level)

On the rehearsed slice the two arms drafted **byte-identical rosters**, so every paired delta is
exactly 0.0. Mechanism verified by diffing the arm SHAs: `draft_league`/`_pick` and
`value/policy.py` are unchanged between `01f01d3c` and `7b3fd735`; the only draft-relevant diff
is a slot-alias widening in `value/mcts.py` (`OP`/`SFLX` → SUPERFLEX set) that is inert for
league-matrix rows (they use `SUPERFLEX`). The candidate's behavioral changes live in the
evaluator (held COMMON under v4 by design) and in the frontend TypeScript policy — for which
`static_proxy` is the documented stand-in (`season_eval.py` gotcha: e10 replaces it with the
real TS policy over the node bridge). Consequence: under the frozen engine-side policy mix, the
authoritative v4 experiment would compare identical drafts across all slices, yielding all-zero
paired deltas → structurally `preserve_v5` (inconclusive). The experimental variable is not
exercised by the engine policy mix alone. Resolution options (reviewer/Andrew's call; each is a
material protocol change requiring a new manifest version): wire the e10 TS policy bridge into
the draft stage per arm; or redefine the frozen policy identities to a surface that actually
differs between the arm SHAs. The harness itself is agnostic and ready for either.

## Still blocked

Authoritative fit/confirmation prohibited pending: harness review PASS, resolution of the
finding above, and a NEW accepted calibration report passing every inherited threshold (the
failed C02 report stands unreinterpreted). Stopped at this checkpoint.
