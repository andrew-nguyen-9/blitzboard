"""Model backtest 2015-2025 (v3 Epic 12): validate VORP ranking + the season-long Monte
Carlo simulator out-of-sample against real nflverse actuals, then upload the metrics.

Out-of-sample by construction: each season S is projected ONLY from season S-1 per-game
actuals (prior usage + week-to-week variance), then scored on season S real totals — no
hindsight. This is heavy (≈11 seasons of nflverse weekly frames, cached under data/), so it
runs LOCALLY or via the manual-dispatch workflow — never in daily CI (keeps CI minutes low).

Metrics → table `model_backtest` (PK model,season; season 0 = across-seasons summary):
  • vorp        : spearman(value, actual season pts) overall + per position; top-24 precision.
  • monte_carlo : P10-P90 interval coverage (target ≈0.80), mean-abs-error, spearman(mean,actual).

Upload is idempotent (upsert) and null-safe: with no SUPABASE_SERVICE_ROLE_KEY it dry-runs
and just prints (mirrors common.upsert / publish_snapshot). Models are computed + validated
regardless of keys.

    python -m backtest.models_backtest --seasons 2015-2025
    python -m backtest.models_backtest --no-upload          # compute only
"""
from __future__ import annotations

import argparse

from common import console, upsert

from models import Projection, SeasonSimulator, VorpEngine, from_per_game
from models.projector import PROJECTED_GAMES

from .actuals import season_actuals
from .cache import cached
from .rules import load_rules_fixture

BASE_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
MIN_PRIOR_GAMES = 4   # need a few games to trust a prior-season per-game line
TOP_N = 24
# A prior-season per-game line is a NOISY projection of next-season talent/role, so the
# realized spread is wider than within-season variance alone. Inflate per-game σ by a
# between-season drift term (≈ PROJ_DRIFT × ppg_mean, in quadrature). ponytail: tuned
# calibration knob — backtest coverage rises toward realism (residual under-coverage is
# real year-over-year fantasy volatility, see 12.done.md). The LIVE model doesn't need this:
# EnsembleProjector σ already bakes in cross-projector disagreement (estimation error).
PROJ_DRIFT = 0.5


def season_player_lines(season: int) -> dict[str, dict]:
    """player_key → {pos,name,total,games,ppg_mean,ppg_stdev} for a season (cached)."""
    def build():
        import pandas as pd
        rows = season_actuals(season)
        by: dict[str, dict] = {}
        for r in rows:
            d = by.setdefault(r["player_key"], {"pos": r["pos"], "name": r["name"], "pts": []})
            d["pts"].append(float(r["points"]))
        recs = []
        for k, d in by.items():
            pts = d["pts"]
            g = len(pts)
            mean = sum(pts) / g if g else 0.0
            var = sum((x - mean) ** 2 for x in pts) / g if g else 0.0
            recs.append({"player_key": k, "pos": d["pos"], "name": d["name"],
                         "total": sum(pts), "games": g, "ppg_mean": mean, "ppg_stdev": var ** 0.5})
        return pd.DataFrame(recs)
    df = cached(f"lines_{season}", build)
    return {r["player_key"]: r for r in df.to_dict("records")}


