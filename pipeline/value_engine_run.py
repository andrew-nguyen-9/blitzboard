"""
value_engine_run.py — the P1 orchestrator (referenced by etl_daily.yml).

Loads players + history from Supabase, builds the HistoryStore, runs the
EnsembleProjector to produce projections (stored per-source AND as the ensemble),
then runs a ValueEngine (VORP) to produce superflex-aware player_value rows.

Usage:
    python value_engine_run.py --engine vorp
    python value_engine_run.py --engine vorp --season 2025 --no-consensus
"""
from __future__ import annotations

import argparse
import datetime as dt

from common import console, get_supabase, upsert, fetch_all
from models import (
    HistoryStore,
    HeuristicProjector,
    RegressionProjector,
    ConsensusProjector,
    EnsembleProjector,
    KickerProjector,
    DefenseProjector,
    VorpEngine,
    load_league_rules,
)

CURRENT_YEAR = dt.date.today().year


def _load_players(sb) -> list[dict]:
    return fetch_all("players", "id,full_name,position,nfl_team,age")


def _load_history(sb) -> list[dict]:
    # season aggregates only (week is null) — seasonal projections for P1
    return fetch_all("player_stats_history", "player_id,season,stats",
                     apply=lambda q: q.is_("week", "null"))


def build_store(rules, players: list[dict], history: list[dict]) -> HistoryStore:
    pos_by_id = {p["id"]: p.get("position") for p in players}
    age_by_id = {p["id"]: p.get("age") for p in players}
    store = HistoryStore(rules)
    for h in history:
        stats = h.get("stats") or {}
        pid = h["player_id"]
        season = h["season"]
        # approximate age in that season from current age
        cur_age = age_by_id.get(pid)
        age = (cur_age - (CURRENT_YEAR - season)) if cur_age else None
        store.add(
            player_id=pid, season=season, stats=stats,
            games=stats.get("games") or 0, age=age, position=pos_by_id.get(pid),
        )
    return store.finalize()


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute projections + player values.")
    ap.add_argument("--engine", default="vorp", choices=["vorp"])  # monte_carlo = P7
    ap.add_argument("--season", type=int, default=CURRENT_YEAR)
    ap.add_argument("--league", default=None, help="league_id (default: the one seeded league)")
    ap.add_argument("--no-consensus", action="store_true", help="skip FFC ADP fetch")
    args = ap.parse_args()

    sb = get_supabase()
    if sb is None:
        console.print("[red]Supabase not configured — set pipeline/.env first.[/red]")
        return
    rules = load_league_rules(args.league)
    if rules is None:
        return

    players = _load_players(sb)
    history = _load_history(sb)
    console.print(f"[cyan]{len(players)} players · {len(history)} season lines[/cyan]")
    store = build_store(rules, players, history)

    # offensive ensemble (≈ equal weights; tunable)
    subs = [
        (HeuristicProjector(store, rules, args.season), 1.0),
        (RegressionProjector(store, rules, args.season), 1.0),
    ]
    if not args.no_consensus:
        subs.append((ConsensusProjector(store, rules, args.season, teams=rules.league_size), 1.0))
    ensemble = EnsembleProjector(subs)

    # K and D/ST get their own dedicated projectors (not the offense ensemble)
    kicker = KickerProjector(store, rules, args.season, teams=rules.league_size)
    defense = DefenseProjector(store, rules, args.season, teams=rules.league_size)

    def projector_for(pos: str):
        if pos == "K":
            return kicker
        if pos in ("DST", "DEF"):
            return defense
        return ensemble

    # project every player; keep rows for the DB
    proj_rows: list[dict] = []
    projections: dict = {}
    positions: dict[str, str] = {}
    for p in players:
        pos = p.get("position")
        if not pos:
            continue
        if pos in ("DEF", "DST"):  # canonicalize Sleeper's DEF → DST
            pos = "DST"
            p = {**p, "position": "DST"}
        pr = projector_for(pos).project(p)
        if not pr:
            continue
        projections[p["id"]] = pr
        positions[p["id"]] = p["position"]
        proj_rows.append({
            "player_id": pr.player_id, "season": pr.season, "week": None,
            "source": "ensemble", "scoring_profile": "default",
            "mean": pr.mean, "floor": pr.floor, "ceiling": pr.ceiling,
            "stdev": pr.stdev, "by_stat": pr.by_stat,
        })
    console.print(f"[cyan]projected {len(proj_rows)} players[/cyan]")
    # Delete-before-insert: projections key includes NULL `week` for season rows, which
    # can't dedupe (NULL != NULL), so clear this season's ensemble rows first.
    sb.table("projections").delete().eq("source", "ensemble") \
        .eq("scoring_profile", "default").eq("season", args.season).execute()
    upsert("projections", proj_rows, on_conflict="player_id,season,week,source,scoring_profile")

    # VORP (superflex-aware replacement levels via LeagueRules)
    values = VorpEngine().compute(projections, positions, rules)
    value_rows = [{
        "player_id": v.player_id, "league_id": rules.league_id, "engine": v.engine,
        "scoring_profile": "default", "value": round(v.value, 2), "vor": round(v.vor, 2),
        "replacement": round(v.replacement, 2), "boom": v.boom, "bust": v.bust,
        "rank": v.rank,
    } for v in values]
    upsert("player_value", value_rows, on_conflict="player_id,league_id,engine,scoring_profile")
    console.print(f"[green]✓ wrote {len(value_rows)} {args.engine} values[/green]")
    # show the top of the board as a sanity check
    for v in values[:12]:
        console.print(f"  {v.rank:>2}. {positions.get(v.player_id):<3} VOR {v.vor:+.1f}")


if __name__ == "__main__":
    main()
