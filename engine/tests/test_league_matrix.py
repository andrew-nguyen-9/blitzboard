"""E7a: the league-config matrix loader (`blitz_engine.testing.matrix`)."""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import pytest

from blitz_engine.testing import matrix

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "league_matrix.json"
FACTORS = ["teams", "qb_mode", "scoring", "te_premium", "bench_slots", "ir_slots"]


def _expected_slots(qb_mode: str) -> dict[str, int]:
    slots = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1}
    if qb_mode == "superflex":
        slots["SUPERFLEX"] = 1
    elif qb_mode == "2qb":
        slots["QB"] = 2
    slots["K"] = 1
    slots["DST"] = 1
    return slots


def test_all_returns_exactly_432_rows():
    assert len(matrix.all()) == 432


def test_ids_are_unique():
    ids = [r["id"] for r in matrix.all()]
    assert len(ids) == len(set(ids))


def test_starting_slots_match_derivation():
    for row in matrix.all():
        assert row["starting_slots"] == _expected_slots(row["qb_mode"])


def test_smoke_has_16_existing_ids():
    ids = matrix.smoke()
    assert len(ids) == 16
    all_ids = {r["id"] for r in matrix.all()}
    for row in ids:
        assert row["id"] in all_ids


def test_smoke_is_pairwise_covering():
    rows = matrix.smoke()
    factor_levels = {f: {r[f] for r in matrix.all()} for f in FACTORS}
    for a, b in combinations(FACTORS, 2):
        needed = {(la, lb) for la in factor_levels[a] for lb in factor_levels[b]}
        covered = {(r[a], r[b]) for r in rows}
        assert covered == needed, f"{a}x{b} not fully covered by smoke set"


def test_by_id_matches_raw_json():
    raw = json.loads(FIXTURE_PATH.read_text())
    for raw_row in raw["rows"][::37]:  # sample across the grid, cheap but not exhaustive
        assert matrix.by_id(raw_row["id"]) == raw_row


def test_by_id_unknown_raises():
    with pytest.raises(KeyError):
        matrix.by_id("does-not-exist")


def test_to_league_config_seed_is_stable_per_row():
    row = matrix.by_id("t12-superflex-ppr-te0.0-b6-ir1")
    cfg1 = matrix.to_league_config(row)
    cfg2 = matrix.to_league_config(row)
    assert cfg1.seed == cfg2.seed
    other = matrix.by_id("t8-1qb-std-te0.0-b4-ir0")
    assert matrix.to_league_config(other).seed != cfg1.seed
