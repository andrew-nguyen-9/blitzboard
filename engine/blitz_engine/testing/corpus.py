"""E7b deterministic test corpus — the one documented loader for `fixtures/`.

Downstream units import THIS module (never hand-parse the fixture files)::

    from blitz_engine.testing import corpus
    corpus.season(2024)               # frozen season slice (players + weekly points)
    corpus.golden_draft(row_id)       # checked-in autodraft for a smoke() matrix row
    corpus.player_pool(2024, row_id)  # that row's draft pool, scored in its scoring rules

Everything is JSON, checked in, and byte-stable: the TypeScript side reads the SAME files
through `frontend/scripts/gen-golden-drafts.mjs`.

Fixture design (see `build_season` below):
  * `points` is PRE-COMPUTED for every (scoring, te_premium) pair in the e7a matrix, so no
    scoring logic exists on either side of the language boundary — only a dict lookup. That
    is the whole reason the corpus can be byte-identical from Python and from Node.
  * dropped on purpose (absent from the e9 store): vendor preseason projections, ADP, injury
    status, depth charts, age/experience. `preseason` is a DERIVED stand-in — the player's
    prior-season per-game production scaled to this season's week count.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3] / "fixtures"
SEASONS_DIR = _ROOT / "seasons"
GOLDEN_DIR = _ROOT / "golden_drafts"

# The frozen slice seasons. 2018 / 2021 / 2024 span the e9 store's 2014-2025 ingest at its
# well-covered end: all three carry NGS (2016+) and PFR (2018+) support, 2018 is a 16-game
# season while 2021/2024 are 17-game ones (so week-count assumptions get exercised), and they
# sit 3 years apart, straddling the 2021 schedule expansion. 2014-2017 are deliberately out:
# no PFR coverage and (pre-2016) no NGS position labels, so TE would collapse into WR.
SEASONS: tuple[int, ...] = (2018, 2021, 2024)

# The season the golden drafts are generated against, and the seed baked into them.
# Both are hard-coded identically in frontend/scripts/gen-golden-drafts.mjs.
GOLDEN_SEASON = 2024
GOLDEN_SEED = 20260825

SCORINGS: tuple[str, ...] = ("std", "half", "ppr")
TE_PREMIUMS: tuple[float, ...] = (0.0, 0.5)


def scoring_key(scoring: str, te_premium: float) -> str:
    """The `points`/`preseason` dict key for a (scoring, te_premium) pair — e.g. `"half:0.5"`."""
    return f"{scoring}:{float(te_premium):g}"


Slice = dict[str, Any]


@lru_cache(maxsize=None)
def _load(path: str) -> Slice:
    return json.loads(Path(path).read_text())


def _copy(doc: Slice) -> Slice:
    return json.loads(json.dumps(doc))


def season(year: int) -> Slice:
    """One frozen season slice: `{version, season, weeks, source, note, players: [...]}`.

    Each player carries `player_id, name, position, nfl_team, bye_week, adp,
    points{key: [w1..wN]}, preseason{key: {projection, boom, bust}}`.
    Returns a fresh copy, so callers cannot mutate the cache.
    """
    if year not in SEASONS:
        raise KeyError(f"no season slice for {year}; corpus has {SEASONS}")
    return _copy(_load(str(SEASONS_DIR / f"{year}.json")))


def golden_draft(row_id: str) -> Slice:
    """The checked-in autodraft for an e7a `smoke()` row.

    `{row_id, season, seed, num_teams, rounds, starting_slots, bench_slots, picks, rosters}`
    where `picks` is the ordered pick log and `rosters[t]` team `t+1`'s player ids.
    """
    path = GOLDEN_DIR / f"{row_id}.json"
    if not path.exists():
        raise KeyError(f"no golden draft for row {row_id!r} ({path})")
    return _copy(_load(str(path)))


def player_pool(year: int, row_id: str) -> list[dict[str, Any]]:
    """The draft pool for a matrix row: that season's players scored in the ROW's rules.

    Flattens the per-scoring dicts to the row's `(scoring, te_premium)` pair, adding
    `weekly_points`, `actual_points` and `projection`/`boom`/`bust`. Deterministic order:
    projection desc, then `player_id`. This is the exact pool `gen-golden-drafts.mjs` drafts
    from, so a Python assertion about a golden draft can name real players.
    """
    from blitz_engine.testing import matrix  # local: keeps `corpus` importable standalone

    row = matrix.by_id(row_id)
    key = scoring_key(row["scoring"], row["te_premium"])
    out = []
    for p in season(year)["players"]:
        weekly = p["points"][key]
        pre = p["preseason"][key]
        out.append(
            {
                **{k: p[k] for k in ("player_id", "name", "position", "nfl_team", "bye_week", "adp")},
                "weekly_points": weekly,
                "actual_points": round(sum(w for w in weekly if w is not None), 2),
                "projection": pre["projection"],
                "boom": pre["boom"],
                "bust": pre["bust"],
            }
        )
    out.sort(key=lambda p: (-p["projection"], p["player_id"]))
    return out


# ── builder ────────────────────────────────────────────────────────────────────────────
# Regenerates `fixtures/seasons/*.json` from the e9 ParquetStore:
#   pipeline/.venv/bin/python -m blitz_engine.testing.corpus [--data-root ~/.blitz_engine]
# Never run at import time (mirrors e7a's generate_matrix.py); duckdb is imported lazily.

TOP_SKILL = 260  # skill players kept per season (a 14-team/8-bench league drafts <= 252)

_STAT_SQL = """
WITH plays AS (
    SELECT season, week, posteam AS team, defteam,
           passer_player_id, passer_player_name, rusher_player_id, rusher_player_name,
           receiver_player_id, receiver_player_name,
           COALESCE(passing_yards,0) AS pass_yds, COALESCE(rushing_yards,0) AS rush_yds,
           COALESCE(receiving_yards,0) AS rec_yds, COALESCE(pass_touchdown,0) AS pass_td,
           COALESCE(rush_touchdown,0) AS rush_td, COALESCE(complete_pass,0) AS cmp,
           COALESCE(interception,0) AS intc, COALESCE(fumble_lost,0) AS fum,
           COALESCE(two_point_attempt,0) AS two_att, two_point_conv_result
    FROM read_parquet('{pbp}')
    WHERE season = {season} AND season_type = 'REG' AND posteam IS NOT NULL
),
pass AS (
    SELECT passer_player_id AS pid, any_value(passer_player_name) AS nm, week,
           any_value(team) AS team,
           SUM(pass_yds) AS pass_yds, SUM(pass_td) AS pass_td, SUM(intc) AS ints,
           0 AS rush_yds, 0 AS rush_td, 0 AS rec, 0 AS rec_yds, 0 AS rec_td,
           SUM(CASE WHEN two_att=1 AND two_point_conv_result='success' THEN 1 ELSE 0 END) AS two_pt
    FROM plays WHERE passer_player_id IS NOT NULL GROUP BY pid, week
),
rush AS (
    SELECT rusher_player_id, any_value(rusher_player_name), week, any_value(team),
           0, 0, 0, SUM(rush_yds), SUM(rush_td), 0, 0, 0,
           SUM(CASE WHEN two_att=1 AND two_point_conv_result='success' THEN 1 ELSE 0 END)
    FROM plays WHERE rusher_player_id IS NOT NULL GROUP BY 1, week
),
rec AS (
    SELECT receiver_player_id, any_value(receiver_player_name), week, any_value(team),
           0, 0, 0, 0, 0, SUM(cmp), SUM(CASE WHEN cmp=1 THEN rec_yds ELSE 0 END),
           SUM(CASE WHEN cmp=1 THEN pass_td ELSE 0 END),
           SUM(CASE WHEN two_att=1 AND two_point_conv_result='success' THEN 1 ELSE 0 END)
    FROM plays WHERE receiver_player_id IS NOT NULL GROUP BY 1, week
),
fum AS (
    SELECT pid, week, SUM(f) AS fum_lost FROM (
        SELECT rusher_player_id AS pid, week, SUM(fum) AS f FROM plays
        WHERE rusher_player_id IS NOT NULL GROUP BY 1, 2
        UNION ALL
        SELECT receiver_player_id, week, SUM(CASE WHEN cmp=1 THEN fum ELSE 0 END) FROM plays
        WHERE receiver_player_id IS NOT NULL GROUP BY 1, 2
    ) GROUP BY pid, week
),
skill AS (
    SELECT pid, nm, week, team, SUM(pass_yds) pass_yds, SUM(pass_td) pass_td, SUM(ints) ints,
           SUM(rush_yds) rush_yds, SUM(rush_td) rush_td, SUM(rec) rec, SUM(rec_yds) rec_yds,
           SUM(rec_td) rec_td, SUM(two_pt) two_pt
    FROM (SELECT * FROM pass UNION ALL SELECT * FROM rush UNION ALL SELECT * FROM rec)
    GROUP BY pid, nm, week, team
)
SELECT s.pid AS player_id, any_value(s.nm) AS raw_name, s.week, any_value(s.team) AS team,
       SUM(s.pass_yds) AS pass_yds, SUM(s.pass_td) AS pass_td, SUM(s.ints) AS ints,
       SUM(s.rush_yds) AS rush_yds, SUM(s.rush_td) AS rush_td, SUM(s.rec) AS rec,
       SUM(s.rec_yds) AS rec_yds, SUM(s.rec_td) AS rec_td, SUM(s.two_pt) AS two_pt,
       COALESCE(any_value(f.fum_lost), 0) AS fum_lost
