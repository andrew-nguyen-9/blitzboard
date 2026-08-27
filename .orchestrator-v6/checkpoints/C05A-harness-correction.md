# C05A — v4-harness authority/provenance correction (for independent re-review)

Append-only. Bounded correction of the five deterministic blockers the independent reviewer raised
at **BLOCK** commit `6c63808b02ed8018c11a6f34a65ab25e4ed327ef`. No frozen file edited; nothing
authoritative run.

- producer branch: `v6/c05a-harness-correction`, based on `af24062e30c20fd06eb54654968cd89126961a57`
- reviewer verdict source: `v6/bench-portfolio-review` @ `6c63808`
  (`.orchestrator-v6/checkpoints/C05-harness-codex.md`)
- reviewer probe copied UNCHANGED: `engine/tests/test_v6_c05_harness_authority_adversarial.py`
  (blob sha256 `33e759b954799d112d88793c43cc1937b097a42ec92907ac7d42ff18909e3551`)

## Scientific disposition (unchanged, restated)

C05 remains **parked** and **v5 preserved**. The frozen engine-side arms are behaviorally identical
over the entire matrix (the all-zero finding is a correct engine-layer null); the frozen experiment
does not exercise the candidate policy, and calibration still fails. This correction hardens the
harness as reusable infrastructure ONLY. It authorizes nothing: no authoritative run, no policy
bridge, no new experiment version, no calibration reinterpretation.

## Blocker → fix → test (all in `harness_v4.py` + tests)

| Reviewer blocker | Fix | Refusal test |
|---|---|---|
| 1 — `measure_arm(authoritative=True)` accepts a non-authoritative draft | authority flags must match; authoritative refuses non-authoritative input | `test_measure_refuses_authoritative_on_nonauthoritative_draft` |
| 2 — authoritative `n_seasons`/seed/year/league/arm/SHA are caller args | `_check_authoritative_frame` derives all of them from the frozen effective manifest; `mandatory_league_ids` (216, tied to the frozen count); overrides refuse | `test_authoritative_measure_refuses_n_seasons_override`, `..._nonframe_base_seed`, `..._nonmandatory_league`, `test_mandatory_league_ids_is_the_frozen_216` |
| 3 — draft validation does not bind `arm`→policy SHA | `validate_draft_receipt` refuses a receipt whose arm label ≠ its frozen policy SHA (`ARM_POLICY_SHAS`) | reviewer probe `test_draft_receipt_refuses_arm_policy_identity_mismatch` |
| 4 — confirm allowed without a passing fit verdict | `write_fit_verdict`/`require_fit_verdict` (write-once, hash-pinned); confirm-stage draft/measure refuse without it, after the held-out guard | `test_require_fit_verdict_refuses_when_absent`, `..._failed_verdict`, `..._pinned_receipt_drift`, `test_measure_confirm_refuses_without_fit_verdict`, `test_write_then_require_fit_verdict_roundtrip` |
| 5 — draft receipts not bound to v4/exec-v2 hashes | `draft_arm` stamps `manifest_sha256`/`exec_addendum_sha256`/`effective_v4_manifest_sha256`; strict validator refuses missing/mismatched binding | `test_authoritative_validator_refuses_missing_v4_binding`, `..._wrong_effective_hash`, `test_effective_v4_manifest_sha256_is_deterministic` |
| (req 4 seat-policy) | `recompute_seat_policy` reproduces the frozen `draft_league` assignment; strict validator enforces it | `test_recompute_seat_policy_reproduces_the_real_receipt`, `test_authoritative_refuses_tampered_seat_policy`, `test_authoritative_validator_passes_untampered_real_receipt` |

The strict authoritative path uses `validate_authoritative_draft_receipt` (shape + arm↔policy +
frozen frame + recomputed seat-policy + v4 binding). The non-authoritative synthetic validator
(`validate_draft_receipt`) is unchanged except for the unconditional arm↔policy bind, so the 13
pre-existing harness tests stay green.

## Verification

- New/changed files only (vs `af24062`): `harness_v4.py` (+188/−1), the reviewer probe (+53), the
  C05A adversarial suite (+211), this checkpoint, and the plan. No other file touched.
- Frozen files byte-for-byte preserved (`shasum -c` OK): `execution.py`, `runner.py`, `manifest.py`,
  `season_eval.py`, `promotion-v3.json`, `promotion-v4.json`, `promotion-v4-exec-v2.json`.
- Focused suite: **79 passed** — `test_promotion` / `_adapter` / `_execution` / `_harness_v4`,
  the reviewer probe (2/2), the C05A suite, and the three C05 freeze-adversarial probes
  (`C05_PROD_ROOT` set to this worktree).
- Frozen Ruff scope (`blitz_engine/promotion` + the C05A test): all checks passed.
- `git diff --check` clean; tree clean at checkpoint.

## Still blocked (unchanged)

Authoritative fit/confirmation remains prohibited pending: independent re-review PASS of this C05A
correction, and a NEW accepted calibration report (the failed C02 report stands, unreinterpreted).
Stopped at this checkpoint for re-review. No push/merge/PR.
