"""
Roster source-of-truth tests (F3) — player → NFL-team mapping.

`player_ingest.normalize_team` is the single point that turns Sleeper's raw team
value into a CANONICAL NFL code (or None). Deterministic & re-runnable with no DB
(pure-function assertions). A final optional check hits live data IFF Supabase is
configured; it self-skips offline so `python -m pytest` is green anywhere — no
mutating probe, idempotent.

    python tests/test_roster_mapping.py
    python -m pytest tests/test_roster_mapping.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from player_ingest import NFL_TEAMS, normalize, normalize_team  # noqa: E402


def test_canonical_set_is_32_teams():
    assert len(NFL_TEAMS) == 32, sorted(NFL_TEAMS)
    print("✓ canonical NFL set has exactly 32 teams")


def test_legacy_aliases_map_to_canonical():
    """Relocated / variant abbreviations resolve to the current canonical code —
    the crux of the 'wrong NFL team' bug."""
    cases = {
        "OAK": "LV", "SD": "LAC", "STL": "LAR", "LA": "LAR", "SL": "LAR",
        "WSH": "WAS", "WFT": "WAS", "JAC": "JAX", "ARZ": "ARI", "BLT": "BAL",
        "CLV": "CLE", "HST": "HOU", "GBP": "GB", "KCC": "KC", "SFO": "SF",
        "TBB": "TB", "NOR": "NO", "NWE": "NE",
    }
    for raw, want in cases.items():
        assert normalize_team(raw) == want, (raw, normalize_team(raw), want)
    print(f"✓ {len(cases)} legacy/variant codes map to canonical teams")


def test_current_codes_pass_through():
    for code in NFL_TEAMS:
        assert normalize_team(code) == code, code
    print("✓ all 32 current codes pass through unchanged")


def test_case_and_whitespace_tolerant():
    assert normalize_team("  oak ") == "LV"
    assert normalize_team("kc") == "KC"
    print("✓ tolerant of case + Sleeper whitespace padding")


def test_non_team_and_unknown_become_none():
    """Free agents / retired / junk / an unrecognized code → None, never a wrong
    team (mis-attachment is the failure mode we're eliminating)."""
    for raw in (None, "", "FA", "NONE", "0", "RET", "  ", "XYZ", "ZZZ", 0):
        assert normalize_team(raw) is None, (raw, normalize_team(raw))
    print("✓ non-team / unknown values normalize to None")


def test_output_is_always_canonical_or_none():
    samples = ["OAK", "SD", "KC", "LAR", "FA", "", None, "JAC", "WSH", "bogus"]
    for raw in samples:
        out = normalize_team(raw)
        assert out is None or out in NFL_TEAMS, (raw, out)
    print("✓ output is always a canonical code or None")


def test_idempotent():
    """normalize_team(normalize_team(x)) == normalize_team(x)."""
    for raw in ["OAK", "SD", "LAR", "KC", "FA", None, "WSH", "bogus"]:
        once = normalize_team(raw)
        twice = normalize_team(once if once is not None else "")
        assert twice == once, (raw, once, twice)
    print("✓ normalize_team is idempotent")


def test_normalize_row_attaches_correct_team():
    """End-to-end through normalize(): a Sleeper record with a legacy team code
    lands on the correct canonical NFL team; a free agent gets None."""
    raider = normalize("100", {"full_name": "Test Raider", "position": "WR", "team": "OAK"})
    assert raider["nfl_team"] == "LV", raider
    charger = normalize("101", {"first_name": "Test", "last_name": "Bolt",
                                "position": "RB", "team": "SD"})
    assert charger["nfl_team"] == "LAC", charger
    fa = normalize("102", {"full_name": "Free Agent", "position": "TE", "team": None})
    assert fa["nfl_team"] is None, fa
    dst = normalize("KC", {"full_name": "Kansas City", "position": "DEF", "team": "KC"})
    assert dst["nfl_team"] == "KC", dst
    print("✓ normalize() attaches the correct canonical team end-to-end")


def test_live_roster_sanity_optional():
    """IFF Supabase is configured, every non-null nfl_team in `players` is a
    canonical code (no mis-attached / stale rows). Self-skips offline."""
    try:
        from common import fetch_all, get_supabase
    except Exception as e:  # pragma: no cover - import guard
        print(f"… live check skipped (import: {e})")
        return
    if get_supabase() is None:
        print("… live check skipped (Supabase unconfigured)")
        return
    rows = fetch_all("players", "full_name,position,nfl_team")
    bad = [r for r in rows if r.get("nfl_team") and r["nfl_team"] not in NFL_TEAMS]
    assert not bad, f"{len(bad)} rows with non-canonical nfl_team, e.g. {bad[:10]}"
    print(f"✓ live: {len(rows)} players, all teams canonical")


def main():
    test_canonical_set_is_32_teams()
    test_legacy_aliases_map_to_canonical()
    test_current_codes_pass_through()
    test_case_and_whitespace_tolerant()
    test_non_team_and_unknown_become_none()
    test_output_is_always_canonical_or_none()
    test_idempotent()
    test_normalize_row_attaches_correct_team()
    test_live_roster_sanity_optional()
    print("\nALL ROSTER-MAPPING TESTS PASSED ✅")


if __name__ == "__main__":
    main()
