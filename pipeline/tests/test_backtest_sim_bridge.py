"""v2.4.1.2 — the python→node sim bridge runs a full mock draft deterministically.

Spawns the real Node bridge (needs frontend/node_modules/.bin/tsx). Plain asserts:
    python tests/test_backtest_sim_bridge.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.sim_bridge import run_draft               # noqa: E402

players = [{"id": f"pl{i}", "full_name": f"P{i}",
            "position": ["QB", "RB", "WR", "TE", "K", "DST"][i % 6],
            "bye_week": (i % 14) + 1, "nfl_team": f"T{i % 32}", "metadata": {},
            "value": {"vor": 200 - i, "replacement": 50, "boom": 220 - i,
                      "bust": 180 - i, "adp": i + 1, "rank": i + 1}}
           for i in range(200)]
a = run_draft(players, seed=7, num_teams=12)
b = run_draft(players, seed=7, num_teams=12)
assert a == b, "bridge must be deterministic per seed"
assert len(a) == 12, len(a)
flat = [pid for team in a for pid in team]
assert len(set(flat)) == len(flat), "no player drafted twice"
assert all(len(team) == 16 for team in a), [len(t) for t in a]
print("ok test_backtest_sim_bridge")
