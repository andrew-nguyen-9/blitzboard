"""Adapter tests: PROVISIONAL C02 surfaces → C05 promotion inputs. Synthetic/non-authoritative.

Every evaluation here is either fabricated or a mapping of C02's committed calibration report;
no test promotes anything, and the one full-stack test proves the opposite — that provisional
C02 output cannot pass the C05 gates without the explicit attestations C02 review would supply.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from blitz_engine.promotion import (
    PairingError,
    calibration_gate,
    evaluate_promotion,
    load_manifest,
)
from blitz_engine.promotion.adapter import (
    INTERFACE_MISMATCHES,
    arm_run_from_result,
    calibration_report_from_c02,
    deterministic_receipt_from_probes,
    probe_leak_guard,
)
from blitz_engine.simulation.season_eval import SeasonEvalResult

REPO = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO / ".orchestrator-v6" / "experiments" / "promotion-v3.json"
C02_REPORT_PATH = REPO / ".orchestrator-v6" / "experiments" / "calibration" / "report.json"

TEAMS = 4
N_SEASONS = 3
SEATS = ("static_proxy", "vorp_adp", "engine_msv", "static_proxy")


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(MANIFEST_PATH)


@pytest.fixture(scope="module")
def c02_report():
    return json.loads(C02_REPORT_PATH.read_text())


def make_result(
    points: np.ndarray,
    *,
    h2h: float = 0.5,
    playoff: np.ndarray | None = None,
    champ: np.ndarray | None = None,
    seats: tuple[str, ...] = SEATS,
) -> SeasonEvalResult:
    """A fabricated C02-shaped result; `points` is (n_seasons, teams)."""
    po = playoff if playoff is not None else np.tile([1.0, 1.0, 0.0, 0.0], (N_SEASONS, 1))
    ch = champ if champ is not None else np.tile([1.0, 0.0, 0.0, 0.0], (N_SEASONS, 1))
    return SeasonEvalResult(
        started_points=points.mean(axis=0),
        h2h_win_rate=np.full(TEAMS, h2h),
        seat_policy=list(seats),
        starts_lost=np.zeros(TEAMS),
        waiver_adds=np.zeros(TEAMS),
        n_seasons=N_SEASONS,
        weeks=14,
        per_season=points,
        emergency_adds=np.zeros(TEAMS),
        upside_adds=np.zeros(TEAMS),
        playoff_rate=po.mean(axis=0) if po.size else np.empty(0),
        champ_rate=ch.mean(axis=0) if ch.size else np.empty(0),
        per_season_h2h=np.full((N_SEASONS, TEAMS), h2h),
        per_season_playoff=po,
        per_season_champ=ch,
    )


def adapt(arm: str, sha: str, res: SeasonEvalResult, lid: str, year: int = 2021):
    return arm_run_from_result(
        arm, sha, res, year=year, league_id=lid, base_seed=2026082601,
        board_hash=f"synthetic-board-{lid}",
    )


# ── SeasonEvalResult → ArmRun ──────────────────────────────────────────────────────────


def test_adapter_maps_all_paired_families():
    rng = np.random.default_rng(3)
    pts = rng.normal(1000.0, 20.0, size=(N_SEASONS, TEAMS))
    res = make_result(pts, h2h=0.55)
    run = adapt("v6_candidate", "cand-sha", res, "t10-1qb-std-te0.0-b4-ir0")
    assert np.allclose(np.asarray(run.per_season), pts)
    assert run.h2h_win_rate == tuple(np.full(TEAMS, 0.55))
    # playoff/championship proxies are the per-seat means of the 0/1 season samples
    assert run.playoff_proxy == (1.0, 1.0, 0.0, 0.0)
    assert run.championship_proxy == (1.0, 0.0, 0.0, 0.0)
    assert run.seat_policy == SEATS
    assert run.synthetic is True


def test_pre_c02_result_maps_proxies_to_none():
    pts = np.ones((N_SEASONS, TEAMS)) * 1000.0
    res = make_result(pts, playoff=np.empty((0, 0)), champ=np.empty((0, 0)))
    run = adapt("v6_candidate", "cand-sha", res, "t10-1qb-std-te0.0-b4-ir0")
    assert run.playoff_proxy is None and run.championship_proxy is None


def test_adapter_preserves_pairing_enforcement(manifest):
    lid = "t10-1qb-std-te0.0-b4-ir0"
    pts = np.ones((N_SEASONS, TEAMS)) * 1000.0
    cand = adapt("v6_candidate", "cand-sha", make_result(pts + 5), lid)
    other_seats = make_result(pts, seats=("vorp_adp",) * TEAMS)
    ctrl = adapt("v5_shipped", "ctrl-sha", other_seats, lid)
    with pytest.raises(PairingError, match="seat_policy"):
        evaluate_promotion(manifest, [(cand, ctrl)])


def _receipts(calibration_report):
    return dict(
        deterministic_receipt=deterministic_receipt_from_probes(
            invariants_pass=True, determinism_ok=True, leak_guard_live=True
        ),
        runtime_receipt={"wall_clock_hours": 0.1, "peak_rss_gib": 0.5},
        calibration_report=calibration_report,
    )


def _full_attestations():
    return {
        "deterministic_unit_failures": 0, "held_out_confirmed": True,
        "season_evaluator_no_regression": True, "missing_data_degrades_explicitly": True,
    }


def test_adapted_pairs_flow_through_the_full_gate_stack(manifest, c02_report):
    """Fabricated C02-shaped wins + fully-attested calibration: promote, still non-authoritative."""
    rng = np.random.default_rng(11)
    pairs = []
    for i, lid in enumerate(manifest["mandatory_high_risk_slices"]):
        ctrl_pts = rng.normal(1000.0, 20.0, size=(N_SEASONS, TEAMS))
        po = np.tile([1.0, 0.0, 1.0, 0.0], (N_SEASONS, 1))
        ctrl = adapt("v5_shipped", "ctrl-sha", make_result(ctrl_pts, playoff=po, champ=po), lid)
        cand = adapt(
            "v6_candidate", "cand-sha",
            make_result(ctrl_pts + 5.0 + i * 0.01, h2h=0.51, playoff=po, champ=po), lid,
        )
        pairs.append((cand, ctrl))
    # A synthetic passing calibration report shaped like C02's, with review attestations supplied.
    calib, gaps = calibration_report_from_c02(c02_report, _full_attestations())
    calib["benchmarks"] = [
        {**b, "spearman_delta": 0.01, "weighted_rank_error_delta": -0.1}
        for b in calib["benchmarks"]
    ]  # synthetic: the REAL provisional deltas fail (see the next test), which is the point
    calib["cohort_material_regressions"] = 0
    calib["top_n_recall_regressions"] = 0
    report = evaluate_promotion(manifest, pairs, **_receipts(calib))
    assert report["verdict"] == "promote"
    assert report["authoritative"] is False
    assert gaps  # the mapping gaps are always surfaced


# ── C02 calibration report mapping (the REAL committed provisional report) ─────────────


def test_real_c02_calibration_report_maps_and_fails_conservatively(manifest, c02_report):
    mapped, gaps = calibration_report_from_c02(c02_report)
    assert len(mapped["benchmarks"]) == 4
    by_id = {b["id"]: b for b in mapped["benchmarks"]}
    sf = by_id["12-team-half-ppr-superflex/fantasypros-superflex-ecr"]
    oneqb = by_id["12-team-half-ppr-1qb/fantasypros-half-ppr-ecr"]
    # matches C02's own threshold_checks: superflex improves, 1QB declines
    assert sf["spearman_delta"] > 0 and sf["weighted_rank_error_delta"] < 0
    assert oneqb["spearman_delta"] < 0
    for b in mapped["benchmarks"]:  # source identity survived the mapping
        assert len(b["snapshot_sha256"]) == 64 and b["retrieval_utc"]
    # conservative defaults: unattested gaps fail the gate — provisional C02 cannot promote
    assert mapped["deterministic_unit_failures"] == 1
    assert mapped["held_out_confirmed"] is False
    assert calibration_gate(mapped, manifest["calibration_gates"])["status"] == "fail"
    assert any("held-out" in g for g in gaps)


def test_real_c02_report_fails_even_fully_attested(manifest, c02_report):
    """The provisional deltas themselves fail the frozen thresholds (1QB/2QB spearman < 0)."""
    mapped, _ = calibration_report_from_c02(c02_report, _full_attestations())
    assert calibration_gate(mapped, manifest["calibration_gates"])["status"] == "fail"


def test_attestations_cannot_override_report_derived_fields(c02_report):
    with pytest.raises(ValueError, match="may not override"):
        calibration_report_from_c02(c02_report, {"benchmarks": []})


def test_full_stack_with_real_provisional_calibration_does_not_ship(manifest, c02_report):
    rng = np.random.default_rng(13)
    pairs = []
    for lid in manifest["mandatory_high_risk_slices"]:
        ctrl_pts = rng.normal(1000.0, 20.0, size=(N_SEASONS, TEAMS))
        ctrl = adapt("v5_shipped", "ctrl-sha", make_result(ctrl_pts), lid)
        cand = adapt("v6_candidate", "cand-sha", make_result(ctrl_pts + 8.0, h2h=0.52), lid)
        pairs.append((cand, ctrl))
    mapped, _ = calibration_report_from_c02(c02_report, _full_attestations())
    report = evaluate_promotion(manifest, pairs, **_receipts(mapped))
    assert report["verdict"] == "do_not_ship_candidate"  # calibration vetoes a clean synthetic win


# ── mechanical probes ──────────────────────────────────────────────────────────────────


def test_leak_probe_confirms_guard_is_live_on_real_evaluator():
    from blitz_engine.testing import matrix

    row = next(r for r in matrix.all() if r["id"] == "t10-1qb-std-te0.0-b4-ir0")
    assert probe_leak_guard(2021, row, seed=2026082601) is True


def test_receipt_probe_mapping_and_dead_guard_blocks(manifest):
    rec = deterministic_receipt_from_probes(
        invariants_pass=True, determinism_ok=True, leak_guard_live=False
    )
    assert rec == {
        "invariants_pass": True, "leakage_detected": True, "nondeterminism_detected": False,
    }
    lid = "t10-1qb-std-te0.0-b4-ir0"
    pts = np.ones((N_SEASONS, TEAMS)) * 1000.0
    cand = adapt("v6_candidate", "cand-sha", make_result(pts + 5), lid)
    ctrl = adapt("v5_shipped", "ctrl-sha", make_result(pts), lid)
    report = evaluate_promotion(
        manifest, [(cand, ctrl)],
        deterministic_receipt=rec,
        runtime_receipt={"wall_clock_hours": 0.1, "peak_rss_gib": 0.5},
        calibration_report=None,
    )
    assert report["verdict"] == "BLOCK"


def test_interface_mismatches_are_recorded():
    assert len(INTERFACE_MISMATCHES) >= 6
    assert any("transaction cost" in m for m in INTERFACE_MISMATCHES)
    assert any("held-out" in m for m in INTERFACE_MISMATCHES)
