"""Aggregate nflverse PBP kicking plays into the per-week buckets score_kicking wants.

The league scores field goals by distance (0-39=3 … 60+=6), so we bin each made FG
by kick_distance and count misses + PATs per (kicker, season, week)."""
from __future__ import annotations


def _bucket(dist: float) -> str:
    if dist < 40:
        return "fg_made_0_39"
    if dist < 50:
        return "fg_made_40_49"
    if dist < 60:
        return "fg_made_50_59"
    return "fg_made_60_plus"


def _blank() -> dict:
    return {"fg_made_0_39": 0, "fg_made_40_49": 0, "fg_made_50_59": 0,
            "fg_made_60_plus": 0, "pat_made": 0, "pat_missed": 0, "fg_missed": 0}


def kicker_week_buckets(pbp_rows) -> dict:
    out: dict[tuple[str, int, int], dict] = {}
    for r in pbp_rows:
        kid = r.get("kicker_player_id")
        if not kid or kid != kid:  # None / NaN
            continue
        key = (str(kid), int(r["season"]), int(r["week"]))
        b = out.setdefault(key, _blank())
        pt = r.get("play_type")
        if pt == "field_goal":
            if r.get("field_goal_result") == "made":
                # NaN/None distance (data gap) → bucket as 0-39 rather than letting NaN
                # comparisons fall through to the 60+ tier and over-credit the kicker.
                dist = r.get("kick_distance")
                dist = float(dist) if dist is not None and dist == dist else 0.0
                b[_bucket(dist)] += 1
            else:
                b["fg_missed"] += 1
        elif pt == "extra_point":
            if r.get("extra_point_result") == "good":
                b["pat_made"] += 1
            else:
                b["pat_missed"] += 1
    return out
