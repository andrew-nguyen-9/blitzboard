"""Independent C05 v4 harness authority-boundary probes."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from blitz_engine.promotion.execution import ExecutionError
from blitz_engine.promotion.harness_v4 import (
    CANDIDATE_SHA,
    load_execution_manifest_v4,
    validate_draft_receipt,
)
from blitz_engine.promotion.runner import derive_eval_seed

from blitz_engine.simulation import season_eval
from blitz_engine.testing import matrix


def _root() -> Path:
    return Path(os.environ["C05_PROD_ROOT"])


def test_draft_receipt_refuses_arm_policy_identity_mismatch() -> None:
    root = _root()
    path = next(
        (root / ".orchestrator-v6/prep/c05-v4-rehearsal/draft/fit").glob(
            "v6_candidate-*.json"
        )
    )
    receipt = json.loads(path.read_text())
    receipt["arm"] = "v5_shipped"
    receipt["policy_sha"] = CANDIDATE_SHA
    row = next(r for r in matrix.all() if r["id"] == receipt["league_id"])
    board = frozenset(
        p.player_id for p in season_eval.build_players(receipt["year"], receipt["league_id"])
    )
    with pytest.raises(ExecutionError, match="arm.*policy|policy.*arm"):
        validate_draft_receipt(receipt, row, board)


def test_authoritative_constraints_are_frozen_in_effective_manifest() -> None:
    effective = load_execution_manifest_v4(_root())
    assert effective["evaluator"]["n_seasons"] == 8
    assert effective["seed_derivation"]["base_seeds"] == [
        2026082601,
        2026082602,
        2026082603,
        2026082604,
    ]
    assert derive_eval_seed(2026082601, 2021, "t10-1qb-std-te0.0-b4-ir0")
