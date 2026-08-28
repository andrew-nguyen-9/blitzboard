"""E7b — the corpus is a *deterministic* product; these tests are the guarantee.

A flaky corpus makes every downstream ablation unreadable, so we check the three things that
can rot: the fixtures load identically twice, every e7a smoke() row has a golden draft whose
rosters are legal under that row's shape, and the generator still reproduces a checked-in file
byte for byte (one cheap row guards the whole sweep).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from blitz_engine.testing import corpus, matrix

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
CHEAP_ROW = "t8-1qb-std-te0.0-b4-ir0"  # 8 teams x 13 rounds — the smallest smoke row

ELIGIBLE = {
    "QB": {"QB"},
    "RB": {"RB"},
    "WR": {"WR"},
    "TE": {"TE"},
    "FLEX": {"RB", "WR", "TE"},
    "SUPERFLEX": {"QB", "RB", "WR", "TE"},
    "K": {"K"},
    "DST": {"DST", "DEF"},
}
# ── determinism ────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("year", corpus.SEASONS)
def test_season_loads_identically_twice(year: int) -> None:
    a, b = corpus.season(year), corpus.season(year)
    assert a == b
    a["players"][0]["name"] = "MUTATED"  # the cache must hand out copies, not shared state
    assert corpus.season(year)["players"][0]["name"] != "MUTATED"


def test_golden_draft_loads_identically_twice() -> None:
    a, b = corpus.golden_draft(CHEAP_ROW), corpus.golden_draft(CHEAP_ROW)
    assert a == b
    a["picks"].clear()
    assert corpus.golden_draft(CHEAP_ROW)["picks"]


def test_player_pool_is_stable_and_row_scored() -> None:
    pool = corpus.player_pool(corpus.GOLDEN_SEASON, CHEAP_ROW)
    assert pool == corpus.player_pool(corpus.GOLDEN_SEASON, CHEAP_ROW)
    assert [p["projection"] for p in pool] == sorted(
        (p["projection"] for p in pool), reverse=True
    )
    # a PPR row must value a receiver strictly above the same player in a standard row
    ppr_row = next(r for r in matrix.smoke() if r["scoring"] == "ppr")
    ppr = {p["player_id"]: p for p in corpus.player_pool(corpus.GOLDEN_SEASON, ppr_row["id"])}
    std = {p["player_id"]: p for p in pool}
    wr = next(p for p in pool if p["position"] == "WR" and p["actual_points"] > 100)
    assert ppr[wr["player_id"]]["actual_points"] > std[wr["player_id"]]["actual_points"]


# ── shape of the season slices ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("year", corpus.SEASONS)
def test_season_slice_is_well_formed(year: int) -> None:
    doc = corpus.season(year)
    assert doc["season"] == year and doc["weeks"] >= 16
    keys = {corpus.scoring_key(s, t) for s in corpus.SCORINGS for t in corpus.TE_PREMIUMS}
    positions = set()
    for p in doc["players"]:
        assert set(p["points"]) == keys and set(p["preseason"]) == keys
        assert all(len(v) == doc["weeks"] for v in p["points"].values())
        assert p["bye_week"] is None or 1 <= p["bye_week"] <= doc["weeks"]
        positions.add(p["position"])
    assert {"QB", "RB", "WR", "TE", "K", "DST"} <= positions  # every draftable slot has bodies


def test_unknown_season_and_row_raise() -> None:
    with pytest.raises(KeyError):
        corpus.season(1999)
    with pytest.raises(KeyError):
        corpus.golden_draft("not-a-row")


# ── golden drafts ──────────────────────────────────────────────────────────────────────
def test_every_smoke_row_has_a_golden_draft() -> None:
    missing = [
        r["id"] for r in matrix.smoke()
        if not (corpus.GOLDEN_DIR / f"{r['id']}.json").exists()
    ]
    assert not missing, f"smoke rows without a golden draft: {missing}"


@pytest.mark.parametrize("row", matrix.smoke(), ids=lambda r: r["id"])
def test_golden_draft_rosters_are_legal(row: dict) -> None:
    g = corpus.golden_draft(row["id"])
    rounds = sum(row["starting_slots"].values()) + row["bench_slots"]
    assert (g["num_teams"], g["rounds"], g["seed"]) == (row["teams"], rounds, corpus.GOLDEN_SEED)

    drafted = [pid for team in g["rosters"] for pid in team]
    assert len(set(drafted)) == len(drafted), "a player was drafted twice"
    assert len(g["rosters"]) == row["teams"]
    assert all(len(t) == rounds for t in g["rosters"]), "a team did not fill its roster"

    pos = {p["player_id"]: p["position"] for p in corpus.player_pool(g["season"], row["id"])}
    for team_starters in g["starters"]:
        assert [s["slot"] for s in team_starters] == [
            slot for slot, n in row["starting_slots"].items() for _ in range(n)
        ]
        for s in team_starters:
            if s["player_id"] is not None:
                assert pos[s["player_id"]] in ELIGIBLE[s["slot"]], f"{s} ineligible"


@pytest.mark.parametrize("row", matrix.smoke(), ids=lambda r: r["id"])
def test_golden_drafts_fill_every_required_starter(row: dict) -> None:
    for team_starters in corpus.golden_draft(row["id"])["starters"]:
        empty = [s["slot"] for s in team_starters if s["player_id"] is None]
        assert not empty, f"empty starter slot(s) {empty} in {row['id']}"


# ── the generator still reproduces the checked-in bytes ────────────────────────────────
def test_generator_reproduces_one_row_byte_for_byte() -> None:
    tsx = FRONTEND / "node_modules" / ".bin" / "tsx"
    if not tsx.exists() or shutil.which("node") is None:
        pytest.skip("frontend deps not installed — run `npm ci` in frontend/ to exercise this")
    before = (corpus.GOLDEN_DIR / f"{CHEAP_ROW}.json").read_bytes()
    proc = subprocess.run(
        [str(tsx), "scripts/gen-golden-drafts.mjs", "--check", "--row", CHEAP_ROW],
        cwd=FRONTEND, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, f"golden draft drifted:\n{proc.stdout}\n{proc.stderr}"
    assert (corpus.GOLDEN_DIR / f"{CHEAP_ROW}.json").read_bytes() == before  # --check never writes


def test_golden_files_are_canonical_json() -> None:
    """Byte-stability needs a canonical encoding: compact separators, trailing newline."""
    for row in matrix.smoke():
        raw = (corpus.GOLDEN_DIR / f"{row['id']}.json").read_text()
        assert raw.endswith("}\n") and ", " not in raw[: raw.index("[")]
        json.loads(raw)