FROM skill s LEFT JOIN fum f ON f.pid = s.pid AND f.week = s.week
GROUP BY s.pid, s.week
"""

_K_SQL = """
SELECT kicker_player_id AS player_id, any_value(kicker_player_name) AS raw_name, week,
       any_value(posteam) AS team,
       SUM(CASE WHEN field_goal_result='made' AND kick_distance < 40 THEN 3
                WHEN field_goal_result='made' AND kick_distance < 50 THEN 4
                WHEN field_goal_result='made' THEN 5
                WHEN field_goal_result IN ('missed','blocked') THEN -1 ELSE 0 END)
     + SUM(CASE WHEN extra_point_result='good' THEN 1
                WHEN extra_point_result IN ('failed','blocked') THEN -1 ELSE 0 END) AS pts
FROM read_parquet('{pbp}')
WHERE season = {season} AND season_type = 'REG' AND kicker_player_id IS NOT NULL
  AND posteam IS NOT NULL
GROUP BY player_id, week
"""

_DST_SQL = """
WITH g AS (
    SELECT defteam AS team, week,
           MAX(COALESCE(posteam_score_post,0)) AS pa,
           SUM(COALESCE(sack,0)) AS sacks, SUM(COALESCE(interception,0)) AS ints,
           SUM(CASE WHEN fumble_lost=1 THEN 1 ELSE 0 END) AS fr,
           SUM(COALESCE(safety,0)) AS safeties,
           SUM(CASE WHEN COALESCE(return_touchdown,0)=1 THEN 1 ELSE 0 END) AS def_td
    FROM read_parquet('{pbp}')
    WHERE season = {season} AND season_type = 'REG' AND defteam IS NOT NULL
    GROUP BY team, week
)
SELECT 'DST-' || team AS player_id, team AS raw_name, week, team,
       sacks + 2*ints + 2*fr + 2*safeties + 6*def_td
     + CASE WHEN pa = 0 THEN 10 WHEN pa < 7 THEN 7 WHEN pa < 14 THEN 4
            WHEN pa < 21 THEN 1 WHEN pa < 28 THEN 0 WHEN pa < 35 THEN -1 ELSE -4 END AS pts
