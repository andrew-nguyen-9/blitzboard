"""v2.4.1.3 — orchestrator join + per-team weekly points assembly (pure, no network).

Plain asserts (no pytest in the venv):
    python tests/test_backtest_run.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.run import join_pool_to_actuals, weekly_team_points, _norm_name, _abbr_name   # noqa: E402
from backtest.evaluate import SUPERFLEX_SLOTS                                    # noqa: E402

actuals = [{"player_key": "a", "name": "A", "pos": "QB", "team": "X", "season": 2023, "week": 1, "points": 30.0},
           {"player_key": "b", "name": "B", "pos": "RB", "team": "Y", "season": 2023, "week": 1, "points": 12.0}]
pool = [{"id": "a", "pos": "QB"}, {"id": "b", "pos": "RB"}]
pos_by_key = join_pool_to_actuals(pool, actuals)
assert pos_by_key["a"] == "QB" and pos_by_key["b"] == "RB"

abw = {1: {"a": 30.0, "b": 12.0}}
wtp = weekly_team_points([["a", "b"]], {"a": "QB", "b": "RB"}, abw, SUPERFLEX_SLOTS)
assert wtp == [[42.0]], wtp     # QB 30 + RB 12, one week

# name normalization strips suffixes/punctuation so ADP joins to nflverse names
assert _norm_name("Patrick Mahomes II") == "patrick mahomes"
assert _norm_name("A.J. Brown") == "aj brown"

# kicker abbreviation bridge: nflverse "M.Prater" and FFC "Matt Prater" both → "mprater"
assert _abbr_name("M.Prater") == _abbr_name("Matt Prater") == "mprater"
assert _abbr_name("Justin Tucker") == "jtucker"
print("ok test_backtest_run")
