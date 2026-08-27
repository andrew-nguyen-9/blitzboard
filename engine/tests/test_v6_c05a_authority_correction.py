"""C05A authority/provenance correction — one adversarial test per reviewer refusal (6c63808).

Non-authoritative. Pure-validator paths run directly; `measure_arm` paths pass REPO as a clean
committed tooling root so `tooling_provenance` passes and the new authority checks are reached.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from blitz_engine.promotion.execution import ExecutionError
from blitz_engine.promotion.harness_v4 import (
    load_execution_manifest_v4,
    mandatory_league_ids,
    measure_arm,
)
from blitz_engine.promotion.runner import HeldOutGuard
from blitz_engine.testing import matrix

REPO = Path(__file__).resolve().parents[2]
EFFECTIVE = load_execution_manifest_v4(REPO)
REAL_FIT = REPO / ".orchestrator-v6" / "prep" / "c05-v4-rehearsal" / "draft" / "fit"


def _real_receipt(arm: str = "v6_candidate") -> dict:
    return json.loads(next(REAL_FIT.glob(f"{arm}-*.json")).read_text())


def _row(receipt: dict) -> dict:
    return next(r for r in matrix.all() if r["id"] == receipt["league_id"])


def _board(receipt: dict) -> frozenset[str]:
    from blitz_engine.simulation import season_eval as se

    return frozenset(p.player_id for p in se.build_players(receipt["year"], receipt["league_id"]))


def _guard() -> HeldOutGuard:
    return HeldOutGuard(list(EFFECTIVE["seasons"]), list(EFFECTIVE["held_out_seasons"]))


# ── req 1: draft/measurement authority must match ──────────────────────────────────────


def test_measure_refuses_authoritative_on_nonauthoritative_draft(tmp_path):
    r = _real_receipt()
    assert r["authoritative"] is False
    p = tmp_path / "draft" / "fit" / "x.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(r))
    with pytest.raises(ExecutionError, match="authorit"):
        measure_arm(
            p, REPO, effective=EFFECTIVE, n_seasons=8, guard=_guard(),
            out_dir=tmp_path, tooling_root=REPO, authoritative=True,
        )


# ── req 2: authoritative frame derived exclusively from the frozen manifest ────────────


def _authoritative_receipt(tmp_path, name="a.json", **over) -> Path:
    r = _real_receipt()
    r["authoritative"] = True
    r.update(over)
    p = tmp_path / "draft" / "fit" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(r))
    return p


def _measure_auth(path, n_seasons=8):
    return measure_arm(
        path, REPO, effective=EFFECTIVE, n_seasons=n_seasons, guard=_guard(),
        out_dir=path.parent.parent.parent, tooling_root=REPO, authoritative=True,
    )


def test_mandatory_league_ids_is_the_frozen_216():
    ids = mandatory_league_ids(EFFECTIVE)
    assert len(ids) == 216
    assert "t10-1qb-std-te0.0-b4-ir0" in ids
    assert "t8-1qb-std-te0.0-b4-ir0" not in ids  # t8 is not mandatory


def test_authoritative_measure_refuses_n_seasons_override(tmp_path):
    p = _authoritative_receipt(tmp_path)
    with pytest.raises(ExecutionError, match="n_seasons"):
        _measure_auth(p, n_seasons=1)


def test_authoritative_refuses_nonframe_base_seed(tmp_path):
    p = _authoritative_receipt(tmp_path, base_seed=999999999)
    with pytest.raises(ExecutionError, match="base_seed"):
        _measure_auth(p)


def test_authoritative_refuses_nonmandatory_league(tmp_path):
    p = _authoritative_receipt(tmp_path, league_id="t8-1qb-std-te0.0-b4-ir0")
    with pytest.raises(ExecutionError, match="mandatory"):
        _measure_auth(p)
