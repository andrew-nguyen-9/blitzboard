"""v2.4.1.1 — offense weekly scorer matches the seeded half-PPR rules.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_actuals_offense.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.rules import load_rules_fixture          # noqa: E402
from backtest.actuals import score_offense_week         # noqa: E402

sc = load_rules_fixture().scoring
# 300 pass yds (12) + 3 pass TD (12) - 1 INT (-2) + 50 rush yds (5) + 1 rush TD (6)
# + 5 rec (2.5) + 80 rec yds (8) + 1 rec TD (6) = 49.5
line = {"passing_yards": 300, "passing_tds": 3, "interceptions": 1,
        "rushing_yards": 50, "rushing_tds": 1,
        "receptions": 5, "receiving_yards": 80, "receiving_tds": 1}
assert abs(score_offense_week(line, sc) - 49.5) < 1e-6, score_offense_week(line, sc)
print("ok test_backtest_actuals_offense")
