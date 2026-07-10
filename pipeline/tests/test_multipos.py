"""
E2 — multi-position analytics tests (models/multipos.py). Pure, no DB/network.

Proves: eligibility extraction from metadata.fantasy_positions, the scarcer slot
wins on VOR for a dual-eligible player, single-position degrade, and exactly one
primary flag.

    python tests/test_multipos.py  |  python -m pytest tests/test_multipos.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.multipos import (  # noqa: E402
    analyze, eligible_positions, is_multi_position, primary_position,
)


def _player(fps, position="RB"):
    return {"id": "p1", "position": position, "metadata": {"fantasy_positions": fps}}


def test_eligible_positions_from_metadata():
    assert eligible_positions(_player(["RB", "WR"])) == ("RB", "WR")
    # de-dupes and filters non-skill slots
    assert eligible_positions(_player(["WR", "WR", "K"])) == ("WR",)
    # falls back to primary position when fantasy_positions is empty
    assert eligible_positions({"position": "TE", "metadata": {}}) == ("TE",)
    # unknown → empty
    assert eligible_positions({"metadata": {}}) == ()
    print("✓ eligibility extraction + filtering")


def test_is_multi_position():
    assert is_multi_position(_player(["RB", "WR"])) is True
    assert is_multi_position(_player(["RB"])) is False
    print("✓ multi-position detection")


def test_scarcer_position_is_primary():
    """Same points, different replacement baselines: the player is most valuable at
    the position where replacement is HIGHER-scarcity (higher VOR)."""
    # WR replacement lower than RB → identical points yield MORE VOR at WR.
    repl = {"RB": 120.0, "WR": 95.0}
    lines = analyze(_player(["RB", "WR"]), projected_pts=140.0, replacement_by_pos=repl)
    assert lines[0].position == "WR"                 # best value first
    assert lines[0].primary is True and lines[1].primary is False
    assert lines[0].vor == 45.0 and lines[1].vor == 20.0
    assert primary_position(_player(["RB", "WR"]), 140.0, repl) == "WR"
    print("✓ scarcer slot wins:", [(l.position, l.vor) for l in lines])


def test_single_position_degrades_to_one_line():
    lines = analyze(_player(["RB"]), 140.0, {"RB": 120.0})
    assert len(lines) == 1 and lines[0].position == "RB" and lines[0].primary is True
    print("✓ single-position → one primary line")


def test_exactly_one_primary_on_tie():
    """Tied VOR must still yield exactly one primary flag."""
    lines = analyze(_player(["RB", "WR"]), 130.0, {"RB": 100.0, "WR": 100.0})
    assert sum(1 for l in lines if l.primary) == 1
    print("✓ exactly one primary even on a VOR tie")


def test_unknown_eligibility_is_empty():
    assert analyze({"metadata": {}}, 100.0, {}) == []
    assert primary_position({"metadata": {}}, 100.0, {}) is None
    print("✓ unknown eligibility → []")


def main():
    for fn in [
        test_eligible_positions_from_metadata, test_is_multi_position,
        test_scarcer_position_is_primary, test_single_position_degrades_to_one_line,
        test_exactly_one_primary_on_tie, test_unknown_eligibility_is_empty,
    ]:
        fn()
    print("\nALL MULTIPOS TESTS PASSED ✅")


if __name__ == "__main__":
    main()
