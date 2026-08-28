"""C05D auxiliary authority — deterministic/calibration/runtime receipts must be mechanically
authoritative (schema + provenance + frame binding) in both writing and confirmation. Byte-hash
pinning proves retention, never authority. Missing runtime fields must never default to a pass.
"""
from __future__ import annotations

import json
import math
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
    fit_frame_sha256,
    load_execution_manifest_v4,
    require_fit_verdict,
    validate_auxiliary,
)
from blitz_engine.promotion.manifest import sha256_file
from blitz_engine.promotion.runner import derive_eval_seed

REPO = Path(__file__).resolve().parents[2]
EFF = load_execution_manifest_v4(REPO)
_CORE = ("deterministic_checks", "started_points_aggregate", "hidden_regression_rule",
         "h2h_win_rate", "playoff_proxy", "championship_proxy", "calibration_gates", "limits")
FRAME = "f" * 64


def _bound(kind, frame_sha=FRAME, **extra):
    d = {"kind": kind, "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
         "fit_frame_sha256": frame_sha, "produced_by_tooling": {"tooling_head": "abc"}}
    d.update(extra)
    return d


def _det():
    return _bound("deterministic_receipt", invariants_pass=True, leakage_detected=False,
                  nondeterminism_detected=False)


def _rt():
    return _bound("runtime_receipt", wall_clock_hours=1.0, peak_rss_gib=1.0)


def _va(deterministic=None, calibration=None, runtime=None, frame_sha=FRAME):
    return validate_auxiliary(EFF, frame_sha, deterministic=deterministic,
                              calibration=calibration, runtime=runtime)


# ── deterministic authority ────────────────────────────────────────────────────────────


def test_deterministic_is_never_admitted_from_caller():
    # C05E: even a fully-shaped caller receipt stays absent until mechanically generated
    assert _va(deterministic=_det())["deterministic"] is None


@pytest.mark.parametrize("mut", [
    {"fit_frame_sha256": "0" * 64},                       # frame binding drift
    {"effective_v4_manifest_sha256": "0" * 64},           # protocol binding drift
    {"produced_by_tooling": None},                        # no provenance
    {"kind": "nope"},                                     # wrong kind
    {"invariants_pass": False},                           # a real deterministic failure
    {"leakage_detected": True},
])
def test_deterministic_unauthoritative_is_dropped(mut):
    assert _va(deterministic={**_det(), **mut})["deterministic"] is None


# ── runtime authority: missing/malformed/non-finite must never survive ─────────────────


def test_runtime_is_never_admitted_from_caller():
    # C05E: a well-formed caller runtime receipt is still not mechanical authority ⇒ absent
    assert _va(runtime=_rt())["runtime"] is None


@pytest.mark.parametrize("doc", [
    {},                                                     # empty — the reviewer's {} runtime
    _bound("runtime_receipt", wall_clock_hours=1.0),        # missing peak_rss_gib
    _bound("runtime_receipt", peak_rss_gib=1.0),            # missing wall_clock_hours
    {**_rt(), "wall_clock_hours": -1.0},                    # negative
    {**_rt(), "peak_rss_gib": float("inf")},               # non-finite
    {**_rt(), "wall_clock_hours": "1.0"},                  # wrong type
])
def test_runtime_unauthoritative_is_dropped(doc):
    assert _va(runtime=doc)["runtime"] is None


def test_runtime_missing_keys_never_default_to_pass():
    # {} would satisfy the frozen limits gate (defaults to 0 ≤ max); the validator must drop it
    assert _va(runtime={})["runtime"] is None


# ── calibration authority: no accepted report is frozen ⇒ never admissible ─────────────


def test_calibration_bare_dictionary_is_never_admitted():
    forged = _bound("calibration_receipt", accepted=True,
                    accepted_report_sha256="deadbeef",
                    source_manifest_sha256=EFF["calibration_gates"]["source_manifest_sha256"],
                    source_amendment_sha256=EFF["calibration_gates"]["source_amendment_sha256"],
                    report={"executed": True, "benchmarks": []})
    assert _va(calibration=forged)["calibration"] is None  # no frozen accepted-report identity


# ── confirmation revalidates auxiliary authority + replays (req 7) ─────────────────────


