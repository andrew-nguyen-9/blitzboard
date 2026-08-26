"""`blitz-engine` CLI — the four verbs of the local quant engine.

    blitz-engine fit      # fit the Bayesian projection model (E1) -> quantiles + draws
    blitz-engine sim      # correlated Monte-Carlo season/league simulation (E3)
    blitz-engine draft    # value / equity / MCTS draft strategy (E4)
    blitz-engine publish  # write a versioned snapshot + compact export

Every verb is wired to the real modules and hands off through **named store tables** under
`EngineConfig.data_root`, so the verbs compose in order without a scheduler:

    player_weeks (or pbp)  --fit-->  projection_quantiles / projection_shares / players
    projection_quantiles   --sim-->  mc_probs / corr_matrix (+ league_standings)
    projection_quantiles   --draft-> draft_board / strategy_tree.json
    all of the above       --publish-> <data_root>/snapshots/<version>/ (+ /compact)

Every verb honours `--seed` (the run is recorded in the `ModelRegistry` under a version
derived from params+data+sha+seed), streams per `EngineConfig` (`chunk_size`, `mc_batch`,
float32), prints ONE machine-readable JSON summary line, and returns a nonzero exit code on
failure. `ponytail:` argparse only — no CLI framework; heavy imports stay inside the handler
so `--help` (and the store-less paths) never pay for jax/torch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from blitz_engine.config import EngineConfig, load_config
from blitz_engine.registry import ModelRegistry
from blitz_engine.store import ParquetStore

if TYPE_CHECKING:
    import pandas as pd

_VERBS = ("fit", "sim", "draft", "publish")

# Store tables the verbs hand off through (see module docstring).
PLAYER_WEEKS = "player_weeks"
PLAYERS = "players"
QUANTILES = "projection_quantiles"
SHARES = "projection_shares"
MC_PROBS = "mc_probs"
CORR = "corr_matrix"
DRAFT_BOARD = "draft_board"
STRATEGY_JSON = "strategy_tree.json"
POLICY_JSON = "policy.json"

_PW_COLS = ("player_id", "position", "team", "week", "team_plays", "opportunities", "yards", "tds")


def _wire(args: argparse.Namespace) -> tuple[EngineConfig, ParquetStore, ModelRegistry]:
    """Resolve config + open the store + registry the same way for every verb."""
    cfg = load_config(
        **{k: v for k, v in {
            # `load_config` only coerces env strings — an explicit override must arrive typed.
            "data_root": Path(args.data_root).expanduser() if args.data_root else None,
            "seed": args.seed,
            "cloud_burst": args.cloud_burst,
        }.items() if v is not None}
    )
    store = ParquetStore.open(cfg.data_root, cfg)
    registry = ModelRegistry(cfg.data_root)
    return cfg, store, registry


# -- shared helpers ------------------------------------------------------------
def _emit(verb: str, **fields: object) -> None:
    """The one machine-readable summary line every verb prints."""
    print(json.dumps({"verb": verb, "ok": True, **fields}, default=str), flush=True)


def _data_hash(store: ParquetStore, tables: Sequence[str]) -> str:
    """Cheap content id for the run's inputs: name + byte size of each input table."""
    h = hashlib.sha256()
    for name in tables:
        path = store.path(name)
        h.update(name.encode())
        h.update(str(path.stat().st_size if path.exists() else 0).encode())
    return h.hexdigest()[:16]


def _read_table(store: ParquetStore, name: str, *, required: bool = True) -> pd.DataFrame | None:
    """Read a store table as a DataFrame (index preserved), or None/raise when absent."""
    import pandas as pd

    path = store.path(name)
    if not path.exists():
        if required:
            raise FileNotFoundError(
                f"store table {name!r} missing under {store.root} — run the previous verb first"
            )
        return None
    return pd.read_parquet(path)


