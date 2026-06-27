"""v2.4.1.1 — D/ST per-team-week aggregation scores under the seeded tiers.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_defense.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.rules import load_rules_fixture           # noqa: E402
from backtest.pbp_defense import team_week_dst           # noqa: E402
from models.scoring import score_defense                 # noqa: E402

# DEN defense: 1 sack, 1 INT, allowed 13 pts & 250 scrimmage yds in week 1 (KC the offense).
rows = [
    {"defteam": "DEN", "posteam": "KC", "play_type": "pass", "season": 2023, "week": 1, "sack": 1,
     "interception": 0, "fumble_lost": 0, "fumble_recovery_1_team": None, "safety": 0,
     "touchdown": 0, "return_touchdown": 0, "yards_gained": 150, "home_team": "DEN",
     "away_team": "KC", "home_score": 20, "away_score": 13},
    {"defteam": "DEN", "posteam": "KC", "play_type": "run", "season": 2023, "week": 1, "sack": 0,
     "interception": 1, "fumble_lost": 0, "fumble_recovery_1_team": None, "safety": 0,
     "touchdown": 0, "return_touchdown": 0, "yards_gained": 100, "home_team": "DEN",
     "away_team": "KC", "home_score": 20, "away_score": 13},
    # punt return: 60 return yards must NOT count as yards allowed (not a scrimmage play).
    {"defteam": "DEN", "posteam": "KC", "play_type": "punt", "season": 2023, "week": 1, "sack": 0,
     "interception": 0, "fumble_lost": 0, "fumble_recovery_1_team": None, "safety": 0,
     "touchdown": 0, "return_touchdown": 0, "yards_gained": 60, "home_team": "DEN",
     "away_team": "KC", "home_score": 20, "away_score": 13},
    # trailing administrative row with null posteam must NOT overwrite points_allowed
    # to DEN's own score (13). This was the contamination bug.
    {"defteam": "DEN", "posteam": None, "play_type": None, "season": 2023, "week": 1, "sack": 0,
     "interception": 0, "fumble_lost": 0, "fumble_recovery_1_team": None, "safety": 0,
     "touchdown": 0, "return_touchdown": 0, "yards_gained": 0, "home_team": "DEN",
     "away_team": "KC", "home_score": 20, "away_score": 13},
]
d = team_week_dst(rows)[("DEN", 2023, 1)]
assert d["sacks"] == 1 and d["interceptions"] == 1
assert d["yards_allowed"] == 250, d["yards_allowed"]      # 150+100, punt 60 excluded
assert d["points_allowed"] == 13, d["points_allowed"]     # KC's score, not DEN's
# score: sack 1 + int 2 + PA tier 7_13 -> 3 + YA tier 200_299 -> 2 = 8
got = score_defense(d, load_rules_fixture().scoring)
assert abs(got - 8.0) < 1e-6, got
print("ok test_backtest_defense")
