"""
scoring.py — convert a raw stat line into fantasy points under a LeagueRules
scoring config (the `scoring` JSONB from db/seed_league_smores.sql).

Offensive skill positions (QB/RB/WR/TE) are fully supported here. K and D/ST use
different stat sources and get their own treatment (their projections are computed
separately — see ConsensusProjector / P1-later), so this returns 0 for them.

Stat keys match nflverse / nfl_data_py columns (see history_ingest.STAT_COLS).
Tolerant of missing keys (treated as 0), so partial stat lines score cleanly.
"""
from __future__ import annotations


def _g(stats: dict, key: str) -> float:
    v = stats.get(key)
    return float(v) if v is not None else 0.0


def score_stats(stats: dict, scoring: dict) -> float:
    """Fantasy points for one stat line under `scoring`.

    >>> s = {"passing": {"pt_per_yd":0.04,"td":4,"int":-2},
    ...      "rushing": {"pt_per_yd":0.1,"td":6},
    ...      "receiving": {"pt_per_yd":0.1,"ppr":0.5,"td":6},
    ...      "misc": {"fumble_lost":-2}}
    >>> line = {"passing_yards":300,"passing_tds":3,"interceptions":1}
    >>> round(score_stats(line, s), 2)   # 12 + 12 - 2
    22.0
    """
    p = scoring.get("passing", {})
    r = scoring.get("rushing", {})
    rec = scoring.get("receiving", {})
    misc = scoring.get("misc", {})

    pts = 0.0
    # passing
    pts += _g(stats, "passing_yards") * p.get("pt_per_yd", 0.04)
    pts += _g(stats, "passing_tds") * p.get("td", 4)
    pts += _g(stats, "interceptions") * p.get("int", -2)
    pts += _g(stats, "passing_2pt_conversions") * p.get("two_pt", 2)
    # rushing
    pts += _g(stats, "rushing_yards") * r.get("pt_per_yd", 0.1)
    pts += _g(stats, "rushing_tds") * r.get("td", 6)
    pts += _g(stats, "rushing_2pt_conversions") * r.get("two_pt", 2)
    # receiving
    pts += _g(stats, "receiving_yards") * rec.get("pt_per_yd", 0.1)
    pts += _g(stats, "receptions") * rec.get("ppr", 0.5)
    pts += _g(stats, "receiving_tds") * rec.get("td", 6)
    pts += _g(stats, "receiving_2pt_conversions") * rec.get("two_pt", 2)
    # misc
    pts += _g(stats, "fumbles_lost") * misc.get("fumble_lost", -2)
    return round(pts, 2)


def score_kicking(stats: dict, scoring: dict) -> float:
    """Kicker points under DISTANCE-BASED scoring (Smores: 0-39=3 … 60+=6).

    Expects per-bucket FG-made counts: fg_made_0_39, fg_made_40_49,
    fg_made_50_59, fg_made_60_plus; plus pat_made, pat_missed, fg_missed.
    """
    k = scoring.get("kicking", {})
    pts = 0.0
    pts += _g(stats, "fg_made_0_39") * k.get("fg_0_39", 3)
    pts += _g(stats, "fg_made_40_49") * k.get("fg_40_49", 4)
    pts += _g(stats, "fg_made_50_59") * k.get("fg_50_59", 5)
    pts += _g(stats, "fg_made_60_plus") * k.get("fg_60_plus", 6)
    pts += _g(stats, "pat_made") * k.get("pat", 1)
    pts += _g(stats, "pat_missed") * k.get("pat_miss", -2)
    pts += _g(stats, "fg_missed") * k.get("fg_miss", -1)
    return round(pts, 2)


def _tier(value: float, tiers: dict, bounds: list[tuple[float, float, str]]) -> float:
    """Map a continuous value to its tier's points using (lo, hi, key) bounds."""
    for lo, hi, key in bounds:
        if lo <= value <= hi:
            return float(tiers.get(key, 0))
    return 0.0


# (lo, hi, scoring-key) for D/ST points-allowed and yards-allowed tiers (Smores rules).
_PA_BOUNDS = [(0, 0, "0"), (1, 6, "1_6"), (7, 13, "7_13"), (14, 17, "14_17"),
              (18, 27, "18_27"), (28, 34, "28_34"), (35, 45, "35_45"), (46, 999, "46_plus")]
_YA_BOUNDS = [(0, 99, "lt_100"), (100, 199, "100_199"), (200, 299, "200_299"),
              (300, 349, "300_349"), (350, 399, "350_399"), (400, 449, "400_449"),
              (450, 499, "450_499"), (500, 549, "500_549"), (550, 99999, "550_plus")]


def score_defense(stats: dict, scoring: dict) -> float:
    """Team D/ST points: events + points-allowed tier + yards-allowed tier.

    Expects: sacks, interceptions, fumble_recoveries, safeties, blocked_kicks,
    def_tds (any TD), two_pt_returns, one_pt_safeties, points_allowed, yards_allowed.
    The tier stats are typically per-game; sum across games for a season line.
    """
    d = scoring.get("dst", {})
    pts = 0.0
    pts += _g(stats, "sacks") * d.get("sack", 1)
    pts += _g(stats, "interceptions") * d.get("int", 2)
    pts += _g(stats, "fumble_recoveries") * d.get("fumble_rec", 2)
    pts += _g(stats, "safeties") * d.get("safety", 2)
    pts += _g(stats, "blocked_kicks") * d.get("blocked_kick", 2)
    pts += _g(stats, "def_tds") * d.get("td_any", 6)
    pts += _g(stats, "two_pt_returns") * d.get("two_pt_return", 2)
    pts += _g(stats, "one_pt_safeties") * d.get("one_pt_safety", 1)
    # tiers are scored per game then summed; if a season total is provided as a
    # list under _pa_games / _ya_games, score each game, else score the single value.
    pa = scoring.get("dst", {}).get("points_allowed", {})
    ya = scoring.get("dst", {}).get("yards_allowed", {})
    for g in stats.get("_pa_games", [stats.get("points_allowed")] if "points_allowed" in stats else []):
        if g is not None:
            pts += _tier(float(g), pa, _PA_BOUNDS)
    for g in stats.get("_ya_games", [stats.get("yards_allowed")] if "yards_allowed" in stats else []):
        if g is not None:
            pts += _tier(float(g), ya, _YA_BOUNDS)
    return round(pts, 2)


# Default per-position points when a player has no usable history (replacement-ish
# floor so the ensemble still ranks them sanely). Tuned to half-PPR.
POSITION_FLOOR = {"QB": 180.0, "RB": 90.0, "WR": 90.0, "TE": 60.0, "K": 110.0, "DST": 90.0}