def _player_weeks(
    store: ParquetStore, table: str, seasons: Sequence[int] | None, max_players: int | None
) -> pd.DataFrame:
    """The tidy player-week frame `ModelData.from_frame` consumes.

    Prefers the curated `player_weeks` table; falls back to deriving one from raw `pbp`.
    `# ponytail:` `ModelData.from_store` is advertised in the projection docstrings but does
    not exist, so the store→ModelData adaptation lives here (see .done.md gotchas).
    """
    df = _read_table(store, table, required=False)
    if df is None:
        df = _player_weeks_from_pbp(store, seasons)
    missing = [c for c in _PW_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{table!r} is not a player-week table — missing columns {missing}")
    if seasons and "season" in df.columns:
        df = df[df["season"].isin(list(seasons))]
    if max_players:
        top = (
            df.groupby("player_id")["opportunities"].sum().nlargest(max_players).index
        )
        df = df[df["player_id"].isin(top)]
    if df.empty:
        raise ValueError("no player-week rows after filtering — nothing to fit")
    # The E1 likelihoods are positive-support (Gamma yards / Poisson TDs); real pbp yields
    # negative player-weeks (sacks, lost yardage), so clip at zero here rather than in the model.
    counts = ["team_plays", "opportunities", "yards", "tds"]
    df[counts] = df[counts].clip(lower=0.0)
    return df.reset_index(drop=True)


def _player_weeks_from_pbp(store: ParquetStore, seasons: Sequence[int] | None) -> pd.DataFrame:
    """Aggregate raw play-by-play into player-weeks in ONE DuckDB query (never in RAM).

    Opportunities = pass attempts / carries / targets; position is the player's dominant
    role that week (QB/RB/WR only — pbp carries no roster position, so TE is folded into
    WR). A curated `player_weeks` table always wins over this fallback.
    """
    pbp = store.path("pbp")
    if not pbp.exists():
        raise FileNotFoundError(f"neither {PLAYER_WEEKS!r} nor 'pbp' exists under {store.root}")
    where = f"AND season IN ({', '.join(str(int(s)) for s in seasons)})" if seasons else ""
    sql = f"""
    WITH plays AS (
        SELECT season, week, posteam AS team,
               passer_player_id, rusher_player_id, receiver_player_id,
               COALESCE(passing_yards, 0) AS pass_yds,
               COALESCE(rushing_yards, 0) AS rush_yds,
               COALESCE(receiving_yards, 0) AS rec_yds,
               COALESCE(pass_touchdown, 0) AS pass_td,
               COALESCE(rush_touchdown, 0) AS rush_td
        FROM read_parquet('{str(pbp).replace("'", "''")}')
        WHERE posteam IS NOT NULL {where}
    ),
    tp AS (
        SELECT season, week, team, COUNT(*)::DOUBLE AS team_plays FROM plays GROUP BY 1, 2, 3
    ),
    roles AS (
        SELECT season, week, team, passer_player_id AS player_id, 'QB' AS position,
               COUNT(*)::DOUBLE AS opp, SUM(pass_yds)::DOUBLE AS yds, SUM(pass_td)::DOUBLE AS td
        FROM plays WHERE passer_player_id IS NOT NULL GROUP BY 1, 2, 3, 4
        UNION ALL
        SELECT season, week, team, rusher_player_id, 'RB',
               COUNT(*)::DOUBLE, SUM(rush_yds)::DOUBLE, SUM(rush_td)::DOUBLE
        FROM plays WHERE rusher_player_id IS NOT NULL GROUP BY 1, 2, 3, 4
        UNION ALL
        SELECT season, week, team, receiver_player_id, 'WR',
               COUNT(*)::DOUBLE, SUM(rec_yds)::DOUBLE, SUM(pass_td)::DOUBLE
        FROM plays WHERE receiver_player_id IS NOT NULL GROUP BY 1, 2, 3, 4
    )
    SELECT r.player_id, arg_max(r.position, r.opp) AS position, any_value(r.team) AS team,
           r.season AS season, r.week AS week,
           any_value(tp.team_plays) AS team_plays,
           SUM(r.opp) AS opportunities, SUM(r.yds) AS yards, SUM(r.td) AS tds
    FROM roles r JOIN tp USING (season, week, team)
    GROUP BY r.player_id, r.season, r.week
    """
    return store.query(sql).df()


def _players_frame(pw: pd.DataFrame) -> pd.DataFrame:
    """The correlation universe (`player_id`, `position`, `team`) — one row per player."""
    last = pw.sort_values(["week"]).groupby("player_id", as_index=False).last()
    return last[["player_id", "position", "team"]].reset_index(drop=True)


def _season_marginals(quantiles: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-player-WEEK quantiles into the per-player marginals the sim consumes.

    Weekly means add; weekly sds add in quadrature (weeks treated as independent — the
    within-player correlation the sim cares about is *across players*, not across weeks).
    """
    import numpy as np

    g = quantiles.groupby("player_id")
    out = g.agg(mean=("mean", "sum"), stdev=("stdev", lambda s: float(np.sqrt((s**2).sum()))))
    return out.reset_index()


def _value_board(store: ParquetStore) -> tuple[dict[str, list[tuple[str, float]]], dict[str, str]]:
    """`{position: [(player_id, value), …] desc}` + `{player_id: position}` from the store."""
    marg = _season_marginals(_read_table(store, QUANTILES))
    players = _read_table(store, PLAYERS)
    df = players.merge(marg, on="player_id", how="inner").sort_values("mean", ascending=False)
    by_pos: dict[str, list[tuple[str, float]]] = {}
    for pid, pos, val in zip(df["player_id"], df["position"], df["mean"], strict=True):
        by_pos.setdefault(str(pos).upper(), []).append((str(pid), float(val)))
    return by_pos, {str(p): str(q).upper() for p, q in zip(df["player_id"], df["position"],
                                                          strict=True)}


def _feasible_starters(available: Sequence[str], template: Sequence[str]) -> tuple[str, ...]:
    """Drop template slots no available position can fill (a pbp-only board has no K/DST)."""
    from blitz_engine.value.mcts import slot_positions

    have = {p.upper() for p in available}
    return tuple(s for s in template if slot_positions(s) & have)


def _round_robin(ids: Sequence[str], weeks: int) -> list[list[tuple[str, str]]]:
    """Circle-method schedule: `weeks` weeks of (home, away) matchups over an even field."""
    rot = list(ids)
    schedule = []
    for _ in range(weeks):
        schedule.append([(rot[i], rot[-1 - i]) for i in range(len(rot) // 2)])
        rot = [rot[0], rot[-1], *rot[1:-1]]
    return schedule


# -- verbs ---------------------------------------------------------------------
def _cmd_fit(args: argparse.Namespace) -> int:
    """Fit the hierarchical projection model and persist quantiles + posterior draws."""
    from blitz_engine.projection import HierarchicalProjector, ModelData

    cfg, store, registry = _wire(args)
    pw = _player_weeks(store, args.table, args.seasons, args.max_players)
    data = ModelData.from_frame(pw)

    projector = HierarchicalProjector(cfg)
    report = projector.fit(
        data,
        num_warmup=args.warmup,
        num_samples=args.samples,
        num_chains=args.chains,
        enforce_gate=not args.no_gate,
    )
    projection = projector.predict(store=store)
    store.write_parquet(QUANTILES, projection.quantiles)
    store.write_parquet(SHARES, projection.shares)
    store.write_parquet(PLAYERS, _players_frame(pw))

    rec = registry.record(
        params={"verb": "fit", "warmup": args.warmup, "samples": args.samples,
                "chains": args.chains, "table": args.table, **cfg.as_dict()},
        data_hash=_data_hash(store, (args.table, "pbp")),
        seed=cfg.seed,
    )
    _emit("fit", version=rec.version, players=data.n_players, obs=data.n_obs,
          rhat_max=round(report.rhat_max, 4), ess_min=round(report.ess_min, 1),
          divergences=report.n_divergences, converged=report.passed, seed=cfg.seed,
          quantiles=store.path(QUANTILES), draws=projection.draws_path)
    return 0


def _cmd_sim(args: argparse.Namespace) -> int:
    """Run the correlated Monte-Carlo simulation over the fitted marginals."""
    from blitz_engine.simulation.mc import SimConfig, simulate

    cfg, store, registry = _wire(args)
    marginals = _season_marginals(_read_table(store, QUANTILES))
    players = _read_table(store, PLAYERS)

    sim_cfg = SimConfig(
        n_runs=args.runs, batch_size=args.batch or cfg.mc_batch, seed=cfg.seed
    )
    result = simulate(marginals, players, config=sim_cfg)
    store.write_parquet(MC_PROBS, result.outputs)
    store.write_parquet(CORR, result.corr_matrix)

    league: dict[str, object] | None = None
    if args.league:
        from blitz_engine.simulation.league import LeagueConfig, Roster, simulate_league
        from blitz_engine.value.mcts import SUPERFLEX_TEMPLATE

        slots = _feasible_starters(players["position"].unique(), SUPERFLEX_TEMPLATE)
        ranked = marginals.sort_values("mean", ascending=False)["player_id"].astype(str).tolist()
        n_teams = args.league if args.league % 2 == 0 else args.league + 1
        # Roster depth degrades to what the board can actually fill (never an error).
        per_team = min(len(slots), len(ranked) // n_teams)
        if per_team < 1:
            raise ValueError(f"league sim needs >= {n_teams} players, board has {len(ranked)}")
        picks: list[list[str]] = [[] for _ in range(n_teams)]
        for i, pid in enumerate(ranked[: n_teams * per_team]):  # snake draft over the board
            rnd, seat = divmod(i, n_teams)
            picks[seat if rnd % 2 == 0 else n_teams - 1 - seat].append(pid)
        rosters = [Roster(id=f"t{i}", starters=tuple(p)) for i, p in enumerate(picks)]
        lr = simulate_league(
            marginals, players, rosters, _round_robin([r.id for r in rosters], args.weeks),
            config=LeagueConfig(n_seasons=args.league_seasons, seed=cfg.seed,
                                playoff_teams=min(args.playoff_teams, n_teams)),
        )
        store.write_parquet("league_standings", lr.standings)
        league = {"rosters": len(rosters), "weeks": args.weeks, "n_seasons": lr.n_seasons,
                  "champion": str(lr.p_champion().idxmax())}

    rec = registry.record(
        params={"verb": "sim", "n_runs": sim_cfg.n_runs, "batch_size": sim_cfg.batch_size,
                "league": bool(args.league), **cfg.as_dict()},
        data_hash=_data_hash(store, (QUANTILES, PLAYERS)),
        seed=cfg.seed,
    )
    _emit("sim", version=rec.version, players=len(result.outputs), n_runs=result.n_runs,
          batch=result.batch_size, peak_mb=round(result.peak_bytes / 1024**2, 1),
          within_budget=result.within_budget, cloud_burst_suggested=result.cloud_burst_suggested,
          seed=cfg.seed, mc_probs=store.path(MC_PROBS), corr=store.path(CORR), league=league)
    return 0


def _cmd_draft(args: argparse.Namespace) -> int:
    """Compute the live equity board, the fast-policy pick, an MCTS plan and a legal roster."""
    import pandas as pd

    from blitz_engine.value.equity import live_draft_value
    from blitz_engine.value.mcts import SUPERFLEX_TEMPLATE, DraftState, mcts_plan
    from blitz_engine.value.opponent import OpponentField
    from blitz_engine.value.policy import FastDraftPolicy
    from blitz_engine.value.roster_solver import Player, RosterRequirements, solve_roster

    cfg, store, registry = _wire(args)
    by_pos, positions = _value_board(store)
    slots = _feasible_starters(by_pos.keys(), SUPERFLEX_TEMPLATE)
    if not slots:
        raise ValueError("no draftable positions on the board")

    field_ = OpponentField.uniform(args.opponents)
    board = live_draft_value(by_pos, field_, sensitivity=args.sensitivity)
    policy_pick = FastDraftPolicy().pick(board, slots, positions)

    root = DraftState(board={p: tuple(v) for p, v in by_pos.items()}, slots_left=slots)
    plan = mcts_plan(root, field_, n_iter=args.mcts_iter, seed=cfg.seed)

    pool = [Player(id=pid, position=positions[pid], value=val)
            for pid, val in board.ranked[: args.pool]]
    lineup = solve_roster(
        pool, RosterRequirements(starters=slots, bench_size=args.bench), rounds_remaining=99
    )

    store.write_parquet(DRAFT_BOARD, pd.DataFrame({
        "player_id": [p for p, _ in board.ranked],
        "position": [positions[p] for p, _ in board.ranked],
        "equity_value": [v for _, v in board.ranked],
        "vorp": [board.vorp[p] for p, _ in board.ranked],
    }))
    strategy = {"best_action": plan.best_action, "value_estimate": plan.value_estimate,
                "action_visits": plan.action_visits, "action_values": plan.action_values,
                "policy_target": plan.policy_target(), "slots": list(slots)}
    (store.root / STRATEGY_JSON).write_text(json.dumps(strategy, indent=2, default=str))
    (store.root / POLICY_JSON).write_text(json.dumps(
        {"pick": policy_pick[0] if policy_pick else None,
         "position": policy_pick[1] if policy_pick else None,
         "weights": list(FastDraftPolicy().weights.coef)}, indent=2, default=str))

    rec = registry.record(
        params={"verb": "draft", "opponents": args.opponents, "mcts_iter": args.mcts_iter,
                "slots": list(slots), **cfg.as_dict()},
        data_hash=_data_hash(store, (QUANTILES, PLAYERS)),
        seed=cfg.seed,
    )
    _emit("draft", version=rec.version, candidates=len(board.ranked), best=board.best(),
          policy_pick=policy_pick[0] if policy_pick else None,
          mcts_best=plan.best_action, value_estimate=round(plan.value_estimate, 4),
          starters=len(lineup.starters), starter_value=round(lineup.starter_value, 2),
          seed=cfg.seed, board=store.path(DRAFT_BOARD), strategy=store.root / STRATEGY_JSON)
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    """Assemble the versioned snapshot bundle + the compact public export."""
    import pandas as pd

    from blitz_engine.snapshot import SCHEMA_VERSION, Snapshot
    from blitz_engine.snapshot.publish_availability import (
        build_availability_rows,
        publish_availability,
    )

    cfg, store, registry = _wire(args)
    empty = pd.DataFrame()
    quantiles = _read_table(store, QUANTILES)
    values = _read_table(store, args.values, required=False) if args.values else None
    corr = _read_table(store, CORR, required=False)
    mc_probs = _read_table(store, MC_PROBS, required=False)

    # e2b: publish the availability surface alongside the snapshot (docs/design/v5-architecture.md
    # §4). Degrade-safe on both ends — an absent `players` table skips availability entirely
    # (still exit 0), and `publish_availability` no-ops without SUPABASE_SERVICE_ROLE_KEY.
    players = _read_table(store, PLAYERS, required=False)
    availability = None
    if players is not None and not args.skip_availability:
        avail_rows = build_availability_rows(players, args.season, args.week)
        availability = publish_availability(avail_rows)

    def _json_file(name: str) -> dict:
        path = store.root / name
        return json.loads(path.read_text()) if path.exists() else {}

    snap = Snapshot(
        values=quantiles if values is None else values,
        quantiles=quantiles,
        corr_matrix=empty if corr is None else corr,
        mc_probs=empty if mc_probs is None else mc_probs,
        strategy_tree=_json_file(STRATEGY_JSON),
        policy=_json_file(POLICY_JSON),
    )
    rec = registry.record(
        params={"verb": "publish", "schema_version": SCHEMA_VERSION, **cfg.as_dict()},
        data_hash=_data_hash(store, (QUANTILES, CORR, MC_PROBS)),
        seed=cfg.seed,
    )
    out = Path(args.out).expanduser() if args.out else cfg.data_root / "snapshots" / rec.version
    full = snap.write(out)
    compact = snap.export_compact(Path(args.compact_out).expanduser() if args.compact_out
                                 else out / "compact")
    _emit("publish", version=rec.version, schema_version=SCHEMA_VERSION, seed=cfg.seed,
          rows={"values": len(snap.values), "quantiles": len(snap.quantiles),
                "corr_matrix": len(snap.corr_matrix), "mc_probs": len(snap.mc_probs)},
          full=full, compact=compact, availability=availability)
    return 0


_HANDLERS = {
    "fit": _cmd_fit,
    "sim": _cmd_sim,
    "draft": _cmd_draft,
    "publish": _cmd_publish,
}


def _add_verb_options(verb: str, p: argparse.ArgumentParser) -> None:
    """Only the options the verb's real module actually needs (`ponytail:` no dead knobs)."""
    if verb == "fit":
        p.add_argument("--table", default=PLAYER_WEEKS,
                       help=f"Tidy player-week table (default {PLAYER_WEEKS}; falls back to pbp).")
        p.add_argument("--seasons", type=int, nargs="*", default=None, help="Seasons to fit on.")
        p.add_argument("--max-players", type=int, default=None,
                       help="Keep only the N busiest players (bounds the 16 GB fit).")
        p.add_argument("--warmup", type=int, default=500, help="NUTS warmup draws.")
        p.add_argument("--samples", type=int, default=500, help="NUTS posterior draws per chain.")
        p.add_argument("--chains", type=int, default=2, help="Chains (run sequentially).")
        p.add_argument("--no-gate", action="store_true",
                       help="Report convergence instead of blocking on it (dev only).")
    elif verb == "sim":
        p.add_argument("--runs", type=int, default=100_000, help="Monte-Carlo runs.")
        p.add_argument("--batch", type=int, default=None,
                       help="Draws per streamed batch (default: config.mc_batch).")
        p.add_argument("--league", type=int, default=0,
                       help="Also simulate an N-team league off the value board (0 = skip).")
        p.add_argument("--weeks", type=int, default=14, help="League regular-season weeks.")
        p.add_argument("--league-seasons", type=int, default=2_000, help="League seasons to sim.")
        p.add_argument("--playoff-teams", type=int, default=6,
                       help="Playoff berths (clamped to the number of rosters).")
    elif verb == "draft":
        p.add_argument("--opponents", type=int, default=9, help="GMs picking before your turn.")
        p.add_argument("--mcts-iter", type=int, default=400, help="MCTS simulations.")
        p.add_argument("--sensitivity", type=float, default=1.0, help="Equity sensitivity.")
        p.add_argument("--pool", type=int, default=60, help="Top-N board rows fed to the solver.")
        p.add_argument("--bench", type=int, default=6, help="Bench slots in the roster solve.")
    elif verb == "publish":
        p.add_argument("--values", default=None,
                       help=f"Table to publish as `values` (default: {QUANTILES}).")
        p.add_argument("--out", default=None,
                       help="Full snapshot dir (default: <data_root>/snapshots/<version>).")
        p.add_argument("--compact-out", default=None,
                       help="Compact export dir (default: <out>/compact).")
        p.add_argument("--season", type=int, default=datetime.now(UTC).year,
                       help="Season the availability rows are published for (default: this year).")
        p.add_argument("--week", type=int, default=1,
                       help="Week the availability rows are published for (default: 1).")
        p.add_argument("--skip-availability", action="store_true",
                       help="Skip the availability publish step entirely (snapshot only).")


def build_parser() -> argparse.ArgumentParser:
    """The full argparse tree — one subparser per verb, shared global options."""
    parser = argparse.ArgumentParser(
        prog="blitz-engine",
        description="BlitzBoard local quant engine — fit | sim | draft | publish.",
    )
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in _VERBS:
        p = sub.add_parser(verb, help=_HANDLERS[verb].__doc__ or verb)
        p.add_argument("--data-root", default=None,
                       help="Override the local store/snapshot/registry root.")
        p.add_argument("--seed", type=int, default=None, help="Override the RNG seed.")
        p.add_argument("--cloud-burst", action="store_true", default=None,
                       help="Opt in to external heavy compute (never the default).")
        _add_verb_options(verb, p)
        p.set_defaults(func=_HANDLERS[verb])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for the `blitz-engine` console script. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 — a verb failure is an exit code, not a traceback
        print(json.dumps({"verb": args.verb, "ok": False,
                          "error": f"{type(exc).__name__}: {exc}"}), flush=True)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
