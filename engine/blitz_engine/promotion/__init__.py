"""C05 preregistered-promotion machinery: manifest freeze, pairing, stats, gates.

This package executes the protocol frozen in `.orchestrator-v6/experiments/promotion-v3.json`.
It never decides anything the manifest does not already say: the manifest is loaded, hash-verified
and validated; arm runs are pairing-validated BEFORE any statistic is computed; gates apply the
frozen thresholds; and every report carries an explicit `authoritative` flag — a synthetic or
baseline dry run can never read as a shipping decision.

    from blitz_engine.promotion import load_manifest, evaluate_promotion

The authoritative v5-vs-v6 run additionally requires `arms.candidate.combined_candidate_sha` to be
frozen (non-null) — `evaluate_promotion(..., authoritative=True)` refuses to run without it.
"""
from blitz_engine.promotion.gates import (
    PromotionReport,
    calibration_gate,
    canonical_report_json,
    evaluate_promotion,
    final_verdict,
    report_hash,
)
from blitz_engine.promotion.manifest import (
    ManifestError,
    load_manifest,
    sha256_file,
    validate_manifest,
    verify_board_corpus,
)
from blitz_engine.promotion.runner import (
    ArmRun,
    HeldOutGuard,
    HeldOutLeakError,
    NondeterminismError,
    PairingError,
    PromotionError,
    assert_deterministic,
    board_fingerprint,
    derive_eval_seed,
    pair_slice,
    run_arm,
    validate_pair,
)
from blitz_engine.promotion.stats import (
    boot_seed,
    paired_ci95,
    seat_deltas,
    slice_no_regression,
)

__all__ = [
    "ArmRun",
    "HeldOutGuard",
    "HeldOutLeakError",
    "ManifestError",
    "NondeterminismError",
    "PairingError",
    "PromotionError",
    "PromotionReport",
    "assert_deterministic",
    "board_fingerprint",
    "boot_seed",
    "calibration_gate",
    "canonical_report_json",
    "derive_eval_seed",
    "evaluate_promotion",
    "final_verdict",
    "load_manifest",
    "pair_slice",
    "paired_ci95",
    "report_hash",
    "run_arm",
    "seat_deltas",
    "sha256_file",
    "slice_no_regression",
    "validate_manifest",
    "validate_pair",
    "verify_board_corpus",
]
