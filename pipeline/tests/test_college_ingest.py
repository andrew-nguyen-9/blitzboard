"""
E2 — college_ingest tests. F2 adapter shape + degrade path + pure normalize.

Runs with NO key and NO Supabase, so the degrade contract is the default exercised:
missing CFBD_API_KEY → run() returns [] with no fetch, no write, no raise. normalize
is pure on a CFBD long-format fixture. No network.

    python tests/test_college_ingest.py  |  python -m pytest tests/test_college_ingest.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import common  # noqa: E402
from ingest.college_ingest import CollegeStatsAdapter, prospect_score  # noqa: E402

# CFBD /stats/player/season long format: one row per player×category×statType.
_FIXTURE = [
    {"playerId": "1001", "player": "Bijan Robinson", "team": "Texas", "conference": "Big 12",
     "season": 2022, "category": "rushing", "statType": "YDS", "stat": 1580},
    {"playerId": "1001", "player": "Bijan Robinson", "team": "Texas", "conference": "Big 12",
     "season": 2022, "category": "rushing", "statType": "TD", "stat": 18},
    {"playerId": "1001", "player": "Bijan Robinson", "team": "Texas", "conference": "Big 12",
     "season": 2022, "category": "receiving", "statType": "YDS", "stat": 314},
    {"playerId": "1001", "player": "Bijan Robinson", "team": "Texas", "conference": "Big 12",
     "season": 2022, "category": "receiving", "statType": "TD", "stat": 2},
    # a low-production player → low prospect score
    {"playerId": "2002", "player": "Backup Guy", "team": "Rice", "conference": "AAC",
     "season": 2022, "category": "rushing", "statType": "YDS", "stat": 60},
    # an ignored category/statType (defensive) must not crash normalize
    {"playerId": "2002", "player": "Backup Guy", "team": "Rice", "conference": "AAC",
     "season": 2022, "category": "defensive", "statType": "SACKS", "stat": 3},
]


def _no_key_no_supabase():
    os.environ.pop("CFBD_API_KEY", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    common.get_supabase.cache_clear()


def test_requires_key_and_degrades_without_it():
    _no_key_no_supabase()
    a = CollegeStatsAdapter(2022)
    assert a.requires_key == "CFBD_API_KEY"
    assert a.enabled is False
    # run() short-circuits: no fetch, no write, empty, no raise.
    a.fetch = lambda: (_ for _ in ()).throw(AssertionError("fetched while key absent"))  # type: ignore
    assert a.run() == []
    print("✓ missing CFBD_API_KEY degrades to []")


def test_normalize_pivots_and_scores():
    rows = CollegeStatsAdapter(2022).normalize(_FIXTURE)
    by_id = {r["cfbd_player_id"]: r for r in rows}
    bijan = by_id["1001"]
    assert bijan["stats"] == {"rush_yards": 1580.0, "rush_tds": 18.0,
                              "rec_yards": 314.0, "rec_tds": 2.0}
    assert bijan["college"] == "Texas" and bijan["season"] == 2022
    assert bijan["search_name"] == "bijan robinson"
    # productive prospect scores well above the low-production backup
    assert bijan["prospect_score"] > by_id["2002"]["prospect_score"]
    assert 0.0 <= by_id["2002"]["prospect_score"] <= 1.0
    print("✓ normalize pivots long→wide and scores prospects")


def test_normalize_is_pure_on_empty():
    assert CollegeStatsAdapter(2022).normalize([]) == []
    assert CollegeStatsAdapter(2022).normalize(None) == []
    print("✓ empty payload → no rows")


def test_prospect_score_neutral_on_empty_stats():
    assert prospect_score({}) == 0.5
    assert prospect_score({"rush_yards": 1800, "rush_tds": 22}) == 1.0  # clamps at ceiling
    print("✓ prospect_score anchors 0.5 empty, clamps 1.0")


def test_enrich_players_noops_offline():
    _no_key_no_supabase()
    rows = CollegeStatsAdapter(2022).normalize(_FIXTURE)
    # fetch_all returns [] with no Supabase → no players → no upsert, no raise.
    assert CollegeStatsAdapter(2022).enrich_players(rows) == 0
    print("✓ enrich_players no-ops offline")


def main():
    for fn in [
        test_requires_key_and_degrades_without_it, test_normalize_pivots_and_scores,
        test_normalize_is_pure_on_empty, test_prospect_score_neutral_on_empty_stats,
        test_enrich_players_noops_offline,
    ]:
        fn()
    print("\nALL COLLEGE-INGEST TESTS PASSED ✅")


if __name__ == "__main__":
    main()
