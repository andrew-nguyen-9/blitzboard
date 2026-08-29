from __future__ import annotations

import csv
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import value_engine_run
from models import (
    PlayerValue,
    blend_rankings,
    load_draft_sheet,
)


def test_load_draft_sheet_reads_visible_position_blocks(tmp_path):
    """Moving or misreading a block must not assign a player's points to another position."""
    rows = [[""] * 30 for _ in range(5)]
    rows[0][1], rows[0][11], rows[0][21] = "QUARTERBACK", "RUNNING BACK", "WIDE RECEIVER"
    for start in (1, 11, 21):
        rows[1][start : start + 8] = ["TIER", "NAME", "TM/BYE", "PTS", "VALUE", "PS", "ECR", "DRAFT"]
    rows[2][1:9] = ["1", "Josh Allen", "BUF/7", "305", "62", "73%", "QB1", ""]
    rows[2][11:19] = ["1", "James Cook III", "BUF/7", "209", "95", "93%", "RB5", ""]
    rows[2][21:29] = ["1", "Puka Nacua", "LAR/11", "233", "127", "93%", "WR2", ""]
    rows[3][1] = "TIGHT END"
    rows[4][1:9] = ["1", "Brock Bowers", "LV/13", "164", "52", "80%", "TE1", ""]
    path = tmp_path / "DraftSheet.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)

    ranks = load_draft_sheet(path)

    assert ranks["josh allen"] == {
        "name": "Josh Allen", "position": "QB", "points": 305.0,
        "value": 62.0, "tier": 1, "position_rank": 1.0,
    }
    assert ranks["james cook"]["name"] == "James Cook III"
    assert ranks["james cook"]["position"] == "RB"
    assert ranks["puka nacua"]["points"] == 233.0
    assert ranks["brock bowers"]["tier"] == 1


def test_blend_rankings_reassigns_existing_value_slots_without_changing_vor():
    """A private reorder must not manufacture new value magnitudes or projection points."""
    values = [
        PlayerValue("a", "vorp", 30.0, 12.0, 100.0, 1),
        PlayerValue("b", "vorp", 20.0, 11.0, 100.0, 2),
        PlayerValue("c", "vorp", 10.0, 10.0, 100.0, 3),
    ]
    rankings = {
        "alpha": {"name": "Alpha", "position": "RB", "value": 1.0, "tier": 3, "position_rank": 3.0},
        "bravo": {"name": "Bravo", "position": "RB", "value": 2.0, "tier": 2, "position_rank": 2.0},
        "charlie": {"name": "Charlie", "position": "RB", "value": 3.0, "tier": 1, "position_rank": 1.0},
    }

    result = blend_rankings(
        values,
        names={"a": "Alpha", "b": "Bravo", "c": "Charlie"},
        positions={"a": "RB", "b": "RB", "c": "RB"},
        rankings=rankings,
        weight=1.0,
    )

    assert [(row.player_id, row.value, row.vor, row.rank) for row in result] == [
        ("c", 30.0, 10.0, 1),
        ("b", 20.0, 11.0, 2),
        ("a", 10.0, 12.0, 3),
    ]


def test_value_engine_cli_exposes_private_draft_sheet_input():
    """Removing the opt-in flag would make the private source impossible to select safely."""
    result = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "..", "value_engine_run.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--draft-sheet DRAFT_SHEET" in result.stdout
    assert "--draft-sheet-weight DRAFT_SHEET_WEIGHT" in result.stdout


def test_value_engine_accepts_private_sheet_for_smores_superflex(monkeypatch):
    """Restoring the old 1QB guard must not reject the Smores league."""
    monkeypatch.setattr(sys, "argv", ["value_engine_run.py", "--draft-sheet", "sheet.csv"])
    monkeypatch.setattr(value_engine_run, "get_supabase", lambda: object())
    monkeypatch.setattr(
        value_engine_run,
        "load_league_rules",
        lambda _league: SimpleNamespace(league_size=12, is_superflex=True),
    )

    def reached_engine(_sb, _season):
        raise RuntimeError("superflex sheet accepted")

    monkeypatch.setattr(value_engine_run, "enrich_byes", reached_engine)
    with pytest.raises(RuntimeError, match="superflex sheet accepted"):
        value_engine_run.main()
