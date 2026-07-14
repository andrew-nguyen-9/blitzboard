"""E4-rl-policy — PPO self-play draft policy net + degrade-neutral gate to the distilled policy.

rel=degrade / optional ("later wave"): the RL policy net is trained by PPO self-play (reward =
roster championship-equity proxy) and warm-started from the distilled `FastDraftPolicy`. It is
promoted to the live board **only if it beats the distilled baseline** on a held-out backtest;
otherwise the distilled policy stays live. These tests cover the gates the brief names:

    * **instant inference** — the net picks in ≪1 ms over a precomputed board (drop-in for the
      distilled `FastDraftPolicy.pick`);
    * **warm start** — the net argmax-matches the distilled linear policy out of the box
      (scarcity-aware, degrade-neutral start);
    * **training runs** — bounded PPO self-play updates the net without collapsing;
    * **degrade-neutral gate** — the promotion is a bootstrap-CI win over the distilled baseline;
      on a degrade the live policy is the distilled one, unchanged (never worse, never fake-green);
    * **no regression** — the unit is purely additive to the value surface.

`ponytail:` the net eats the *same* four scarcity features and the *same* board (`live_draft_value`
+ `position_features`) as the distilled policy, so the tests reuse that live surface and every
produced roster is legal by construction.
"""
from __future__ import annotations

import time

import numpy as np
import torch

from blitz_engine.value.equity import live_draft_value
from blitz_engine.value.opponent import OpponentField
from blitz_engine.value.policy import DEFAULT_WEIGHTS, FastDraftPolicy
from blitz_engine.value.rl import (
    DraftEnv,
    RLDraftPolicy,
    build_live_policy,
    draft_universe,
    evaluate_edge,
    select_live_policy,
    train_rl_policy,
    warm_start_net,
)
from blitz_engine.value.rl.train import _POS_SPEC

_TEMPLATE = ("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPERFLEX", "K", "DST")
_N_TEAMS = 6


def _live_board(seed: int) -> tuple[object, dict[str, str]]:
    """A full-universe live board + player→position map for the given seed."""
    players = draft_universe(seed)
    board = {
        p: [(pid, players[pid][1]) for pid in players if players[pid][0] == p]
        for p in _POS_SPEC
    }
    field = OpponentField.uniform(_N_TEAMS - 1)
    lb = live_draft_value(board, field)
    pos_of = {pid: players[pid][0] for pid in players}
    return lb, pos_of


# ======================================================================================
# instant inference — the net is a drop-in for the fast distilled policy
# ======================================================================================
def test_rl_policy_instant_inference_is_fast() -> None:
    """A full draft's worth of net lookups over a precomputed board stays ≪1 ms/pick."""
    lb, pos_of = _live_board(1)
    rl = RLDraftPolicy(net=warm_start_net(seed=0))
    t0 = time.perf_counter()
    for _ in range(200):
        assert rl.pick(lb, list(_TEMPLATE), pos_of) is not None
    per_pick = (time.perf_counter() - t0) / 200
    assert per_pick < 1e-3, f"RL live lookup too slow: {per_pick * 1e6:.0f} us/pick"


def test_rl_policy_pick_matches_fast_policy_contract() -> None:
    """`RLDraftPolicy.pick` returns a legal ``(player_id, position)`` like `FastDraftPolicy`."""
    lb, pos_of = _live_board(2)
    pick = RLDraftPolicy(net=warm_start_net(seed=0)).pick(lb, list(_TEMPLATE), pos_of)
    assert pick is not None
    pid, pos = pick
    assert pos_of[pid] == pos  # the returned player actually plays the returned position


# ======================================================================================
# warm start — the net starts as the distilled scarcity-aware policy
# ======================================================================================
def test_warm_start_argmax_matches_distilled_policy() -> None:
    """Behaviour-cloned net argmaxes the same open position as the distilled linear policy."""
    fast = FastDraftPolicy()
    rl = RLDraftPolicy(net=warm_start_net(seed=0))
    agree = 0
    for s in range(6):
        lb, pos_of = _live_board(s)
        fs = fast.action_scores(lb, list(_TEMPLATE), pos_of)
        rs = rl.action_scores(lb, list(_TEMPLATE), pos_of)
        if max(fs, key=lambda p: fs[p]) == max(rs, key=lambda p: rs[p]):
            agree += 1
    assert agree >= 5, f"warm-started net should track the distilled policy, agreed {agree}/6"


