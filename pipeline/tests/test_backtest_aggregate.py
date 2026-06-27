"""v2.4.1.3 — H2H-vs-field record + bootstrap CI aggregation.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_aggregate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.evaluate import h2h_record, aggregate     # noqa: E402

# 3 teams, 2 weeks. Team 0 outscores both others every week → 4-0-0; team 1 loses all.
wtp = [[20.0, 25.0], [10.0, 12.0], [15.0, 18.0]]
assert h2h_record(0, wtp) == (4, 0, 0), h2h_record(0, wtp)
assert h2h_record(1, wtp) == (0, 4, 0), h2h_record(1, wtp)

agg = aggregate([100.0, 102.0, 98.0, 101.0, 99.0], seed=1)
assert 98.0 <= agg["lo"] <= agg["mean"] <= agg["hi"] <= 102.0, agg
assert abs(agg["mean"] - 100.0) < 1e-9, agg
print("ok test_backtest_aggregate")
