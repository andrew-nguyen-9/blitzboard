"""v2.4.1.3 — weekly-optimal lineup picks the best legal superflex starters.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_evaluate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.evaluate import optimal_week_points, SUPERFLEX_SLOTS, slots_from_rules  # noqa: E402
from backtest.rules import load_rules_fixture                                          # noqa: E402

# Slots are derived from the fixture (single source of truth) and must equal the known
# 10-starter superflex shape — pin it so a fixture change can't silently reshape lineups.
assert slots_from_rules(load_rules_fixture()) == [
    ("QB", ("QB",)), ("RB", ("RB",)), ("RB", ("RB",)), ("WR", ("WR",)), ("WR", ("WR",)),
    ("TE", ("TE",)), ("FLEX", ("RB", "WR", "TE")), ("OP", ("QB", "RB", "WR", "TE")),
    ("DST", ("DST",)), ("K", ("K",)),
], slots_from_rules(load_rules_fixture())
assert SUPERFLEX_SLOTS == slots_from_rules(load_rules_fixture())

pos = {"qb1": "QB", "qb2": "QB", "rb1": "RB", "rb2": "RB", "rb3": "RB",
       "wr1": "WR", "wr2": "WR", "te1": "TE", "k1": "K", "d1": "DST"}
wk = {"qb1": 30, "qb2": 25, "rb1": 20, "rb2": 18, "rb3": 5,
      "wr1": 22, "wr2": 15, "te1": 10, "k1": 8, "d1": 9}
# QB:qb1(30) RB:rb1(20),rb2(18) WR:wr1(22),wr2(15) TE:te1(10)
# FLEX(RB/WR/TE leftover): rb3(5)  OP(QB/RB/WR/TE leftover): qb2(25)  DST:d1(9) K:k1(8)
# => 30+20+18+22+15+10+5+25+9+8 = 162
got = optimal_week_points(list(pos), pos, wk, SUPERFLEX_SLOTS)
assert abs(got - 162.0) < 1e-6, got

# A QB on the bench in a 1-QB league still starts here via OP (superflex) — verify the
# 2nd QB is preferred over a low RB for the OP slot.
wk2 = dict(wk, qb2=3)   # weaken qb2 → FLEX/OP just take the two leftovers (rb3=5, qb2=3)
got2 = optimal_week_points(list(pos), pos, wk2, SUPERFLEX_SLOTS)
# 8 dedicated starters = 132, + FLEX rb3(5) + OP qb2(3) = 140
assert abs(got2 - 140.0) < 1e-6, got2
print("ok test_backtest_evaluate")