# ======================================================================================
# training — bounded PPO self-play runs and updates the net without collapse
# ======================================================================================
def test_ppo_training_updates_weights_without_collapse() -> None:
    """PPO self-play moves the net off its warm start yet keeps the drafts sane (no collapse)."""
    warm = warm_start_net(seed=0)  # identical init to the trainer's internal warm start (seed=0)
    trained = train_rl_policy(seed=0, n_iters=8, episodes_per_iter=3)

    # the optimiser actually changed the policy — training was not a silent no-op.
    changed = any(
        not torch.allclose(a, b)
        for a, b in zip(warm.parameters(), trained.parameters(), strict=True)
    )
    assert changed, "PPO update left the net unchanged"

    # and the trained policy still drafts full, legal, sanely-valued rosters (no collapse).
    env = DraftEnv(n_teams=_N_TEAMS)
    seeds = range(200, 210)
    warm_total = np.mean([sum(env.rollout(warm, seed=s, greedy=True)[1]) for s in seeds])
    trained_total = np.mean([sum(env.rollout(trained, seed=s, greedy=True)[1]) for s in seeds])
    assert trained_total > 0.85 * warm_total  # value captured did not collapse


# ======================================================================================
# degrade-neutral gate — promote the RL policy ONLY on a bootstrap-CI win
# ======================================================================================
def test_select_promotes_only_on_ci_win() -> None:
    """`select_live_policy` returns the RL policy iff the per-seed edge CI clears zero."""
    rl = RLDraftPolicy(net=warm_start_net(seed=0))
    distilled = FastDraftPolicy()

    winning = [1.0, 1.2, 0.8, 1.1, 0.9, 1.3, 0.7, 1.0]  # clearly positive edge
    win = select_live_policy(rl, distilled, winning)
    assert win.beat_baseline and win.policy is rl and win.ci[0] > 0.0

    inconclusive = [0.2, -0.3, 0.1, -0.1, 0.0, -0.2, 0.15, -0.05]  # CI straddles zero
    deg = select_live_policy(rl, distilled, inconclusive)
    assert not deg.beat_baseline and deg.policy is distilled  # fall back to distilled


def test_build_live_policy_is_degrade_neutral() -> None:
    """End-to-end gate: the live policy is never worse than the distilled baseline."""
    distilled = FastDraftPolicy()
    res = build_live_policy(
        train_seed=0, eval_seeds=range(100, 116), n_iters=8, episodes_per_iter=3,
    )
    # the verdict is internally consistent: a promotion implies a positive mean edge + CI>0.
    if res.beat_baseline:
        assert res.mean_edge > 0.0 and res.ci[0] > 0.0
        assert res.policy is res.rl_policy
    else:
        # degrade: the shipped distilled policy stays live, unchanged.
        assert res.policy is res.distilled

    # the selected live policy is >= the distilled baseline on the held-out backtest (never worse).
    seeds = range(120, 132)
    selected_vs_distilled = evaluate_edge(
        res.policy if isinstance(res.policy, RLDraftPolicy) else res.rl_policy,
        distilled, seeds,
    ) if res.beat_baseline else [0.0]
    assert np.mean(selected_vs_distilled) >= -1e-9


# ======================================================================================
# no regression — additive to the value surface, distilled baseline untouched
# ======================================================================================
def test_no_regression_distilled_baseline_untouched() -> None:
    """Importing the RL unit does not perturb the shipped distilled fast policy."""
    assert tuple(FastDraftPolicy().weights.coef) == DEFAULT_WEIGHTS
    # the RL policy is a distinct, additive surface (its own pick path).
    lb, pos_of = _live_board(3)
    assert RLDraftPolicy(net=warm_start_net(seed=0)).pick(lb, list(_TEMPLATE), pos_of) is not None