FROM g
"""

# pbp carries no roster position (TE would collapse into WR), so positions/display names come
# from the NGS tables' player_gsis_id -> player_position mapping.
_POS_SQL = """
SELECT player_gsis_id AS player_id, arg_max(player_position, n) AS position,
       arg_max(player_display_name, n) AS name
FROM (
    SELECT player_gsis_id, player_position, player_display_name, COUNT(*) AS n
    FROM read_parquet('{ngs}') WHERE player_gsis_id IS NOT NULL
    GROUP BY 1, 2, 3
) GROUP BY player_id
"""

_STAT_COLS = ("pass_yds", "pass_td", "ints", "rush_yds", "rush_td", "rec", "rec_yds",
              "rec_td", "two_pt", "fum_lost")


def _score(r: dict[str, float], pos: str, scoring: str, te_premium: float) -> float:
    """Fantasy points for one skill player-week. Standard rules; PPR/TE-premium as configured."""
    ppr = {"std": 0.0, "half": 0.5, "ppr": 1.0}[scoring] + (te_premium if pos == "TE" else 0.0)
    return (
        r["pass_yds"] / 25.0 + 4 * r["pass_td"] - 2 * r["ints"]
        + r["rush_yds"] / 10.0 + 6 * r["rush_td"]
        + r["rec_yds"] / 10.0 + 6 * r["rec_td"] + ppr * r["rec"]
        - 2 * r["fum_lost"] + 2 * r["two_pt"]
    )


def build_season(year: int, data_root: Path | str | None = None) -> Path:  # pragma: no cover - IO
    """Write `fixtures/seasons/<year>.json` from the e9 store. Returns the path."""
    import duckdb
    import numpy as np

    from blitz_engine.store import ParquetStore

    store = ParquetStore(Path(data_root or "~/.blitz_engine").expanduser())
    pbp = str(store.path("pbp")).replace("'", "''")
    con = duckdb.connect()

    def q(sql: str, season_year: int):
        return con.execute(sql.format(pbp=pbp, season=season_year)).df()

    posmap: dict[str, tuple[str, str]] = {}
    for tbl in ("ngs_passing", "ngs_rushing", "ngs_receiving"):
        d = con.execute(_POS_SQL.format(ngs=str(store.path(tbl)).replace("'", "''"))).df()
        for _, r in d.iterrows():
            posmap.setdefault(str(r["player_id"]), (str(r["position"]), str(r["name"])))

    def collect(y: int) -> dict[str, dict[str, Any]]:
        """player_id -> {name, team, w: {week: statrow|float}, pos?, flat?} for one season."""
        out: dict[str, dict[str, Any]] = {}
        for _, r in q(_STAT_SQL, y).iterrows():
            pid = str(r["player_id"])
            e = out.setdefault(pid, {"name": str(r["raw_name"]), "team": str(r["team"]), "w": {}})
            e["w"][int(r["week"])] = {k: float(r[k]) for k in _STAT_COLS}
            e["team"] = str(r["team"])
        # K/DST weeks are already points, not stat lines (`flat`). A kicker with a stray
        # fake-FG carry is overwritten here on purpose — he is a K in every league.
        for sql, kind in ((_K_SQL, "K"), (_DST_SQL, "DST")):
            for _, r in q(sql, y).iterrows():
                pid = str(r["player_id"])
                e = out.setdefault(pid, {})
                if not e.get("flat"):
                    e.clear()
                    e.update({"name": str(r["raw_name"]), "team": str(r["team"]), "w": {},
                              "flat": True, "pos": kind})
                e["team"] = str(r["team"])
                e["w"][int(r["week"])] = float(r["pts"])
        return out

    cur, prev = collect(year), collect(year - 1)
    weeks = max(int(w) for e in cur.values() for w in e["w"])

    played = con.execute(
        "SELECT DISTINCT team, week FROM ("
        f"SELECT posteam AS team, week FROM read_parquet('{pbp}') WHERE season={year} "
        "AND season_type='REG' AND posteam IS NOT NULL UNION "
        f"SELECT defteam, week FROM read_parquet('{pbp}') WHERE season={year} "
        "AND season_type='REG' AND defteam IS NOT NULL)"
    ).df()
    byes: dict[str, int | None] = {}
    for team, grp in played.groupby("team"):
        missing = sorted(set(range(1, weeks + 1)) - {int(w) for w in grp["week"]})
        byes[str(team)] = missing[0] if missing else None

    def week_points(entry, wk: int, pos: str, scoring: str, tep: float) -> float | None:
        row = entry["w"].get(wk)
        if row is None:
            return None
        return round(row if entry.get("flat") else _score(row, pos, scoring, tep), 2)

    def position_of(pid: str, entry) -> str | None:
        return entry.get("pos") or posmap.get(pid, (None, None))[0]

    ranked: list[tuple[float, str]] = []
    for pid, e in cur.items():
        p = position_of(pid, e)
        if p in ("QB", "RB", "WR", "TE"):
            ranked.append((-sum(_score(r, p, "half", 0.0) for r in e["w"].values()), pid))
    ranked.sort()
    keep = {pid for _, pid in ranked[:TOP_SKILL]}
    keep |= {pid for pid, e in cur.items() if e.get("pos") in ("K", "DST")}

    players: list[dict[str, Any]] = []
    for pid in sorted(keep):
        e = cur[pid]
        pos = position_of(pid, e)
        if pos is None:
            continue
        prior = prev.get(pid)
        points: dict[str, list[float | None]] = {}
        preseason: dict[str, dict[str, float]] = {}
        for sc in SCORINGS:
            for tep in TE_PREMIUMS:
                key = scoring_key(sc, tep)
                points[key] = [week_points(e, w, pos, sc, tep) for w in range(1, weeks + 1)]
                pw = [week_points(prior, w, pos, sc, tep) for w in sorted(prior["w"])] if prior else []
                pw = [x for x in pw if x is not None]
                if pw:
                    proj = float(np.mean(pw)) * weeks
                    boom = float(np.percentile(pw, 85)) * weeks
                    bust = float(np.percentile(pw, 15)) * weeks
                else:  # no prior season (rookie / no snaps) — a replacement-level body
                    proj = boom = bust = 0.0
                preseason[key] = {"projection": round(proj, 2), "boom": round(boom, 2),
                                  "bust": round(bust, 2)}
        team = e["team"]
        players.append({
            "player_id": pid,
            "name": f"{team} D/ST" if pos == "DST" else (posmap.get(pid, (None, ""))[1] or e["name"]),
            "position": pos,
            "nfl_team": team,
            "bye_week": byes.get(team),
            "adp": None,
            "points": points,
            "preseason": preseason,
        })

    players.sort(key=lambda x: x["player_id"])
    doc = {
        "version": 1,
        "season": year,
        "weeks": weeks,
        "source": "e9 ParquetStore (pbp REG + ngs_* positions)",
        "note": (
            "points[<scoring>:<te_premium>][w-1] = week-w fantasy points (null = did not "
            "appear). preseason[...] is DERIVED from the prior season, not a vendor "
            "projection; adp is always null (neither is in the store)."
        ),
        "players": players,
    }
    out = SEASONS_DIR / f"{year}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n")
    return out


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="rebuild fixtures/seasons/*.json from the e9 store")
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--season", type=int, action="append")
    args = ap.parse_args()
    for y in args.season or SEASONS:
        print(build_season(y, args.data_root))
