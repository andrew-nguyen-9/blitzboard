"""Evaluate a drafted roster against actual weekly points: best legal starting lineup
each week, summed over the season. The lineup rule mirrors the frontend's fillRoster
(fill the most-restrictive slots first, highest scorer per slot) so the backtest and the
live board agree on what "optimal lineup" means."""
from __future__ import annotations

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
