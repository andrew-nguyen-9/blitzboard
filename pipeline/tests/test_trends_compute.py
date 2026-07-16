"""Unit tests for trends_compute (Epic E1).

Synthetic history fixtures only — no live network/DB. Asserts the invariants
the frontend depends on: rising usage → trend > 0.5, flat/no-history → 0.5,
rookies/empty history never crash, absent columns degrade to neutral, QB
starting signals track the depth chart + injury, and build_rows is idempotent.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trends_compute as tc  # noqa: E402


def _wk(season, week, **stats):
    return {"player_id": "p1", "season": season, "week": week, "stats": stats}


def test_rising_usage_trends_up():
    """Season starts low, last 4 weeks spike → every usage trend > 0.5."""
    hist = (
        [_wk(2024, w, targets=2, carries=1, target_share=0.05, routes_run=10)
         for w in range(1, 10)]
        + [_wk(2024, w, targets=10, carries=4, target_share=0.28, routes_run=35)
           for w in range(10, 14)]
    )
    t = tc.compute_trends(hist)
    assert t["opportunity_trend"] > 0.5
    assert t["target_share_trend"] > 0.5
    assert t["routes_trend"] > 0.5
    assert t["routes_run"] == 35.0  # recent-window avg count


def test_declining_usage_trends_down():
    hist = (
        [_wk(2024, w, targets=12, carries=3, target_share=0.30, routes_run=38)
         for w in range(1, 10)]
        + [_wk(2024, w, targets=2, carries=0, target_share=0.04, routes_run=8)
           for w in range(10, 14)]
    )
    t = tc.compute_trends(hist)
    assert t["opportunity_trend"] < 0.5
    assert t["target_share_trend"] < 0.5
    assert t["routes_trend"] < 0.5


def test_flat_usage_is_neutral():
    hist = [_wk(2024, w, targets=6, carries=2, target_share=0.15, routes_run=25)
            for w in range(1, 14)]
    t = tc.compute_trends(hist)
    assert t["opportunity_trend"] == 0.5
    assert t["target_share_trend"] == 0.5
    assert t["routes_trend"] == 0.5


def test_no_history_is_neutral():
    t = tc.compute_trends([])
    assert t == {"opportunity_trend": 0.5, "target_share_trend": 0.5,
                 "routes_run": 0.0, "routes_trend": 0.5}


def test_rookie_seasonal_only_no_crash():
    """Only season-aggregate (week=None) rows → no weekly window → neutral."""
    hist = [{"player_id": "p1", "season": 2024, "week": None,
             "stats": {"targets": 40}}]
    t = tc.compute_trends(hist)
    assert t["opportunity_trend"] == 0.5 and t["routes_run"] == 0.0


def test_absent_routes_column_degrades():
    """E2 not yet landed / column missing → routes_run 0, routes_trend neutral,
    but the other trends still compute."""
    hist = (
        [_wk(2024, w, targets=3, carries=1, target_share=0.06) for w in range(1, 10)]
        + [_wk(2024, w, targets=9, carries=3, target_share=0.25) for w in range(10, 14)]
    )
    t = tc.compute_trends(hist)
    assert t["routes_run"] == 0.0
    assert t["routes_trend"] == 0.5
    assert t["opportunity_trend"] > 0.5  # unaffected by the missing column


def test_null_and_nan_cells_are_safe():
    hist = [
        _wk(2024, 1, targets=None, carries=float("nan"), target_share=None),
        _wk(2024, 2, targets=5, carries=2, target_share=0.12, routes_run=20),
    ]
    t = tc.compute_trends(hist)  # must not raise
    assert 0.0 <= t["opportunity_trend"] <= 1.0


def test_qb_signals_by_depth_and_injury():
    starter = {"position": "QB", "metadata": {"depth_chart_order": 1}}
    backup = {"position": "QB", "metadata": {"depth_chart_order": 2}}
    hurt = {"position": "QB", "metadata": {"depth_chart_order": 1},
            "injury_status": "Out"}
    rb = {"position": "RB", "metadata": {"depth_chart_order": 1}}
    noorder = {"position": "QB", "metadata": {}}

    s_sp, s_js = tc.qb_signals(starter)
    b_sp, _ = tc.qb_signals(backup)
    h_sp, _ = tc.qb_signals(hurt)
    assert s_sp > b_sp > 0.0
    assert h_sp < s_sp  # injury suppresses the starter
    assert tc.qb_signals(rb) == (0.5, 0.5)      # non-QB neutral
    assert tc.qb_signals(noorder) == (0.5, 0.5)  # no depth info neutral


def test_build_rows_filters_and_is_idempotent():
    players = [
        {"id": "a", "position": "WR", "nfl_team": "DAL", "status": "Active",
         "metadata": {}},
        {"id": "b", "position": "QB", "nfl_team": "KC", "status": "Active",
         "metadata": {"depth_chart_order": 1}},
        {"id": "c", "position": "WR", "nfl_team": None, "status": "Active",
         "metadata": {}},  # no team → filtered
        {"id": "d", "position": "RB", "nfl_team": "SF", "status": "Inactive",
         "metadata": {}},  # inactive → filtered
    ]
    hist = {"a": [_wk(2024, w, targets=6, carries=1, target_share=0.15)
                  for w in range(1, 14)]}
    r1 = tc.build_rows(players, hist)
    r2 = tc.build_rows(players, hist)
    ids = {r["player_id"] for r in r1}
    assert ids == {"a", "b"}  # c/d filtered out
    # idempotent modulo updated_at timestamp
    strip = lambda rows: [{k: v for k, v in r.items() if k != "updated_at"} for r in rows]
    assert strip(r1) == strip(r2)
    a = next(r for r in r1 if r["player_id"] == "a")
    assert a["opportunity_trend"] == 0.5  # flat usage
    b = next(r for r in r1 if r["player_id"] == "b")
    assert b["starting_prob"] > 0.5  # QB1


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✓ {name}")
    print("\nall trends_compute tests passed")
