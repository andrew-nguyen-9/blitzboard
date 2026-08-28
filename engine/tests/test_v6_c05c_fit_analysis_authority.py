"""C05C fit-analysis authority — the harness produces the report mechanically via the frozen
`evaluate_promotion`; no caller-authored report content is trusted, and confirmation reruns the
analysis from all pinned inputs. Non-authoritative test data flagged authoritative to exercise the
mechanism.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from blitz_engine.promotion.execution import ExecutionError
from blitz_engine.promotion.gates import report_hash
from blitz_engine.promotion.harness_v4 import (
    ARM_POLICY_SHAS,
    EXEC_V2_SHA256,
    MEASUREMENT_SHA,
    V4_MANIFEST_SHA256,
    effective_v4_manifest_sha256,
    expected_fit_cells,
    load_execution_manifest_v4,
    validate_fit_analysis_receipt,
    write_fit_verdict,
)
from blitz_engine.promotion.runner import derive_eval_seed

REPO = Path(__file__).resolve().parents[2]
EFF = load_execution_manifest_v4(REPO)
_CORE = ("deterministic_checks", "started_points_aggregate", "hidden_regression_rule",
         "h2h_win_rate", "playoff_proxy", "championship_proxy", "calibration_gates", "limits")


def _mrec(arm, year, lid, seed, *, promote):
    is_cand = arm == "v6_candidate"
    lead = 1.0 if (promote and is_cand) else 0.0
    proxy = [0.6] if (promote and is_cand) else [0.5]  # proxies present in both scenarios
    ar = {
        "arm": arm, "policy_sha": ARM_POLICY_SHAS[arm], "year": year, "league_id": lid,
        "base_seed": seed, "eval_seed": derive_eval_seed(seed, year, lid),
        "board_hash": "b" * 64, "seat_policy": ["static_proxy"], "per_season": [[lead]],
        "h2h_win_rate": [0.6 if (promote and is_cand) else 0.5],
        "playoff_proxy": proxy, "championship_proxy": proxy, "synthetic": False,
    }
    return {
        "kind": "measurement", "authoritative": True, "stage": "fit",
        "measured_by_sha": MEASUREMENT_SHA, "arm_run": ar, "draft_receipt_sha256": "d" * 64,
        "n_seasons": 8, "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
    }


def _frame(tmp_path, *, promote):
    paths = []
    for i, (arm, year, lid, seed) in enumerate(sorted(expected_fit_cells(EFF))):
        p = tmp_path / "measure" / "fit" / f"{i}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_mrec(arm, year, lid, seed, promote=promote)))
        paths.append(str(p))
    return paths


def _cal(ok):
    if not ok:
        return {"executed": True, "benchmarks": []}  # no benchmark snapshots ⇒ calibration fail
    return {
        "executed": True,
        "benchmarks": [{"id": "b1", "snapshot_sha256": "s", "retrieval_utc": "t",
                        "spearman_delta": 0.1, "weighted_rank_error_delta": -0.1,
                        "unmatched_top_100_rate": 0.0}],
        "deterministic_unit_failures": 0, "cohort_material_regressions": 0,
        "top_n_recall_regressions": 0, "outlier_and_decomposition_reported": True,
        "missing_data_degrades_explicitly": True, "held_out_confirmed": True,
        "season_evaluator_no_regression": True,
    }


def _aux(tmp_path, *, calibration_ok=True):
    det = tmp_path / "det.json"
    det.write_text(json.dumps({"invariants_pass": True, "leakage_detected": False,
                               "nondeterminism_detected": False}))
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(_cal(calibration_ok)))
    rt = tmp_path / "rt.json"
    rt.write_text(json.dumps({"wall_clock_hours": 1.0, "peak_rss_gib": 1.0}))
    return str(det), str(cal), str(rt)


def _write(tmp_path, *, promote, calibration_ok=True):
    paths = _frame(tmp_path, promote=promote)
    det, cal, rt = _aux(tmp_path, calibration_ok=calibration_ok)
    return write_fit_verdict(
        tmp_path, effective=EFF, measurement_paths=paths,
        deterministic_receipt_path=det, calibration_report_path=cal, runtime_receipt_path=rt,
    )


# ── the harness produces the verdict mechanically; `pass` is unreachable without an accepted ──
# ── calibration report, so the fit verdict never promotes fabricated evidence (req 1/4/5/6) ───


def test_identical_arms_never_pass(tmp_path):
    doc = json.loads(_write(tmp_path, promote=False).read_text())
    assert doc["verdict"] != "pass"  # zero started-points + no authoritative calibration


def test_failed_calibration_never_promotes(tmp_path):
    doc = json.loads(_write(tmp_path, promote=True, calibration_ok=False).read_text())
    assert doc["verdict"] != "pass"
    assert doc["report_verdict"] == "do_not_ship_candidate"


# Auxiliary-authority validation (C05D) and confirmation-replay coverage live in
# test_v6_c05d_auxiliary_authority.py; the C05C `_aux` fixtures are unbound and so never promote.


# ── validate_fit_analysis_receipt refuses caller-authored authority (blocker 1) ────────


def _fa(verdict, gates):
    report = {"stage": "fit", "authoritative": True,
              "n_pairs": len(expected_fit_cells(EFF)) // 2, "verdict": verdict, "gates": gates}
    return {"kind": "fit_analysis", "report": report, "report_sha256": report_hash(report),
            "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
            "pinned_inputs": {"measurement_sha256": {"m": "a" * 64}}}


def test_validate_refuses_missing_core_gate():
    gates = [{"name": n, "status": "pass"} for n in _CORE[1:]]  # drop one core gate
    with pytest.raises(ExecutionError, match="missing frozen gate"):
        validate_fit_analysis_receipt(_fa("promote", gates), EFF, measurement_shas={"a" * 64})


def test_validate_refuses_verdict_inconsistent_with_gates():
    gates = [{"name": n, "status": "pass"} for n in _CORE]
    gates[0]["status"] = "inconclusive"  # gates say preserve_v5, verdict claims promote
    with pytest.raises(ExecutionError, match="inconsistent"):
        validate_fit_analysis_receipt(_fa("promote", gates), EFF, measurement_shas={"a" * 64})
