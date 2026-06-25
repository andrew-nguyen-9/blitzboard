"""Evaluate a drafted roster against actual weekly points: best legal starting lineup
each week, summed over the season. The lineup rule mirrors the frontend's fillRoster
(fill the most-restrictive slots first, highest scorer per slot) so the backtest and the
live board agree on what "optimal lineup" means.

Also scores a team head-to-head against the rest of the field and aggregates a policy's
per-team scores into a mean with a bootstrap 95% CI (numpy only — no scipy in the venv)."""
from __future__ import annotations

import numpy as np

# 10 starters: QB, RB, RB, WR, WR, TE, FLEX(RB/WR/TE), OP(QB/RB/WR/TE), DST, K.
SUPERFLEX_SLOTS: list[tuple[str, tuple[str, ...]]] = [
    ("QB", ("QB",)), ("RB", ("RB",)), ("RB", ("RB",)), ("WR", ("WR",)), ("WR", ("WR",)),
    ("TE", ("TE",)), ("FLEX", ("RB", "WR", "TE")), ("OP", ("QB", "RB", "WR", "TE")),
    ("DST", ("DST",)), ("K", ("K",)),
]


def optimal_week_points(roster_keys, pos_by_key, week_pts, slots) -> float:
    """Best legal starting lineup for one week: fill fewest-eligible slots first, taking
    the highest-scoring unused eligible player for each."""
    used: set[str] = set()
    order = sorted(range(len(slots)), key=lambda i: len(slots[i][1]))
    total = 0.0
    for i in order:
        _, elig = slots[i]
        best_key, best_pts = None, 0.0
        for k in roster_keys:
            if k in used or pos_by_key.get(k) not in elig:
                continue
            p = week_pts.get(k, 0.0)
            if best_key is None or p > best_pts:
                best_key, best_pts = k, p
        if best_key is not None:
            used.add(best_key)
            total += best_pts
    return total


def season_points_for(roster_keys, pos_by_key, actuals_by_week, slots=SUPERFLEX_SLOTS) -> float:
    """Sum of weekly-optimal points across the regular season (weeks 1..18)."""
    return float(sum(optimal_week_points(roster_keys, pos_by_key, actuals_by_week.get(w, {}), slots)
                     for w in range(1, 19)))


def h2h_record(team_idx, weekly_team_points) -> tuple[int, int, int]:
    """Record of one team vs. every other team, each week (W, L, T) — 'vs the field'."""
    me = weekly_team_points[team_idx]
    w = l = t = 0
    for opp_idx, opp in enumerate(weekly_team_points):
        if opp_idx == team_idx:
            continue
        for wk in range(len(me)):
            if me[wk] > opp[wk]:
                w += 1
            elif me[wk] < opp[wk]:
                l += 1
            else:
                t += 1
    return w, l, t


def aggregate(scores, iters: int = 2000, seed: int = 0) -> dict:
    """Mean of scores with a bootstrap 95% CI (numpy only)."""
    arr = np.asarray(scores, dtype=float)
    rng = np.random.default_rng(seed)
    means = arr[rng.integers(0, len(arr), size=(iters, len(arr)))].mean(axis=1)
    return {"mean": float(arr.mean()),
            "lo": float(np.percentile(means, 2.5)),
            "hi": float(np.percentile(means, 97.5))}
