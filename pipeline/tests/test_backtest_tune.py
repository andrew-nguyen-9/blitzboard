"""v2.4.3.2 — tune/validate driver: baselines, ablations, grid select, report (pure parts).

Plain asserts (no pytest in the venv):
    python tests/test_backtest_tune.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.tune import (  # noqa: E402
    ablation_params,
    grid_configs,
    best_config,
    render_report,
    run_suite,
)

# ── ablation specs: each disables exactly one component, as a params override ──
abl = ablation_params()
assert set(abl) == {"no-kdef-cap", "no-bench-ceiling", "no-bench-injury", "naive-replacement"}, abl
assert abl["no-bench-ceiling"] == {"benchCeilingWeight": 0}, abl["no-bench-ceiling"]
assert abl["naive-replacement"] == {"runDepletion": 1}, abl["naive-replacement"]
# each override is a single-key dict (one component at a time)
assert all(len(v) == 1 for v in abl.values()), abl

# ── grid is a non-empty list of param-override dicts ──
grid = grid_configs()
assert isinstance(grid, list) and len(grid) >= 4, len(grid)
assert all(isinstance(c, dict) for c in grid), grid

# ── best_config picks max points mean, winpct as tiebreak ──
results = [
    ({"boomWeight": 0.5}, {"points": {"mean": 1500.0}, "winpct": {"mean": 50.0}}),
    ({"boomWeight": 0.65}, {"points": {"mean": 1600.0}, "winpct": {"mean": 52.0}}),  # best points
    ({"boomWeight": 0.35}, {"points": {"mean": 1600.0}, "winpct": {"mean": 49.0}}),  # ties points, worse winpct
]
cfg, agg = best_config(results)
assert cfg == {"boomWeight": 0.65}, cfg
assert agg["points"]["mean"] == 1600.0

# ── run_suite orchestrates baselines + ablations with an injected score_fn (no real sim) ──
calls = []
def fake_score(seasons, seeds, policy, rules, slots, params=None):
    calls.append((policy, params))
    # v2 beats both baselines; ablations slightly worse than full v2
    base = {"v2": 1600.0, "rawvorp": 1450.0, "adp": 1400.0}.get(policy, 1500.0)
    if params:  # an ablation / grid point — dampen a touch
        base -= 30.0
    return {"points": {"mean": base, "lo": base - 50, "hi": base + 50},
            "winpct": {"mean": 50.0, "lo": 47.0, "hi": 53.0},
            "seasons": list(seasons), "n": 96}

suite = run_suite([2023], seeds=2, score_fn=fake_score, do_grid=False)
assert suite["baselines"]["v2"]["points"]["mean"] == 1600.0
assert suite["baselines"]["rawvorp"]["points"]["mean"] == 1450.0
assert set(suite["ablations"]) == set(ablation_params()), suite["ablations"].keys()
# every ablation should land below full v2 here (the fake makes it so) — sanity of wiring
assert all(a["points"]["mean"] < 1600.0 for a in suite["ablations"].values())
# baselines called with no params; ablations called with their override on policy v2
assert ("v2", None) in calls and ("rawvorp", None) in calls
assert ("v2", {"benchCeilingWeight": 0}) in calls

# ── report renders markdown citing policies + the v2 advantage ──
md = render_report(suite, seasons=[2023], seeds=2)
assert "# v2.4 Backtest Report" in md
assert "raw-VORP" in md and "ADP-follow" in md  # baseline rows present
assert "beats" in md  # v2 verdict line (fake makes v2 win)
assert "no-bench-ceiling" in md
assert "1600" in md  # v2 mean shows up
assert "## Metric notes" in md and "mixed-policy" in md  # honest caveats present
print("ok test_backtest_tune")
