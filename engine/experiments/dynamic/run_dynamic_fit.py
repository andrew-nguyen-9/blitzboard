"""E11 dynamic fit: MCTS → distill → PPO on REAL corpus data, graded by the **E5 metric**.

Stages (each writes a JSON receipt into ``results/`` and can be re-run independently):

  distill  — MCTS on the real board at every decision point of a real draft → `distill_policy`
             weights + the MCTS-agreement rate of the distilled linear policy.
  gate     — A/B the fitted weights against the shipped `DEFAULT_WEIGHTS` under E5's
             `started_points`, paired per (config, season); bootstrap CI must clear 0.
  ppo      — PPO self-play on the real universe whose reward IS E5 `started_points`, then the
             same gate against the distilled baseline. Checkpoints every iteration.

Reproduce:  see README.md
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.value.policy import (
    DEFAULT_WEIGHTS,
    FEATURE_NAMES,
    FastDraftPolicy,
    PolicyWeights,
    distill_policy,
)
from blitz_engine.value.rl import real_env as R
from blitz_engine.value.rl.train import DraftEnv, select_live_policy

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
MATRIX = HERE.parents[2] / "fixtures" / "league_matrix.json"

#: The fit/eval grid: three corpus seasons × three smoke matrix rows (teams 8/12/14, 1qb/sf/2qb).
YEARS = (2018, 2021, 2024)
ROW_IDS = ("t8-1qb-std-te0.0-b4-ir0", "t12-1qb-half-te0.5-b8-ir0", "t10-2qb-ppr-te0.0-b8-ir1")
SEED = 20260825


def rows() -> list[dict[str, Any]]:
    doc = json.loads(MATRIX.read_text())
    by_id = {r["id"]: r for r in doc["rows"]}
    return [by_id[i] for i in ROW_IDS]


def configs() -> list[tuple[int, dict[str, Any]]]:
    return [(y, r) for y in YEARS for r in rows()]


def _write(name: str, payload: dict[str, Any]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path}")
    return path


def _gate(cand: Any, base: Any, *, n_seasons: int, label: str) -> dict[str, Any]:
    t = time.time()
    edge = R.season_metric_edge(cand, base, configs(), n_seasons=n_seasons, seed=SEED)
    res = select_live_policy(cand, base, edge, seed=SEED)
    lo, hi = res.ci
    out = {
        "label": label,
        "metric": "SeasonEvalResult.started_points (E5)",
        "n_eval_points": len(edge),
        "n_configs": len(configs()),
        "n_seasons": n_seasons,
        "seed": SEED,
        "mean_edge": res.mean_edge,
        "ci95": [lo, hi],
        "verdict": "helps" if res.beat_baseline else "no-help",
        "promoted": bool(res.beat_baseline),
        "seconds": round(time.time() - t, 1),
        "edge": [round(float(e), 4) for e in edge],
    }
    print(json.dumps({k: v for k, v in out.items() if k != "edge"}))
    return out


# ── stages ─────────────────────────────────────────────────────────────────────────────
def stage_distill(n_iter: int, n_drafts: int) -> None:
    samples: list[Any] = []
    best: list[str] = []
    t = time.time()
    for k, (year, row) in enumerate(configs()[:n_drafts]):
        s, b = R.distill_samples(year, row, n_iter=n_iter, seed=SEED + k)
        samples.extend(s)
        best.extend(b)
    fitted = distill_policy(samples, n_steps=600)
    payload = {
        "n_samples": len(samples),
        "n_drafts": min(n_drafts, len(configs())),
        "mcts_iter": n_iter,
        "seed": SEED,
        "feature_names": list(FEATURE_NAMES),
        "cold_weights": dict(zip(FEATURE_NAMES, DEFAULT_WEIGHTS, strict=True)),
        "fitted_weights": fitted.as_dict(),
        "agreement_cold": R.policy_agreement(FastDraftPolicy(), samples, best),
        "agreement_fitted": R.policy_agreement(
            FastDraftPolicy(weights=fitted), samples, best
        ),
        "seconds": round(time.time() - t, 1),
    }
    _write("distill.json", payload)


def stage_gate(n_seasons: int) -> None:
    fitted = PolicyWeights(
        coef=np.array(
            [json.loads((RESULTS / "distill.json").read_text())["fitted_weights"][f]
             for f in FEATURE_NAMES]
        )
    )
    out = _gate(
        FastDraftPolicy(weights=fitted), FastDraftPolicy(),
        n_seasons=n_seasons, label="distilled-real vs shipped-cold weights",
    )
    out["fitted_weights"] = fitted.as_dict()
    _write("gate_distilled.json", out)


def stage_ppo(n_iters: int, episodes: int, n_seasons: int, eval_seasons: int) -> None:
    from blitz_engine.value.rl.policy_net import RLDraftPolicy
    from blitz_engine.value.rl.train import train_rl_policy

    year, row = configs()[-1]
    uni, pool = R.real_universe(year, str(row["id"]), top_n=90)
    ckpt = HERE / "checkpoints"
    ckpt.mkdir(exist_ok=True)
    trace: list[dict[str, float]] = []

    def on_iter(it: int, net: Any, rets: list[float]) -> None:
        import torch

        trace.append({"iter": it, "mean_return": float(np.mean(rets)) if rets else 0.0})
        torch.save(net.state_dict(), ckpt / "ppo_latest.pt")
        (ckpt / "trace.json").write_text(json.dumps(trace, indent=1) + "\n")
        print(f"iter {it} mean E5 return {trace[-1]['mean_return']:.1f}", flush=True)

    env = DraftEnv(
        n_teams=int(row["teams"]),
        template=R.row_template(row),
        universe_fn=lambda _seed, _u=uni: dict(_u),
        league_reward_fn=R.e5_league_reward(pool, row, n_seasons=n_seasons, base_seed=SEED),
    )
    distilled = FastDraftPolicy()
    t = time.time()
    net = train_rl_policy(
        env=env, n_iters=n_iters, episodes_per_iter=episodes,
        distilled_weights=distilled.weights, seed=SEED % 10_000, on_iter=on_iter,
    )
    train_s = round(time.time() - t, 1)
    out = _gate(
        RLDraftPolicy(net=net), distilled, n_seasons=eval_seasons,
        label="PPO(real universe, E5 reward) vs distilled baseline",
    )
    out |= {
        "train_seconds": train_s, "train_iters": n_iters, "episodes_per_iter": episodes,
        "reward": f"E5 started_points, n_seasons={n_seasons}",
        "train_universe": {"year": year, "row": row["id"], "n_players": len(uni)},
        "return_trace": trace,
    }
    _write("gate_ppo.json", out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=("distill", "gate", "ppo"))
    ap.add_argument("--mcts-iter", type=int, default=300)
    ap.add_argument("--drafts", type=int, default=9)
    ap.add_argument("--n-seasons", type=int, default=4)
    ap.add_argument("--ppo-iters", type=int, default=12)
    ap.add_argument("--episodes", type=int, default=4)
    ap.add_argument("--reward-seasons", type=int, default=1)
    a = ap.parse_args()
    if a.stage == "distill":
        stage_distill(a.mcts_iter, a.drafts)
    elif a.stage == "gate":
        stage_gate(a.n_seasons)
    else:
        stage_ppo(a.ppo_iters, a.episodes, a.reward_seasons, a.n_seasons)


if __name__ == "__main__":
    main()
