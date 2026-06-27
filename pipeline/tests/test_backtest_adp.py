"""v2.4.1.2 — ADP → bot-facing value reconstruction is monotone and well-formed.

Plain asserts (no pytest in the venv):
    python tests/test_backtest_adp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.rules import load_rules_fixture        # noqa: E402
from backtest.adp_pool import value_from_adp          # noqa: E402

rules = load_rules_fixture()
players = [{"player_key": f"p{i}", "name": f"P{i}", "pos": "RB", "team": "X", "adp": float(i)}
           for i in range(1, 41)]
out = value_from_adp(players, rules)
v = {p["player_key"]: p["value"] for p in out}
# earlier ADP ⇒ higher vor; strictly decreasing in ADP rank
assert v["p1"]["vor"] > v["p10"]["vor"] > v["p30"]["vor"]
# the replacement-level RB has vor ≈ 0 and ≤ the RB1's vor
rb_repl = rules.replacement_ranks()["RB"]
assert v[f"p{rb_repl}"]["vor"] <= v["p1"]["vor"]
# boom > projected mean (vor+replacement) > bust
assert v["p1"]["boom"] > v["p1"]["vor"] + v["p1"]["replacement"] > v["p1"]["bust"]
# overall rank is 1-indexed by ADP
assert v["p1"]["rank"] == 1
print("ok test_backtest_adp")
