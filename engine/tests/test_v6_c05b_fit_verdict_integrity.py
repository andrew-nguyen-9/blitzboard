"""C05B fit-verdict integrity — adversarial tests for the complete-frame, per-receipt, hash-pinned
fit-analysis, and never-fabricate-pass behavior. Non-authoritative.

The reviewer dummy-receipt probe from b7de57f is copied in unchanged separately once that commit is
available; these are the producer-side completeness/duplicate/pairing/numerical/calibration probes.
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
    assert_complete_fit_frame,
    effective_v4_manifest_sha256,
    expected_fit_cells,
    load_execution_manifest_v4,
    require_fit_verdict,
    validate_fit_analysis_receipt,
    validate_fit_measurement_receipt,
    write_fit_verdict,
)
from blitz_engine.promotion.runner import derive_eval_seed

REPO = Path(__file__).resolve().parents[2]
EFF = load_execution_manifest_v4(REPO)


def _mrec(arm, year, lid, base_seed, **over) -> dict:
    ar = {
        "arm": arm, "policy_sha": ARM_POLICY_SHAS[arm], "year": year, "league_id": lid,
        "base_seed": base_seed, "eval_seed": derive_eval_seed(base_seed, year, lid),
        "board_hash": "b" * 64, "seat_policy": ["static_proxy"], "per_season": [[0.0]],
        "h2h_win_rate": [0.0], "playoff_proxy": None, "championship_proxy": None, "synthetic": False,
    }
    doc = {
        "kind": "measurement", "authoritative": True, "stage": "fit",
        "measured_by_sha": MEASUREMENT_SHA, "arm_run": ar, "draft_receipt_sha256": "d" * 64,
        "n_seasons": 8, "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
    }
    doc.update(over)
    return doc


def _a_cell():
    return sorted(expected_fit_cells(EFF))[0]  # (arm, year, lid, base_seed)


# ── req 3: per-receipt validation ──────────────────────────────────────────────────────


def test_valid_receipt_returns_its_cell_key():
    arm, year, lid, seed = _a_cell()
    assert validate_fit_measurement_receipt(_mrec(arm, year, lid, seed), EFF) == (arm, year, lid, seed)


@pytest.mark.parametrize("mut,match", [
    ({"authoritative": False}, "non-authoritative"),
    ({"stage": "confirm"}, "not 'fit'"),
    ({"measured_by_sha": "0" * 40}, "measurement SHA"),
    ({"manifest_sha256": "0" * 64}, "promotion-v4"),
    ({"exec_addendum_sha256": "0" * 64}, "exec-v2"),
    ({"effective_v4_manifest_sha256": "0" * 64}, "effective-v4"),
    ({"draft_receipt_sha256": ""}, "draft-receipt"),
    ({"n_seasons": 1}, "n_seasons"),
])
def test_receipt_refusals(mut, match):
    arm, year, lid, seed = _a_cell()
    with pytest.raises(ExecutionError, match=match):
        validate_fit_measurement_receipt(_mrec(arm, year, lid, seed, **mut), EFF)


def test_receipt_refuses_arm_policy_mismatch():
    arm, year, lid, seed = _a_cell()
    doc = _mrec(arm, year, lid, seed)
    doc["arm_run"]["policy_sha"] = "0" * 40
    with pytest.raises(ExecutionError, match="policy_sha"):
        validate_fit_measurement_receipt(doc, EFF)


def test_receipt_refuses_missing_pairing_key():
    arm, year, lid, seed = _a_cell()
    doc = _mrec(arm, year, lid, seed)
    doc["arm_run"]["board_hash"] = None
    with pytest.raises(ExecutionError, match="pairing key"):
        validate_fit_measurement_receipt(doc, EFF)


def test_receipt_refuses_offframe_league():
    _, year, _, seed = _a_cell()
    with pytest.raises(ExecutionError, match="mandatory"):
        validate_fit_measurement_receipt(_mrec("v6_candidate", year, "t8-1qb-std-te0.0-b4-ir0", seed), EFF)


# ── req 2: complete-frame enumeration ──────────────────────────────────────────────────


def test_expected_fit_cells_is_3456():
    cells = expected_fit_cells(EFF)
    assert len(cells) == 2 * 2 * 216 * 4 == 3456


def test_frame_refuses_incomplete():
    arm, year, lid, seed = _a_cell()
    with pytest.raises(ExecutionError, match="incomplete"):
        assert_complete_fit_frame([_mrec(arm, year, lid, seed)], EFF)


def test_frame_refuses_duplicate_cell():
    arm, year, lid, seed = _a_cell()
    d = _mrec(arm, year, lid, seed)
    with pytest.raises(ExecutionError, match="duplicate"):
        assert_complete_fit_frame([d, dict(d)], EFF)


# ── req 4: hash-pinned fit-analysis consumption ────────────────────────────────────────


def _fit_analysis(measurement_shas, verdict="preserve_v5", **over) -> dict:
    n_pairs = len(expected_fit_cells(EFF)) // 2
    report = {"stage": "fit", "authoritative": True, "n_pairs": n_pairs, "verdict": verdict,
              "gates": [], "schema_version": "v3"}
    fa = {
        "kind": "fit_analysis", "report": report, "report_sha256": report_hash(report),
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(EFF),
        "pinned_inputs": {"measurement_sha256": {f"m{i}": s for i, s in enumerate(sorted(measurement_shas))}},
    }
    fa.update(over)
    return fa


def test_fit_analysis_valid_returns_verdict():
    shas = {"a" * 64, "b" * 64}
    assert validate_fit_analysis_receipt(_fit_analysis(shas), EFF, measurement_shas=shas) == "preserve_v5"


def test_fit_analysis_refuses_bad_report_hash():
    shas = {"a" * 64}
    fa = _fit_analysis(shas)
    fa["report_sha256"] = "0" * 64
    with pytest.raises(ExecutionError, match="report_sha256"):
        validate_fit_analysis_receipt(fa, EFF, measurement_shas=shas)


def test_fit_analysis_refuses_wrong_n_pairs():
    shas = {"a" * 64}
    fa = _fit_analysis(shas)
    fa["report"]["n_pairs"] = 5
    fa["report_sha256"] = report_hash(fa["report"])
    with pytest.raises(ExecutionError, match="pairs"):
        validate_fit_analysis_receipt(fa, EFF, measurement_shas=shas)


def test_fit_analysis_refuses_mismatched_pinned_set():
    fa = _fit_analysis({"a" * 64})
    with pytest.raises(ExecutionError, match="pinned measurement"):
        validate_fit_analysis_receipt(fa, EFF, measurement_shas={"a" * 64, "c" * 64})


# ── req 1/5/6: write_fit_verdict never fabricates pass ─────────────────────────────────


def _write_complete_frame(tmp_path) -> list[str]:
    paths = []
    for i, (arm, year, lid, seed) in enumerate(sorted(expected_fit_cells(EFF))):
        p = tmp_path / "measure" / "fit" / f"{i}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_mrec(arm, year, lid, seed)))
        paths.append(str(p))
    return paths


def test_write_fit_verdict_records_preserve_v5_not_pass(tmp_path):
    from blitz_engine.promotion.manifest import sha256_file

    paths = _write_complete_frame(tmp_path)
    shas = {sha256_file(p) for p in paths}
    fa = _fit_analysis(shas, verdict="preserve_v5")
    out = write_fit_verdict(tmp_path, effective=EFF, measurement_paths=paths, fit_analysis=fa)
    doc = json.loads(out.read_text())
    assert doc["verdict"] == "preserve_v5"      # inconclusive is NEVER laundered into pass
    assert doc["report_verdict"] == "preserve_v5"


def test_write_fit_verdict_passes_only_on_promote(tmp_path):
    from blitz_engine.promotion.manifest import sha256_file

    paths = _write_complete_frame(tmp_path)
    shas = {sha256_file(p) for p in paths}
    fa = _fit_analysis(shas, verdict="promote")
    out = write_fit_verdict(tmp_path, effective=EFF, measurement_paths=paths, fit_analysis=fa)
    assert json.loads(out.read_text())["verdict"] == "pass"
    # and the confirm gate then admits it
    assert require_fit_verdict(tmp_path, EFF)["verdict"] == "pass"


def test_write_fit_verdict_refuses_incomplete_frame(tmp_path):
    arm, year, lid, seed = _a_cell()
    p = tmp_path / "measure" / "fit" / "0.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(_mrec(arm, year, lid, seed)))
    with pytest.raises(ExecutionError, match="incomplete"):
        write_fit_verdict(tmp_path, effective=EFF, measurement_paths=[str(p)], fit_analysis={})


def test_confirm_refuses_preserve_v5_fit(tmp_path):
    from blitz_engine.promotion.manifest import sha256_file

    paths = _write_complete_frame(tmp_path)
    shas = {sha256_file(p) for p in paths}
    write_fit_verdict(tmp_path, effective=EFF, measurement_paths=paths,
                      fit_analysis=_fit_analysis(shas, verdict="preserve_v5"))
    with pytest.raises(ExecutionError, match="fit verdict is"):
        require_fit_verdict(tmp_path, EFF)
