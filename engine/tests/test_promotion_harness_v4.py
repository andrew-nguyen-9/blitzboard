"""Adversarial tests for the v4 draft/measurement harness — every refusal path. Non-authoritative.

Pure-validator paths are unit-tested directly; subprocess payload behaviour is proven by the real
two-stage rehearsal (receipts under `prep/c05-v4-rehearsal/`), whose summary these tests check.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from blitz_engine.promotion.execution import ExecutionError, checkout_head
from blitz_engine.promotion.harness_v4 import (
    CANDIDATE_SHA,
    EXEC_V2_SHA256,
    MEASUREMENT_SHA,
    V4_MANIFEST_SHA256,
    expected_roster_size,
    load_execution_manifest_v4,
    measure_arm,
    validate_draft_receipt,
    verify_measurement_checkout,
)
from blitz_engine.promotion.manifest import ManifestError
from blitz_engine.promotion.runner import HeldOutGuard, HeldOutLeakError, derive_eval_seed
from blitz_engine.testing import matrix

REPO = Path(__file__).resolve().parents[2]
ROW = next(r for r in matrix.all() if r["id"] == "t10-1qb-std-te0.0-b4-ir0")
SIZE = expected_roster_size(ROW)
BOARD = frozenset(f"p{i}" for i in range(400))


def draft_receipt(**over) -> dict:
    teams = int(ROW["teams"])
    rosters = [[f"p{s * SIZE + i}" for i in range(SIZE)] for s in range(teams)]
    base = {
        "kind": "draft",
        "arm": "v6_candidate",
        "policy_sha": CANDIDATE_SHA,
        "year": 2021,
        "league_id": ROW["id"],
        "base_seed": 2026082601,
        "eval_seed": derive_eval_seed(2026082601, 2021, ROW["id"]),
        "board_hash": "b" * 64,
        "seat_policy": ["static_proxy"] * teams,
        "rosters": rosters,
        "stage": "fit",
        "authoritative": False,
    }
    base.update(over)
    return base


# ── effective v4 manifest chain ────────────────────────────────────────────────────────


def test_v4_chain_loads_and_overlays(tmp_path):
    eff = load_execution_manifest_v4(REPO)
    assert eff["arms"]["candidate"]["combined_candidate_sha"] == CANDIDATE_SHA
    assert eff["evaluator"]["waiver_cost"] == 0.0
    v4 = eff["_v4"]
    assert v4["manifest_sha256"] == V4_MANIFEST_SHA256
    assert v4["exec_v2_sha256"] == EXEC_V2_SHA256
    assert v4["measurement_sha"] == MEASUREMENT_SHA
    assert len(v4["measurement_file_hashes"]) == 7
    assert "seat" in v4["pairing_keys"]


def test_v4_chain_refuses_tampered_files(tmp_path):
    exp = tmp_path / ".orchestrator-v6" / "experiments"
    exp.mkdir(parents=True)
    for name in (
        "promotion-v3.json", "promotion-v3-exec-v1.json", "promotion-v4.json",
        "promotion-v4-exec-v1.json", "promotion-v4-exec-v2.json",
    ):
        shutil.copy(REPO / ".orchestrator-v6" / "experiments" / name, exp / name)
    assert load_execution_manifest_v4(tmp_path)["_v4"]["measurement_sha"] == MEASUREMENT_SHA
    doc = json.loads((exp / "promotion-v4-exec-v2.json").read_text())
    doc["measurement"]["sha"] = "0" * 40
    (exp / "promotion-v4-exec-v2.json").write_text(json.dumps(doc))
    with pytest.raises(ManifestError, match="sha256"):
        load_execution_manifest_v4(tmp_path)  # hash pin fires before content is trusted


# ── measurement checkout verification ──────────────────────────────────────────────────


def test_measurement_checkout_refuses_wrong_head_and_file_drift(tmp_path):
    eff = load_execution_manifest_v4(REPO)
    with pytest.raises(ExecutionError, match="measurement checkout HEAD"):
        verify_measurement_checkout(REPO, eff)  # tooling head != frozen measurement SHA
    # file-drift path: fake checkout that fakes the right HEAD but has a drifted file
    eff2 = json.loads(json.dumps(eff))
    eff2["_v4"]["measurement_sha"] = checkout_head(REPO)
    eff2["_v4"]["measurement_file_hashes"] = {
        "engine/blitz_engine/promotion/harness_v4.py": "0" * 64
    }
    with pytest.raises(ExecutionError, match="measurement file drift"):
        verify_measurement_checkout(REPO, eff2)
    eff2["_v4"]["measurement_file_hashes"] = {"engine/does/not/exist.py": "0" * 64}
    with pytest.raises(ExecutionError, match="measurement file missing"):
        verify_measurement_checkout(REPO, eff2)


# ── exec-v2 roster rules ───────────────────────────────────────────────────────────────


def test_valid_draft_receipt_passes():
    validate_draft_receipt(draft_receipt(), ROW, BOARD)


def test_roster_size_violation_blocks():
    r = draft_receipt()
    r["rosters"][2] = r["rosters"][2][:-1]
    with pytest.raises(ExecutionError, match=f"expected exactly {SIZE}"):
        validate_draft_receipt(r, ROW, BOARD)


def test_duplicate_drafted_id_blocks():
    r = draft_receipt()
    r["rosters"][1][0] = r["rosters"][0][0]
    with pytest.raises(ExecutionError, match="globally unique"):
        validate_draft_receipt(r, ROW, BOARD)


def test_off_board_id_blocks():
    r = draft_receipt()
    r["rosters"][0][0] = "ghost-player"
    with pytest.raises(ExecutionError, match="not on the hashed board"):
        validate_draft_receipt(r, ROW, BOARD)


def test_seat_count_and_league_mismatch_block():
    r = draft_receipt()
    r["rosters"] = r["rosters"][:-1]
    with pytest.raises(ExecutionError, match="seat count"):
        validate_draft_receipt(r, ROW, BOARD)
    r2 = draft_receipt(league_id="t12-1qb-std-te0.0-b4-ir0")
    r2["eval_seed"] = derive_eval_seed(r2["base_seed"], r2["year"], r2["league_id"])
    with pytest.raises(ExecutionError, match="league_id"):
        validate_draft_receipt(r2, ROW, BOARD)


def test_wrong_eval_seed_blocks():
    with pytest.raises(ExecutionError, match="frozen derivation"):
        validate_draft_receipt(draft_receipt(eval_seed=1), ROW, BOARD)


def test_non_draft_receipt_blocks():
    with pytest.raises(ExecutionError, match="not a draft receipt"):
        validate_draft_receipt(draft_receipt(kind="measurement"), ROW, BOARD)


# ── stage isolation and write-once through measure_arm (pre-subprocess refusals) ───────


def test_measure_refuses_held_out_leak_and_wrong_checkout(tmp_path):
    eff = load_execution_manifest_v4(REPO)
    held = draft_receipt(year=2018)
    held["eval_seed"] = derive_eval_seed(held["base_seed"], 2018, held["league_id"])
    p = tmp_path / "draft" / "fit" / "x.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(held))
    with pytest.raises(HeldOutLeakError, match="2018"):
        measure_arm(
            p, REPO, effective=eff, n_seasons=1,
            guard=HeldOutGuard(eff["seasons"], eff["held_out_seasons"]),
            out_dir=tmp_path, tooling_root=REPO,
        )
    fit = draft_receipt()
    p2 = tmp_path / "draft" / "fit" / "y.json"
    p2.write_text(json.dumps(fit))
    with pytest.raises(ExecutionError, match="measurement checkout HEAD"):
        measure_arm(  # the tooling tree is refused as the measurement checkout
            p2, REPO, effective=eff, n_seasons=1,
            guard=HeldOutGuard(eff["seasons"], eff["held_out_seasons"]),
            out_dir=tmp_path, tooling_root=REPO,
        )


def test_confirm_stage_refuses_fit_year(tmp_path):
    eff = load_execution_manifest_v4(REPO)
    r = draft_receipt(stage="confirm")  # year 2021 = fit year
    p = tmp_path / "draft" / "confirm" / "z.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(r))
    with pytest.raises(HeldOutLeakError, match="confirm"):
        measure_arm(
            p, REPO, effective=eff, n_seasons=1,
            guard=HeldOutGuard(eff["seasons"], eff["held_out_seasons"]),
            out_dir=tmp_path, tooling_root=REPO,
        )


# ── the real two-stage rehearsal receipts (produced from the committed harness head) ───


REHEARSAL = REPO / ".orchestrator-v6" / "prep" / "c05-v4-rehearsal"


@pytest.mark.skipif(not REHEARSAL.exists(), reason="v4 rehearsal not yet generated")
def test_v4_rehearsal_measured_both_arms_through_the_common_evaluator():
    summary = json.loads((REHEARSAL / "rehearsal-summary.json").read_text())
    assert "NON-AUTHORITATIVE" in summary["label"]
    assert summary["measured_by"] == MEASUREMENT_SHA
    assert summary["arm_policy_heads"]["v5_shipped"] != summary["arm_policy_heads"]["v6_candidate"]
    assert summary["measurement_deterministic"] is True
    pairing = summary["pairing"]
    assert pairing["paired"] is True
    # the entire point of v4: BOTH arms now carry playoff/championship samples
    assert pairing["playoff_proxy_available_both_arms"] is True
    assert pairing["championship_proxy_available_both_arms"] is True
    for kind in ("measure", "draft"):
        receipts = list((REHEARSAL / kind / "fit").glob("*.json"))
        assert len(receipts) == 2
        for r in receipts:
            doc = json.loads(r.read_text())
            assert doc["authoritative"] is False
            assert doc["produced_by_tooling"]["tooling_tree_clean"] is True
    for r in (REHEARSAL / "measure" / "fit").glob("*.json"):
        doc = json.loads(r.read_text())
        assert doc["measured_by_sha"] == MEASUREMENT_SHA
        assert doc["measurement_file_hashes_verified"] is True
        assert doc["arm_run"]["playoff_proxy"] is not None
        assert doc["arm_run"]["championship_proxy"] is not None
