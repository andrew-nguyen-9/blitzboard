"""
trends_compute.py — per-player opportunity trends → `player_trends` (Epic E1).

Reads the existing `player_stats_history` weekly rows (`stats` JSON keyed by
`history_ingest.STAT_COLS`) and computes, per active player, a recent-window-vs-
season trend of usage: total opportunities (targets + carries), target share,
and routes run. QB `starting_prob` / `job_security` come from the Sleeper depth
chart (`metadata.depth_chart_order`) + injury status.

Every trend is a 0..1 signal where **0.5 == neutral/flat** (rising usage > 0.5,
declining < 0.5). Cascade-safe: a rookie / player with no history / an absent
`stats` column yields 0.5 (or 0 for the raw `routes_run` count) rather than a
crash. Idempotent upsert of one row per active player, safe to re-run.

Usage:
    python trends_compute.py
"""
from __future__ import annotations

from datetime import datetime, timezone

from common import console, fetch_all, upsert

# Recent window: the last N weekly rows of a player's latest season vs the whole
# season. ≈ last 4 weeks captures a role change (breakout / phased-out) without
# being so short that one boom/bust game dominates.
RECENT_WEEKS = 4

NEUTRAL = 0.5

# injury_status values (lowercased) that meaningfully suppress a QB's start odds.
_OUT_STATUSES = {"out", "ir", "pup", "sus", "susp", "doubtful", "d"}
_QUESTIONABLE = {"questionable", "q"}

# Sleeper `status` values that mean "not on an active NFL roster right now".
_INACTIVE_STATUSES = {"inactive", "retired", "non_roster", "cut"}


def _num(v):
    """Coerce a stats-JSON cell to float, or None if missing/non-numeric/NaN."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN guard


def _avg(values: list[float]) -> float | None:
    """Mean of the present (non-None) values, or None if there are none."""
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _trend(recent: float | None, season: float | None) -> float:
    """Map a recent-window avg vs a season avg onto 0..1 with 0.5 == flat.

    Uses the symmetric ratio (recent - season) / (recent + season) ∈ [-1, 1],
    so a doubling and a halving are equal-magnitude moves and the result is
    bounded without a hand-tuned scale. Missing either side → neutral.
    """
    if recent is None or season is None:
        return NEUTRAL
    denom = recent + season
    if denom <= 0:
        return NEUTRAL
    return round(0.5 + 0.5 * (recent - season) / denom, 4)


def _weekly_rows(history: list[dict]) -> list[dict]:
    """A player's weekly (week != null) history, oldest→newest by (season, week)."""
    weekly = [h for h in history if h.get("week") is not None]
    return sorted(weekly, key=lambda h: (h.get("season") or 0, h.get("week") or 0))


def _metric_series(rows: list[dict], value_fn) -> list[float | None]:
    return [value_fn(r.get("stats") or {}) for r in rows]


def _opportunity(stats: dict) -> float | None:
    """Total weekly opportunities = targets + carries (present cells only)."""
    t, c = _num(stats.get("targets")), _num(stats.get("carries"))
    if t is None and c is None:
        return None
    return (t or 0.0) + (c or 0.0)


def compute_trends(history: list[dict]) -> dict:
    """Trend fields for one player from their full stats history.

    No history (rookie / unmatched) → every field neutral (routes_run 0).
    """
    rows = _weekly_rows(history)
    if not rows:
        return {
            "opportunity_trend": NEUTRAL,
            "target_share_trend": NEUTRAL,
            "routes_run": 0.0,
            "routes_trend": NEUTRAL,
        }

    latest_season = rows[-1].get("season")
    season_rows = [r for r in rows if r.get("season") == latest_season]
    recent_rows = season_rows[-RECENT_WEEKS:]

    def field(value_fn):
        recent = _avg(_metric_series(recent_rows, value_fn))
        season = _avg(_metric_series(season_rows, value_fn))
        return recent, season

    opp_recent, opp_season = field(_opportunity)
    ts_recent, ts_season = field(lambda s: _num(s.get("target_share")))
    rt_recent, rt_season = field(lambda s: _num(s.get("routes_run")))

    return {
        "opportunity_trend": _trend(opp_recent, opp_season),
        "target_share_trend": _trend(ts_recent, ts_season),
        # Raw recent-window routes count (0 when the column is absent everywhere).
        "routes_run": round(rt_recent, 2) if rt_recent is not None else 0.0,
        "routes_trend": _trend(rt_recent, rt_season),
    }


def qb_signals(player: dict) -> tuple[float, float]:
    """(starting_prob, job_security) for a QB from depth-chart slot + injury.

    Non-QB, or a QB with no depth-chart order, → (0.5, 0.5) neutral.
    """
    if player.get("position") != "QB":
        return NEUTRAL, NEUTRAL
    order = (player.get("metadata") or {}).get("depth_chart_order")
    try:
        order = int(order)
    except (TypeError, ValueError):
        return NEUTRAL, NEUTRAL

    if order <= 1:
        sp, js = 0.90, 0.85
    elif order == 2:
        sp, js = 0.30, 0.35
    else:
        sp, js = 0.08, 0.15

    inj = (player.get("injury_status") or "").strip().lower()
    if inj in _OUT_STATUSES:
        sp, js = sp * 0.2, js * 0.6
    elif inj in _QUESTIONABLE:
        sp, js = sp * 0.8, js * 0.9

    return round(sp, 4), round(js, 4)


def _is_active(player: dict) -> bool:
    """On an NFL roster now: has a team and isn't flagged inactive/retired."""
    if not player.get("nfl_team"):
        return False
    return (player.get("status") or "").strip().lower() not in _INACTIVE_STATUSES


def build_rows(players: list[dict], history_by_player: dict[str, list[dict]]) -> list[dict]:
    """One `player_trends` row per active player (idempotent shape)."""
    now = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    for p in players:
        if not _is_active(p):
            continue
        pid = p["id"]
        trends = compute_trends(history_by_player.get(pid, []))
        sp, js = qb_signals(p)
        rows.append({
            "player_id": pid,
            **trends,
            "starting_prob": sp,
            "job_security": js,
            "updated_at": now,
        })
    return rows


def _history_by_player() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for h in fetch_all("player_stats_history", "player_id,season,week,stats",
                       apply=lambda q: q.not_.is_("week", "null")):
        out.setdefault(h["player_id"], []).append(h)
    return out


def main() -> None:
    players = fetch_all("players", "id,position,nfl_team,status,injury_status,metadata")
    if not players:
        console.print("[yellow]⚠ no players in DB — run player_ingest.py first.[/yellow]")
        return
    history = _history_by_player()
    rows = build_rows(players, history)
    console.print(f"[cyan]computed trends for {len(rows)} active players[/cyan]")
    upsert("player_trends", rows, on_conflict="player_id")


if __name__ == "__main__":
    main()
