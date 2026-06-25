"""v2.4.1.1 — distance-based kicker buckets score under the seeded rules.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_kicking.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.rules import load_rules_fixture            # noqa: E402
from backtest.pbp_kicking import kicker_week_buckets      # noqa: E402
from models.scoring import score_kicking                  # noqa: E402

rows = [
    {"play_type": "field_goal", "field_goal_result": "made", "kick_distance": 25,
     "kicker_player_id": "K1", "season": 2023, "week": 1},
    {"play_type": "field_goal", "field_goal_result": "made", "kick_distance": 52,
     "kicker_player_id": "K1", "season": 2023, "week": 1},
    {"play_type": "field_goal", "field_goal_result": "missed", "kick_distance": 47,
     "kicker_player_id": "K1", "season": 2023, "week": 1},
    {"play_type": "extra_point", "extra_point_result": "good",
     "kicker_player_id": "K1", "season": 2023, "week": 1},
]
b = kicker_week_buckets(rows)[("K1", 2023, 1)]
assert b["fg_made_0_39"] == 1 and b["fg_made_50_59"] == 1
assert b["fg_missed"] == 1 and b["pat_made"] == 1
# score: 3 (0-39) + 5 (50-59) - 1 (miss) + 1 (pat) = 8
assert abs(score_kicking(b, load_rules_fixture().scoring) - 8.0) < 1e-6
print("ok test_backtest_kicking")
