"""Aggregate nflverse PBP into per-team per-week D/ST lines score_defense wants.

For each play the defending team is `defteam`. We sum sacks, INTs, defensive fumble
recoveries, safeties and defensive/return TDs, total yards allowed (yards_gained vs
that defense), and read points allowed = the offense's final game score. Rare events
(blocked kicks, 2-pt returns, 1-pt safeties) aren't in base PBP columns → left 0 and
documented; revisit in v2.4.3 only if ablations prove the harness is sensitive to them."""
from __future__ import annotations


def _num(v) -> float:
    try:
        return 0.0 if v is None or v != v else float(v)
    except (TypeError, ValueError):
        return 0.0


def _opp_score(r) -> float:
    """Points the defense allowed = the offense (posteam) team's final score."""
    if r.get("posteam") == r.get("home_team"):
        return _num(r.get("home_score"))
    return _num(r.get("away_score"))


def team_week_dst(pbp_rows) -> dict:
    out: dict[tuple[str, int, int], dict] = {}
    for r in pbp_rows:
        dt = r.get("defteam")
        if not dt or dt != dt:
            continue
        key = (str(dt), int(r["season"]), int(r["week"]))
        d = out.setdefault(key, {"sacks": 0.0, "interceptions": 0.0, "fumble_recoveries": 0.0,
                                 "safeties": 0.0, "def_tds": 0.0, "yards_allowed": 0.0,
                                 "points_allowed": None})
        d["sacks"] += _num(r.get("sack"))
        d["interceptions"] += _num(r.get("interception"))
        if r.get("fumble_recovery_1_team") == dt:
            d["fumble_recoveries"] += 1.0
        d["safeties"] += _num(r.get("safety"))
        if _num(r.get("return_touchdown")) and r.get("posteam") != dt:
            d["def_tds"] += 1.0
        d["yards_allowed"] += _num(r.get("yards_gained"))
        d["points_allowed"] = _opp_score(r)  # constant across the game's plays
    return out