def _measurement(arm, year, lid, seed):
    cand = arm == "v6_candidate"
    proxy = [0.6] if cand else [0.5]
    return {
        "kind": "measurement", "authoritative": True, "stage": "fit",
        "measured_by_sha": MEASUREMENT_SHA, "draft_receipt_sha256": "d" * 64, "n_seasons": 8,
        "manifest_sha256": V4_MANIFEST_SHA256, "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
        "arm_run": {
            "arm": arm, "policy_sha": ARM_POLICY_SHAS[arm], "year": year, "league_id": lid,
            "base_seed": seed, "eval_seed": derive_eval_seed(seed, year, lid),
            "board_hash": "b" * 64, "seat_policy": ["static_proxy"],
            "per_season": [[1.0 if cand else 0.0]], "h2h_win_rate": [0.6 if cand else 0.5],
            "playoff_proxy": proxy, "championship_proxy": proxy, "synthetic": False,
        },
    }


def _hand_written_pass(tmp_path):
    """Forge a fit-verdict.json that RECORDS verdict `pass` with a complete valid frame + bound
    auxiliary files. Confirmation must still refuse it: it re-derives authority + verdict."""
    pins = {}
    for i, cell in enumerate(sorted(expected_fit_cells(EFF))):
        p = tmp_path / "measure" / "fit" / f"{i}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_measurement(*cell)))
        pins[str(p)] = sha256_file(str(p))
    frame_sha = fit_frame_sha256(pins)
    aux = {}
    for name, doc in (("deterministic", {**_det(), "fit_frame_sha256": frame_sha}),
                      ("calibration", _bound("calibration_receipt", frame_sha,
                                             accepted=True, report={"executed": True})),
                      ("runtime", {**_rt(), "fit_frame_sha256": frame_sha})):
        f = tmp_path / f"{name}.json"
        f.write_text(json.dumps(doc))
        aux[name] = str(f)
    aux_pins = {k: sha256_file(v) for k, v in aux.items()}
    report = {"stage": "fit", "authoritative": True, "n_pairs": len(expected_fit_cells(EFF)) // 2,
              "verdict": "promote", "gates": [{"name": n, "status": "pass"} for n in _CORE]}
    report_sha = report_hash(report)
    fit_analysis = {"kind": "fit_analysis", "report": report, "report_sha256": report_sha,
                    "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
                    "pinned_inputs": {"measurement_sha256": pins, "auxiliary_sha256": aux_pins}}
    (tmp_path / "fit-verdict.json").write_text(json.dumps({
        "kind": "fit_verdict", "verdict": "pass", "report_verdict": "promote",
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
        "fit_frame_sha256": frame_sha, "fit_receipt_sha256": pins,
        "auxiliary_sha256": aux_pins, "auxiliary_receipt_paths": aux,
        "fit_analysis_report_sha256": report_sha, "fit_analysis": fit_analysis,
    }))


def test_confirm_refuses_forged_pass_by_rerun(tmp_path):
    _hand_written_pass(tmp_path)  # calibration is dropped on replay ⇒ recomputed ≠ promote
    with pytest.raises(ExecutionError, match="recomputed report hash|not promote"):
        require_fit_verdict(tmp_path, EFF)


def test_confirm_refuses_missing_measurement(tmp_path):
    _hand_written_pass(tmp_path)
    doc = json.loads((tmp_path / "fit-verdict.json").read_text())
    Path(next(iter(doc["fit_receipt_sha256"]))).unlink()
    with pytest.raises(ExecutionError, match="pinned measurement drift"):
        require_fit_verdict(tmp_path, EFF)


def test_confirm_refuses_auxiliary_drift(tmp_path):
    _hand_written_pass(tmp_path)
    doc = json.loads((tmp_path / "fit-verdict.json").read_text())
    Path(doc["auxiliary_receipt_paths"]["runtime"]).write_text("{}")
    with pytest.raises(ExecutionError, match="auxiliary receipt drift"):
        require_fit_verdict(tmp_path, EFF)


def test_confirm_refuses_frame_fingerprint_drift(tmp_path):
    _hand_written_pass(tmp_path)
    fv = tmp_path / "fit-verdict.json"
    doc = json.loads(fv.read_text())
    doc["fit_frame_sha256"] = "0" * 64
    fv.write_text(json.dumps(doc))
    with pytest.raises(ExecutionError, match="fit-frame fingerprint drift"):
        require_fit_verdict(tmp_path, EFF)


def test_isfinite_guard_is_real():
    assert math.isfinite(1.0) and not math.isfinite(float("nan"))