def _spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation via Pearson on ranks (numpy only — no scipy in the venv)."""
    import numpy as np
    ax, ay = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    if len(ax) < 3 or ax.std() == 0 or ay.std() == 0:   # constant input ⇒ undefined corr
        return 0.0
    rx = np.argsort(np.argsort(ax))
    ry = np.argsort(np.argsort(ay))
    return float(np.corrcoef(rx, ry)[0, 1])


def _build_projections(prior: dict) -> tuple[dict, dict]:
    """Prior-season per-game lines → season Projections + positions, for players with enough
    prior games. season μ = ppg·PROJECTED_GAMES; season σ = ppg_σ·√games."""
    projections, positions = {}, {}
    for k, d in prior.items():
        if d["pos"] not in BASE_POSITIONS or d["games"] < MIN_PRIOR_GAMES:
            continue
        mean = d["ppg_mean"] * PROJECTED_GAMES
        stdev = max(d["ppg_stdev"] * (PROJECTED_GAMES ** 0.5), 1.0)
        projections[k] = Projection(player_id=k, season=0, source="prior-actuals", mean=mean,
                                    stdev=stdev, floor=mean - 1.28 * stdev, ceiling=mean + 1.28 * stdev)
        positions[k] = d["pos"]
    return projections, positions


def _vorp_metrics(projections, positions, target) -> dict:
    """Spearman(shaped value, actual season pts) overall + per position, and top-24 precision."""
    rules = load_rules_fixture()
    vals = VorpEngine().compute(projections, positions, rules)
    pairs = [(v, target[v.player_id]["total"]) for v in vals if v.player_id in target]
    if len(pairs) < 3:
        return {"n": len(pairs)}
    overall = _spearman([v.value for v, _ in pairs], [t for _, t in pairs])
    by_pos = {}
    for pos in BASE_POSITIONS:
        sub = [(v, t) for v, t in pairs if positions.get(v.player_id) == pos]
        if len(sub) >= 5:
            by_pos[pos] = round(_spearman([v.value for v, _ in sub], [t for _, t in sub]), 4)
    model_top = {v.player_id for v in sorted((v for v, _ in pairs), key=lambda v: v.value, reverse=True)[:TOP_N]}
    actual_top = {pid for pid, _ in sorted(((v.player_id, t) for v, t in pairs), key=lambda x: x[1], reverse=True)[:TOP_N]}
    precision = len(model_top & actual_top) / TOP_N
    return {"spearman": round(overall, 4), "spearman_by_pos": by_pos,
            "top24_precision": round(precision, 4), "n": len(pairs)}


def _mc_metrics(prior, positions, target, seed: int) -> dict:
    """P10-P90 coverage, mean-abs-error, spearman(mean,actual) for the season simulator."""
    inputs = [from_per_game(k, positions[k], prior[k]["ppg_mean"],
                            (prior[k]["ppg_stdev"] ** 2 + (PROJ_DRIFT * prior[k]["ppg_mean"]) ** 2) ** 0.5)
              for k in positions]
    outcomes = SeasonSimulator(n_sims=4000, seed=seed).simulate(inputs)
    rows = [(o, target[o.player_id]["total"]) for o in outcomes if o.player_id in target]
    if len(rows) < 3:
        return {"n": len(rows)}
    covered = sum(1 for o, t in rows if o.floor <= t <= o.ceiling) / len(rows)
    mae = sum(abs(o.proj_mean - t) for o, t in rows) / len(rows)
    sp = _spearman([o.proj_mean for o, _ in rows], [t for _, t in rows])
    return {"coverage": round(covered, 4), "mae": round(mae, 2),
            "spearman_mean": round(sp, 4), "n": len(rows)}


def run(seasons: list[int]) -> list[dict]:
    """Backtest each season; return upsert rows for `model_backtest` (incl. season-0 summary)."""
    vorp_rows, mc_rows = [], []
    for s in seasons:
        try:  # a not-yet-published season 404s at nflverse — skip it, don't crash the run.
            prior = season_player_lines(s - 1)
            target = season_player_lines(s)
        except Exception as e:  # noqa: BLE001 — any fetch/parse failure for one season is non-fatal
            console.print(f"[yellow]⚠ {s}: actuals unavailable ({type(e).__name__}) — skipping.[/yellow]")
            continue
        if not prior or not target:
            console.print(f"[yellow]⚠ {s}: missing prior/target actuals — skipping.[/yellow]")
            continue
        projections, positions = _build_projections(prior)
        if not projections:
            console.print(f"[yellow]⚠ {s}: no projectable players — skipping.[/yellow]")
            continue
        vm = _vorp_metrics(projections, positions, target)
        mm = _mc_metrics(prior, positions, target, seed=s)
        console.print(f"[cyan]{s}: VORP ρ={vm.get('spearman')} p@24={vm.get('top24_precision')} · "
                      f"MC coverage={mm.get('coverage')} mae={mm.get('mae')} (n={mm.get('n')})[/cyan]")
        vorp_rows.append({"season": s, **vm})
        mc_rows.append({"season": s, **mm})

    rows: list[dict] = []
    rows += [{"model": "vorp", "season": r["season"], "metrics": r} for r in vorp_rows]
    rows += [{"model": "monte_carlo", "season": r["season"], "metrics": r} for r in mc_rows]
    rows.append(_summary("vorp", vorp_rows, ("spearman", "top24_precision")))
    rows.append(_summary("monte_carlo", mc_rows, ("coverage", "mae", "spearman_mean")))
    return rows


def _summary(model: str, rows: list[dict], keys: tuple[str, ...]) -> dict:
    """season-0 across-seasons summary row: mean of each metric over the backtested seasons."""
    seasons = [r["season"] for r in rows]
    metrics = {"seasons": seasons}
    for key in keys:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        metrics[key] = round(sum(vals) / len(vals), 4) if vals else None
    return {"model": model, "season": 0, "metrics": metrics}


def _parse_seasons(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split()]


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest VORP + season Monte Carlo vs 2015-2025 actuals.")
    ap.add_argument("--seasons", default="2015-2025", help="range '2015-2025' or list '2015 2016 ...'")
    ap.add_argument("--no-upload", action="store_true", help="compute only; skip Supabase upload")
    args = ap.parse_args()

    rows = run(_parse_seasons(args.seasons))
    if not rows:
        console.print("[red]No seasons backtested.[/red]")
        return
    for r in rows:
        if r["season"] == 0:
            console.print(f"[bold green]{r['model']} summary: {r['metrics']}[/bold green]")
    if args.no_upload:
        console.print("[dim]--no-upload: skipping Supabase write.[/dim]")
        return
    # Idempotent: upsert on (model, season). Null-safe → dry-run without service-role key.
    upsert("model_backtest", rows, on_conflict="model,season")


if __name__ == "__main__":
    main()
