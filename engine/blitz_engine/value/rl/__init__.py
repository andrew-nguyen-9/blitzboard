"""RL draft policy (E4-rl-policy) — PPO self-play net + degrade-neutral gate to distilled policy.

Optional / "later wave", rel=degrade: the RL policy net (`policy_net.py`) is trained by PPO
self-play (`train.py`) whose reward is roster championship equity, and is promoted to the live
board only if it *beats* the distilled `FastDraftPolicy` baseline on a held-out backtest —
otherwise the shipped distilled policy stays live (`build_live_policy` returns it unchanged).

Instant inference: `RLDraftPolicy` mirrors `FastDraftPolicy.pick`/`pick_live` — one forward pass
per open position over the board the draft room already computes, no sim, no search.
"""
from __future__ import annotations

from blitz_engine.value.rl.policy_net import (
    DraftPolicyNet,
    RLDraftPolicy,
    warm_start_net,
)
from blitz_engine.value.rl.train import (
    DraftEnv,
    LivePolicyResult,
    RewardFn,
    bootstrap_ci,
    build_live_policy,
    draft_universe,
    evaluate_edge,
    select_live_policy,
    starter_value_reward,
    train_rl_policy,
)

__all__ = [
    "DraftPolicyNet",
    "RLDraftPolicy",
    "warm_start_net",
    "DraftEnv",
    "LivePolicyResult",
    "RewardFn",
    "bootstrap_ci",
    "build_live_policy",
    "draft_universe",
    "evaluate_edge",
    "select_live_policy",
    "starter_value_reward",
    "train_rl_policy",
]
