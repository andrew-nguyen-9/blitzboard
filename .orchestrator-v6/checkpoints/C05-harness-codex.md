# C05 v4 harness independent checkpoint review

Verdict: **BLOCK**

- reviewed producer head: `af24062e30c20fd06eb54654968cd89126961a57`
- harness implementation: `44ec16b4348efc237686847f8a577af6d96a290c`
- accepted protocol-freeze review: `5a25d98de1681ca81dbe73441e9e4ac7f3d35d0b`
- independent Laptop 2 bundle SHA-256:
  `96cc9d0551abaa510b71f1df45de0a68cd258e80eda15edd6c0b32ac3ba6ef05`

## Reproduced evidence

The received bundle is valid, complete, and advertises exactly producer `af24062`, review
`5a25d98`, and its recorded main ref. The producer tree is clean and all frozen hashes match. The
full C05 harness suite passes 61/61 with `C05_PROD_ROOT` set, the frozen Ruff scope passes, and diff
checks are clean.

Laptop 2's all-zero diagnosis reproduces independently. Baseline and candidate implementations of
`draft_league`, `_pick`, and the season-evaluator slot wrapper are byte-identical. The only
draft-reachable engine difference is the `OP`/`SFLX` alias widening in `value/mcts.py`; none of the
432 generated matrix rows emits either alias. Both rehearsal boards and rosters are identical.
Holding the evaluator common therefore produces exact zero deltas by construction. This is a valid
engine-layer null, but it does not exercise the intended candidate policy in `frontend/lib/draftAI.ts`.

## Deterministic harness blockers

1. `measure_arm(authoritative=True)` accepts a draft receipt whose `authoritative` field is false.
   A rehearsal/probe draft can therefore be laundered into an authoritative measurement receipt.
2. Authoritative `n_seasons` remains a caller argument. The harness does not require the frozen
   value 8. It likewise does not require the base seed to belong to the four frozen seeds.
3. Draft validation does not bind `arm` to its frozen policy SHA. A receipt labelled `v5_shipped`
   with the candidate SHA passes all current validation.
4. Confirmation checks only year versus stage. It does not require a write-once recorded passing
   fit verdict before allowing confirm-stage draft or measurement receipts, despite the frozen
   ordering rule.
5. Draft receipts do not bind themselves to the v4 manifest/exec-v2 hashes, and their tooling
   provenance hashes the v3 effective manifest rather than the effective v4 chain. The later
   measurement receipt records v4 hashes, but that does not prove the draft was produced under the
   accepted v4 protocol.

These are authority and provenance failures. They deterministically block harness acceptance even
though the existing tests are green.

## Scientific disposition

Do not run v4 authoritatively after repairing the harness. The frozen engine-side arms are
behaviorally identical over the entire matrix, so the run is predetermined to produce zero primary
evidence and `preserve_v5`; it cannot answer whether the actual candidate draft policy improves v5.
The correct current disposition is to park C05 and preserve v5. A TypeScript-to-engine policy bridge
would exercise the intended variable, but it is new production behavior and a material experiment
change requiring separately authorized ownership, an append-only manifest, independent review, and
a new passing calibration report. No such work is authorized by this checkpoint.

## Required bounded correction

If the harness is retained as reusable infrastructure, correct it without editing frozen files:

- require draft and measurement authority flags to match, and reject authoritative use of any
  non-authoritative input;
- for authoritative receipts, derive `n_seasons`, allowed seeds, years, league IDs, arm names, and
  arm SHAs exclusively from the effective frozen manifest;
- enforce arm-to-policy-SHA identity and deterministic seat-policy assignment;
- require a hash-pinned, write-once passing fit-verdict receipt before confirmation;
- bind every draft receipt to v4, exec-v2, and an effective-v4-manifest hash;
- add reviewer probes for each refusal and stop at C05A for re-review.

No authoritative execution, policy bridge, new experiment version, calibration reinterpretation,
push, merge, or PR is authorized.
