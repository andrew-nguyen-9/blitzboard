"""C05-owned tests for the execution harness (freeze-review corrections). Non-authoritative."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from blitz_engine.promotion.execution import (
    CANDIDATE_SHA,
    EXEC_V1_SHA256,
    MANIFEST_SHA256,
    ExecutionError,
    arm_command,
    load_execution_manifest,
    verify_arm_checkout,
)
from blitz_engine.promotion.manifest import ManifestError

REPO = Path(__file__).resolve().parents[2]


def test_effective_manifest_injects_only_sha_and_binding():
    effective = load_execution_manifest(REPO)
    assert effective["arms"]["candidate"]["combined_candidate_sha"] == CANDIDATE_SHA
    assert effective["evaluator"]["waiver_cost"] == 0.0
    assert effective["_exec_addendum_sha256"] == EXEC_V1_SHA256
    # the on-disk manifest is untouched: its own copy still carries the immutable null
    disk = json.loads(
        (REPO / ".orchestrator-v6" / "experiments" / "promotion-v3.json").read_text()
    )
    assert disk["arms"]["candidate"]["combined_candidate_sha"] is None
    assert "waiver_cost" not in disk["evaluator"]


def _copy_frozen(tmp: Path) -> Path:
    d = tmp / ".orchestrator-v6" / "experiments"
    d.mkdir(parents=True)
    for name in ("promotion-v3.json", "promotion-v3-exec-v1.json"):
        shutil.copy(REPO / ".orchestrator-v6" / "experiments" / name, d / name)
    return tmp


def test_tampered_manifest_or_addendum_refuses_to_load(tmp_path):
    root = _copy_frozen(tmp_path)
    target = root / ".orchestrator-v6" / "experiments" / "promotion-v3-exec-v1.json"
    doc = json.loads(target.read_text())
    doc["metric_binding"]["waiver_cost"] = 0.5
    target.write_text(json.dumps(doc, indent=2) + "\n")
    with pytest.raises(ManifestError, match="sha256"):
        load_execution_manifest(root)  # hash pin fires before the binding is even read
    # untampered copy loads fine
    clean = load_execution_manifest(_copy_frozen(tmp_path / "clean"))
    assert clean["evaluator"]["waiver_cost"] == 0.0


def test_tooling_tree_is_refused_as_candidate_identity():
    # This repo checkout's HEAD is the C05 tooling head, NOT the frozen candidate SHA.
    with pytest.raises(ExecutionError, match="must come from the arm's own frozen checkout"):
        verify_arm_checkout(REPO, CANDIDATE_SHA)


def test_arm_command_pins_checkout_pythonpath():
    argv, env = arm_command("/some/checkout", "python3", 2021, "t10-1qb-std-te0.0-b4-ir0", 7, 1)
    assert env == {"PYTHONPATH": "/some/checkout/engine"}
    assert argv[0] == "python3" and argv[1] == "-c"
    payload_args = json.loads(argv[3])
    assert payload_args == [2021, "t10-1qb-std-te0.0-b4-ir0", 7, 1, 0.0, "/some/checkout/engine"]
    # the payload refuses any import resolution outside the arm checkout
    assert "resolved OUTSIDE the arm checkout" in argv[2]


def test_receipts_are_write_once_and_stage_separated(tmp_path):
    from blitz_engine.promotion.execution import checkout_head, produce_arm_receipt
    from blitz_engine.promotion.runner import HeldOutGuard, HeldOutLeakError

    effective = load_execution_manifest(REPO)
    head = checkout_head(REPO)  # use this repo as its own "arm checkout" so head-verify passes
    kw = dict(
        effective=effective, year=2021, league_id="t10-1qb-std-te0.0-b4-ir0",
        base_seed=2026082601, n_seasons=1, out_dir=tmp_path, tooling_root=REPO,
    )
    # held-out separation fires before any evaluator work
    with pytest.raises(HeldOutLeakError):
        produce_arm_receipt(
            "x", REPO, head, stage="fit", guard=HeldOutGuard([2021], [2018]),
            **{**kw, "year": 2018},
        )
    # write-once fires before the subprocess: pre-create the receipt path
    target = tmp_path / "fit" / "x-2021-t10-1qb-std-te0.0-b4-ir0-2026082601.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    with pytest.raises(ExecutionError, match="write-once"):
        produce_arm_receipt("x", REPO, head, stage="fit", guard=HeldOutGuard([2021], [2018]), **kw)


def test_frozen_pins_match_the_committed_files():
    from blitz_engine.promotion.manifest import sha256_file

    exp = REPO / ".orchestrator-v6" / "experiments"
    assert sha256_file(exp / "promotion-v3.json") == MANIFEST_SHA256
    assert sha256_file(exp / "promotion-v3-exec-v1.json") == EXEC_V1_SHA256


def test_tooling_provenance_is_mechanical_and_refuses_dirty_trees(monkeypatch):
    from blitz_engine.promotion import execution
    from blitz_engine.promotion.execution import checkout_head, tooling_provenance
    from blitz_engine.promotion.manifest import sha256_file

    # NOTE: only meaningful against a clean committed tree — the pre-commit run of this test
    # is expected to fail, which is exactly the property the reviewer demanded.
    prov = tooling_provenance(REPO)
    assert prov["tooling_head"] == checkout_head(REPO)
    assert prov["tooling_tree_clean"] is True
    assert prov["execution_module_sha256"] == sha256_file(
        REPO / "engine" / "blitz_engine" / "promotion" / "execution.py"
    )
    assert len(prov["effective_manifest_sha256"]) == 64
    monkeypatch.setattr(execution, "_tracked_dirty", lambda root: [" M some/file.py"])
    with pytest.raises(ExecutionError, match="committed clean tooling head"):
        tooling_provenance(REPO)
