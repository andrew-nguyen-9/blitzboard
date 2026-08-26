"""Self-tests for the C05 promotion machinery — ALL data here is synthetic and non-authoritative.

Each test fabricates matched arm runs; nothing here evaluates a real policy, and no result in this
file may be read as promotion evidence. The suite proves the protocol itself: a clear win
promotes, a single regressing mandatory slice vetoes an aggregate win, bound violations veto, zero
evidence never promotes, mismatched pairing dies before analysis, held-out data cannot leak into
fitting, and the analysis is byte-stable across repeated runs.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from blitz_engine.promotion import (
    ArmRun,
    HeldOutGuard,
    HeldOutLeakError,
    NondeterminismError,
    PairingError,
    PromotionError,
    assert_deterministic,
    boot_seed,
    calibration_gate,
    canonical_report_json,
    derive_eval_seed,
    evaluate_promotion,
    final_verdict,
    load_manifest,
    paired_ci95,
    report_hash,
    slice_no_regression,
    validate_manifest,
    verify_board_corpus,
)

REPO = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO / ".orchestrator-v6" / "experiments" / "promotion-v3.json"

TEAMS = 4
N_SEASONS = 3


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(MANIFEST_PATH)


def make_pair(
    league_id: str,
    *,
    year: int = 2021,
    base_seed: int = 2026082601,
    delta: float = 5.0,
    noise: float = 0.5,
    h2h_delta: float = 0.0,
    playoff_delta: float = 0.0,
    rng_seed: int = 7,
    board: str = "board-A",
    ctrl_seat_policy: tuple[str, ...] | None = None,
) -> tuple[ArmRun, ArmRun]:
    """One synthetic matched pair whose candidate leads the control by `delta` per seat-season."""
    rng = np.random.default_rng(rng_seed)
    ctrl = rng.normal(1000.0, 20.0, size=(N_SEASONS, TEAMS))
    cand = ctrl + delta + rng.normal(0.0, noise, size=(N_SEASONS, TEAMS))
    seats = ctrl_seat_policy or ("static_proxy", "vorp_adp", "engine_msv", "static_proxy")
    eval_seed = derive_eval_seed(base_seed, year, league_id)
    common = dict(
        year=year, league_id=league_id, base_seed=base_seed, eval_seed=eval_seed,
        board_hash=board, seat_policy=seats, synthetic=True,
    )
    h2h_c = tuple(0.5 + h2h_delta for _ in range(TEAMS))
    h2h_0 = tuple(0.5 for _ in range(TEAMS))
    po_c = tuple(0.3 + playoff_delta for _ in range(TEAMS))
    po_0 = tuple(0.3 for _ in range(TEAMS))
    candidate = ArmRun(
        arm="v6_candidate", policy_sha="cand-sha",
        per_season=tuple(tuple(map(float, r)) for r in cand),
        h2h_win_rate=h2h_c, playoff_proxy=po_c, championship_proxy=po_c, **common,
    )
    control = ArmRun(
        arm="v5_shipped", policy_sha="ctrl-sha",
        per_season=tuple(tuple(map(float, r)) for r in ctrl),
        h2h_win_rate=h2h_0, playoff_proxy=po_0, championship_proxy=po_0, **common,
    )
    return candidate, control


def passing_calibration_report() -> dict:
    bench = {
        "id": "fantasypros-half-ppr-ecr", "snapshot_sha256": "ab" * 32,
        "retrieval_utc": "2026-08-26T00:00:00Z", "spearman_delta": 0.02,
        "weighted_rank_error_delta": -0.1, "unmatched_top_100_rate": 0.01,
    }
    return {
        "executed": True, "benchmarks": [bench],
        "deterministic_unit_failures": 0, "cohort_material_regressions": 0,
        "top_n_recall_regressions": 0, "outlier_and_decomposition_reported": True,
        "missing_data_degrades_explicitly": True, "held_out_confirmed": True,
        "season_evaluator_no_regression": True,
    }


def passing_receipts() -> dict:
    return dict(
        deterministic_receipt={
            "invariants_pass": True, "leakage_detected": False, "nondeterminism_detected": False,
        },
        runtime_receipt={"wall_clock_hours": 2.0, "peak_rss_gib": 1.5},
        calibration_report=passing_calibration_report(),
    )


def all_mandatory_pairs(manifest, **kw) -> list[tuple[ArmRun, ArmRun]]:
    return [
        make_pair(lid, rng_seed=i, **kw)
        for i, lid in enumerate(manifest["mandatory_high_risk_slices"])
    ]


# ── manifest freeze ────────────────────────────────────────────────────────────────────


def test_manifest_loads_and_is_frozen(manifest):
    assert manifest["schema_version"] == 3
    assert manifest["status"] == "preregistered_not_executed"
    assert manifest["arms"]["candidate"]["combined_candidate_sha"] is None
    assert manifest["held_out_seasons"] == [2018]
    assert len(manifest["mandatory_high_risk_slices"]) == 24
    assert manifest["blocked_slice"] in manifest["mandatory_high_risk_slices"]


def test_board_corpus_hashes_verify_against_repo(manifest):
    assert verify_board_corpus(manifest, REPO) == []


def test_manifest_rejects_executed_status_and_missing_keys(manifest):
    m = dict(manifest)
    m["status"] = "executed"
    with pytest.raises(Exception, match="preregistration"):
        validate_manifest(m)
    m2 = dict(manifest)
    del m2["thresholds"]
    with pytest.raises(Exception, match="thresholds"):
        validate_manifest(m2)
    m3 = dict(manifest)
    m3["held_out_seasons"] = [2021]
    with pytest.raises(Exception, match="overlap"):
        validate_manifest(m3)


# ── seeds and stats ────────────────────────────────────────────────────────────────────


def test_seed_derivation_is_deterministic_and_slice_dependent():
    a = derive_eval_seed(2026082601, 2021, "t10-1qb-std-te0.0-b4-ir0")
    assert a == derive_eval_seed(2026082601, 2021, "t10-1qb-std-te0.0-b4-ir0")
    assert a != derive_eval_seed(2026082601, 2024, "t10-1qb-std-te0.0-b4-ir0")
    assert a != derive_eval_seed(2026082601, 2021, "t10-1qb-std-te0.0-b8-ir0")
    assert boot_seed([1, 2], "x") == boot_seed((1, 2), "x") != boot_seed([1, 2], "y")


def test_paired_ci95_is_deterministic():
    d = np.random.default_rng(0).normal(1.0, 2.0, 40)
    assert paired_ci95(d, seed=5) == paired_ci95(d, seed=5)
    mean, lo, hi = paired_ci95(d, seed=5)
    assert lo <= mean <= hi


def test_slice_no_regression_zero_tolerance():
    assert slice_no_regression(np.array([0.0, 0.0]))
    assert slice_no_regression(np.array([1.0, -0.5]))
    assert not slice_no_regression(np.array([-0.01, 0.0]))
    assert not slice_no_regression(np.array([]))  # absent evidence never passes


# ── the promotion gates ────────────────────────────────────────────────────────────────


def test_clear_promotion_passes(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    report = evaluate_promotion(manifest, pairs, **passing_receipts())
    assert report["verdict"] == "promote"
    assert report["synthetic"] is True
    assert report["authoritative"] is False  # synthetic can never be authoritative
    assert "NON-AUTHORITATIVE" in report["label"]
    assert all(v["status"] == "pass" for v in report["slices"].values())


def test_one_regressing_mandatory_slice_vetoes_aggregate_win(manifest):
    pairs = all_mandatory_pairs(manifest, delta=8.0)
    bad = manifest["blocked_slice"]
    pairs = [p for p in pairs if p[0].league_id != bad]
    pairs.append(make_pair(bad, delta=-3.0, rng_seed=99))
    report = evaluate_promotion(manifest, pairs, **passing_receipts())
    assert report["aggregate"]["mean"] > 0  # the aggregate looks like a win
    assert report["slices"][bad]["status"] == "fail"
    assert report["verdict"] == "do_not_ship_candidate"


def test_h2h_lower_bound_violation_fails(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0, h2h_delta=-0.05)
    report = evaluate_promotion(manifest, pairs, **passing_receipts())
    assert report["verdict"] == "do_not_ship_candidate"
    assert any(g["name"] == "h2h_win_rate" and g["status"] == "fail" for g in report["gates"])


def test_playoff_lower_bound_violation_fails(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0, playoff_delta=-0.05)
    report = evaluate_promotion(manifest, pairs, **passing_receipts())
    assert report["verdict"] == "do_not_ship_candidate"


def test_zero_evidence_never_promotes(manifest):
    pairs = all_mandatory_pairs(manifest, delta=0.0, noise=0.0)  # identical arms → all-zero deltas
    report = evaluate_promotion(manifest, pairs, **passing_receipts())
    assert report["verdict"] == "preserve_v5"
    assert any(
        g["name"] == "started_points_aggregate" and g["status"] == "inconclusive"
        for g in report["gates"]
    )


def test_missing_playoff_proxies_is_inconclusive_not_promote(manifest):
    cand, ctrl = make_pair("t14-2qb-std-te0.5-b4-ir1", delta=5.0)
    strip = lambda r: ArmRun(**{**r.to_dict(), "playoff_proxy": None, "championship_proxy": None})  # noqa: E731
    report = evaluate_promotion(manifest, [(strip(cand), strip(ctrl))], **passing_receipts())
    assert report["verdict"] == "preserve_v5"  # C02 dependency absent → cannot promote


def test_leakage_or_invariant_failure_blocks(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    rec = passing_receipts()
    rec["deterministic_receipt"] = {
        "invariants_pass": True, "leakage_detected": True, "nondeterminism_detected": False,
    }
    assert evaluate_promotion(manifest, pairs, **rec)["verdict"] == "BLOCK"
    rec["deterministic_receipt"] = {
        "invariants_pass": False, "leakage_detected": False, "nondeterminism_detected": False,
    }
    assert evaluate_promotion(manifest, pairs, **rec)["verdict"] == "BLOCK"


def test_limits_violation_fails(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    rec = passing_receipts()
    rec["runtime_receipt"] = {"wall_clock_hours": 13.0, "peak_rss_gib": 1.0}
    assert evaluate_promotion(manifest, pairs, **rec)["verdict"] == "do_not_ship_candidate"


# ── pairing violations die before analysis ─────────────────────────────────────────────


def test_mismatched_board_seed_or_seats_fail_before_analysis(manifest):
    cand, ctrl = make_pair("t10-1qb-std-te0.0-b4-ir0")
    rec = passing_receipts()
    wrong_board = ArmRun(**{**ctrl.to_dict(), "board_hash": "board-B"})
    with pytest.raises(PairingError, match="board_hash"):
        evaluate_promotion(manifest, [(cand, wrong_board)], **rec)
    wrong_seed = ArmRun(**{**ctrl.to_dict(), "base_seed": 1, "eval_seed": ctrl.eval_seed})
    with pytest.raises(PairingError, match="base_seed"):
        evaluate_promotion(manifest, [(cand, wrong_seed)], **rec)
    wrong_seats = ArmRun(
        **{**ctrl.to_dict(), "seat_policy": ("vorp_adp",) * TEAMS}
    )
    with pytest.raises(PairingError, match="seat_policy"):
        evaluate_promotion(manifest, [(cand, wrong_seats)], **rec)
    with pytest.raises(PairingError, match="identical"):
        evaluate_promotion(manifest, [(cand, cand)], **rec)
    drifted = ArmRun(**{**ctrl.to_dict(), "eval_seed": ctrl.eval_seed + 1})
    with pytest.raises(PairingError):
        evaluate_promotion(manifest, [(cand, drifted)], **rec)


# ── held-out separation ────────────────────────────────────────────────────────────────


def test_held_out_cannot_leak_into_fitting(manifest):
    held = make_pair("t10-1qb-std-te0.0-b4-ir0", year=2018)
    with pytest.raises(HeldOutLeakError, match="2018"):
        evaluate_promotion(manifest, [held], **passing_receipts())


def test_confirm_stage_reads_only_held_out(manifest):
    held = make_pair("t10-1qb-std-te0.0-b4-ir0", year=2018, delta=5.0)
    report = evaluate_promotion(manifest, [held], stage="confirm", **passing_receipts())
    assert report["stage"] == "confirm"
    assert report["held_out_access_log"] == [{"year": 2018, "stage": "confirm"}]
    fit_year = make_pair("t10-1qb-std-te0.0-b4-ir0", year=2021)
    with pytest.raises(HeldOutLeakError, match="confirm"):
        evaluate_promotion(manifest, [fit_year], stage="confirm", **passing_receipts())


def test_held_out_guard_rejects_overlap():
    with pytest.raises(HeldOutLeakError):
        HeldOutGuard([2021, 2018], [2018])


# ── authoritative preconditions ────────────────────────────────────────────────────────


def test_authoritative_requires_frozen_candidate_sha(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    with pytest.raises(PromotionError, match="combined_candidate_sha"):
        evaluate_promotion(manifest, pairs, authoritative=True, **passing_receipts())


def test_full_coverage_requirement_marks_missing_slices_inconclusive(manifest):
    pairs = [make_pair(manifest["blocked_slice"], delta=5.0)]
    report = evaluate_promotion(
        manifest, pairs, require_full_coverage=True, **passing_receipts()
    )
    assert report["verdict"] == "preserve_v5"
    assert any(g["name"] == "league_coverage" for g in report["gates"])


# ── calibration gates ──────────────────────────────────────────────────────────────────


def test_calibration_gate_pass_fail_and_missing(manifest):
    calib = manifest["calibration_gates"]
    assert calibration_gate(passing_calibration_report(), calib)["status"] == "pass"
    assert calibration_gate(None, calib)["status"] == "fail"
    bad = passing_calibration_report()
    bad["benchmarks"][0]["snapshot_sha256"] = ""
    assert calibration_gate(bad, calib)["status"] == "fail"
    worse = passing_calibration_report()
    worse["benchmarks"][0]["spearman_delta"] = -0.01
    assert calibration_gate(worse, calib)["status"] == "fail"
    cohort = passing_calibration_report()
    cohort["cohort_material_regressions"] = 1
    assert calibration_gate(cohort, calib)["status"] == "fail"


def test_missing_calibration_report_fails_promotion(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    rec = passing_receipts()
    rec["calibration_report"] = None
    assert evaluate_promotion(manifest, pairs, **rec)["verdict"] == "do_not_ship_candidate"


# ── determinism and byte stability ─────────────────────────────────────────────────────


def test_repeated_analysis_is_byte_stable(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    r1 = evaluate_promotion(manifest, pairs, **passing_receipts())
    r2 = evaluate_promotion(manifest, pairs, **passing_receipts())
    assert canonical_report_json(r1) == canonical_report_json(r2)
    assert report_hash(r1) == report_hash(r2)


def test_assert_deterministic_catches_flaky_runs():
    cand, _ = make_pair("t10-1qb-std-te0.0-b4-ir0")
    assert assert_deterministic(lambda: cand) == cand
    flaky = iter([cand, ArmRun(**{**cand.to_dict(), "board_hash": "other"})])
    with pytest.raises(NondeterminismError, match="board_hash"):
        assert_deterministic(lambda: next(flaky))


def test_armrun_round_trips_through_json():
    cand, _ = make_pair("t10-1qb-std-te0.0-b4-ir0")
    assert ArmRun.from_dict(json.loads(json.dumps(cand.to_dict()))) == cand


def test_final_verdict_needs_both_stages_and_takes_the_worst(manifest):
    pairs = all_mandatory_pairs(manifest, delta=5.0)
    fit = evaluate_promotion(manifest, pairs, **passing_receipts())
    held = [make_pair(lid, year=2018, delta=-4.0, rng_seed=i)
            for i, lid in enumerate(manifest["mandatory_high_risk_slices"])]
    confirm = evaluate_promotion(manifest, held, stage="confirm", **passing_receipts())
    assert fit["verdict"] == "promote"
    assert confirm["verdict"] == "do_not_ship_candidate"
    assert final_verdict(fit, confirm) == "do_not_ship_candidate"
    with pytest.raises(PromotionError):
        final_verdict(fit, fit)
