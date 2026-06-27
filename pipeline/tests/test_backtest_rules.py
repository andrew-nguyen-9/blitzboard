"""v2.4.1.1 — offline league-rules fixture loads with the seeded Smores config.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_rules.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.rules import load_rules_fixture  # noqa: E402

r = load_rules_fixture()
assert r.league_size == 12
assert r.is_superflex is True
assert r.scoring["receiving"]["ppr"] == 0.5            # half-PPR
assert r.scoring["kicking"]["fg_50_59"] == 5           # distance K
assert r.scoring["dst"]["points_allowed"]["0"] == 5    # PA tier
# OP (superflex) pushes QB demand above one-per-team (12); pure slot demand ≈ 15.
assert r.replacement_ranks()["QB"] > 12, r.replacement_ranks()["QB"]
print("ok test_backtest_rules")
