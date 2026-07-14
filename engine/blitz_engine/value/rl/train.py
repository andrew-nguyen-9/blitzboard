"""PPO self-play trainer + the degrade-neutral gate for the RL draft policy (E4-rl-policy).

The offline MCTS was distilled into the linear `FastDraftPolicy`; this trains a `DraftPolicyNet`
to *beat* that distilled baseline by **PPO self-play** on a snake draft whose reward is the roster
you build (a fast championship-equity proxy; swap in `equity_evaluator` for cloud-burst runs).

Because this unit is **rel=degrade / optional**, the honest contract is: train, then grade the RL
policy against the distilled baseline on a held-out backtest. If it clears the bar (bootstrap CI
of the per-seed edge > 0) the live board may use it; otherwise `build_live_policy` returns the
distilled policy unchanged — **degrade-neutral, never worse, never a fake green**.

* `DraftEnv` — a deterministic snake-draft universe + self-play roller (reuses `live_draft_value`
  + `position_features`, so every produced roster is legal by construction).
* `train_rl_policy` — bounded PPO self-play (``float32``, CPU) from a warm-started net.
* `evaluate_edge` / `bootstrap_ci` — per-seed RL-minus-distilled roster edge + its CI.
* `build_live_policy` — the one-call entry the draft room reads: trains, grades, and returns the
  winner (RL if it beat the baseline, else the distilled fallback) with the verdict attached.

`ponytail:` the self-play environment is the *same* board (`live_draft_value`) and the *same*
features (`position_features`) the live policy uses — the trainer adds only a PPO loop and a
bootstrap gate; the reward is the shipped `starter_value` proxy.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import torch
from torch.distributions import Categorical

from blitz_engine.value.equity import live_draft_value
from blitz_engine.value.mcts import SUPERFLEX_TEMPLATE, slot_positions
from blitz_engine.value.opponent import OpponentField
from blitz_engine.value.policy import FastDraftPolicy, PolicyWeights, position_features
from blitz_engine.value.replacement import static_replacement_levels
from blitz_engine.value.rl.policy_net import DraftPolicyNet, RLDraftPolicy, warm_start_net

# The draftable universe: position -> (count, top value·week⁻¹, decay). Mirrors the scarcity
# shape of the E4-value-equity / MCTS fixtures (a steep RB/TE cliff, deep WR, shallow K/DST).
_POS_SPEC: dict[str, tuple[int, float, float]] = {
    "QB": (24, 26.0, 0.55), "RB": (30, 24.0, 1.4), "WR": (36, 23.0, 0.7),
    "TE": (18, 20.0, 1.8), "K": (12, 9.0, 0.15), "DST": (12, 9.0, 0.15),
}


def draft_universe(seed: int) -> dict[str, tuple[str, float]]:
    """A deterministic player universe: ``player_id -> (position, value·week⁻¹)``."""
    rng = np.random.default_rng(seed)
    players: dict[str, tuple[str, float]] = {}
    for pos, (n, top, decay) in _POS_SPEC.items():
        for i in range(n):
            mean = top * float(np.exp(-decay * i / n * 3)) + float(rng.uniform(-1.0, 1.0))
            players[f"{pos}{i}"] = (pos, mean)
    return players


def _available(
    players: Mapping[str, tuple[str, float]], taken: set[str]
) -> dict[str, list[tuple[str, float]]]:
    """Remaining players grouped by position, each list sorted by value descending."""
    out: dict[str, list[tuple[str, float]]] = {}
    for pid, (pos, mean) in players.items():
        if pid not in taken:
            out.setdefault(pos, []).append((pid, mean))
    for lst in out.values():
        lst.sort(key=lambda pv: pv[1], reverse=True)
    return out


def _consume(slots_left: list[str], pos: str) -> None:
    """Drop the most specific open slot that accepts ``pos`` (keep flex slots free)."""
    slot = next((s for s in slots_left if s == pos), None)
    slot = slot or next(s for s in slots_left if pos in slot_positions(s))
    slots_left.remove(slot)


def _pick_raw_vorp(
    abp: Mapping[str, list[tuple[str, float]]], slots_left: Sequence[str]
) -> tuple[str, str] | None:
    """Baseline field pick: best static-VORP player over legal open positions."""
    allowed = {p for s in slots_left for p in slot_positions(s)}
    rep = static_replacement_levels({p: [m for _, m in lst] for p, lst in abp.items()})
    best, best_v = None, -1e9
    for pos, lst in abp.items():
        if pos in allowed and lst:
            v = lst[0][1] - rep.get(pos, 0.0)
            if v > best_v:
                best, best_v = (lst[0][0], pos), v
    return best


# --- reward -------------------------------------------------------------------------------
# A terminal reward: the roster you built. Default is the fast starter-value equity proxy the
# MCTS also uses as its cheap leaf; a sim-priced p_champion reward can be injected for heavy runs.
RewardFn = Callable[[Sequence[tuple[str, str, float]]], float]


def starter_value_reward(roster: Sequence[tuple[str, str, float]]) -> float:
    """Total points·week⁻¹ of the drafted starters (the fast championship-equity proxy)."""
    return float(sum(v for _, _, v in roster))


# --- self-play rollout --------------------------------------------------------------------
@dataclass
class _Step:
    """One decision in a self-play trajectory (kept for the PPO update)."""

    features: torch.Tensor  # [n_positions, N_FEATURES]
    positions: list[str]  # legal positions, aligned with rows of ``features``
    action: int  # index of the chosen position
    logp: float  # log-prob under the behaviour policy (for PPO ratio)
    ret: float = 0.0  # terminal return (filled once the draft finishes)


@dataclass
class DraftEnv:
    """Deterministic snake-draft self-play environment over a scarcity universe.

    All ``n_teams`` seats sample from the *current* net (true self-play), so the policy learns to
    draft against copies of itself. A team's return is `reward_fn` of the roster it built.
    """

    n_teams: int = 6
    template: tuple[str, ...] = SUPERFLEX_TEMPLATE
    reward_fn: RewardFn = starter_value_reward

    def rollout(
        self, net: DraftPolicyNet, *, seed: int, greedy: bool = False
    ) -> tuple[list[_Step], list[float]]:
        """Play one draft; return every team's trajectory steps and per-team returns.

        ``greedy`` argmaxes the net (evaluation); otherwise it samples (exploration for PPO).
        """
        players = draft_universe(seed)
        field = OpponentField.uniform(self.n_teams - 1)
        taken: set[str] = set()
        slots = {t: list(self.template) for t in range(self.n_teams)}
        rosters: dict[int, list[tuple[str, str, float]]] = {t: [] for t in range(self.n_teams)}
        steps: dict[int, list[_Step]] = {t: [] for t in range(self.n_teams)}

        for rnd in range(len(self.template)):
            order = range(self.n_teams) if rnd % 2 == 0 else reversed(range(self.n_teams))
            for t in order:
                abp = _available(players, taken)
                lb = live_draft_value({p: list(v) for p, v in abp.items()}, field)
                pos_of = {pid: p for p, lst in abp.items() for pid, _ in lst}
                feats = position_features(lb, slots[t], pos_of)
                if feats:
                    positions = list(feats)
                    x = torch.from_numpy(np.stack([feats[p] for p in positions])).float()
                    with torch.no_grad():  # behaviour policy: logp is a stored constant for PPO
                        dist = Categorical(logits=net(x))
                        action = int(dist.logits.argmax()) if greedy else int(dist.sample())
                        logp = float(dist.log_prob(torch.tensor(action)))
                    steps[t].append(
                        _Step(features=x, positions=positions, action=action, logp=logp)
                    )
                    pos = positions[action]
                    pid = abp[pos][0][0]
                    val = abp[pos][0][1]
                else:  # no legal net action → fall back to raw-VORP so the draft still completes
                    fallback = _pick_raw_vorp(abp, slots[t])
                    if fallback is None:
                        continue
                    pid, pos = fallback
                    val = next(v for p, v in abp[pos] if p == pid)
                taken.add(pid)
                rosters[t].append((pid, pos, val))
                _consume(slots[t], pos)

        returns = [self.reward_fn(rosters[t]) for t in range(self.n_teams)]
        flat: list[_Step] = []
        for t in range(self.n_teams):
            for st in steps[t]:
                st.ret = returns[t]
                flat.append(st)
        return flat, returns


# --- PPO training -------------------------------------------------------------------------
def train_rl_policy(
    *,
    n_teams: int = 6,
    template: tuple[str, ...] = SUPERFLEX_TEMPLATE,
    reward_fn: RewardFn = starter_value_reward,
    hidden: int = 16,
    n_iters: int = 12,
    episodes_per_iter: int = 4,
    ppo_epochs: int = 4,
    clip: float = 0.2,
    lr: float = 3e-3,
    entropy_coef: float = 0.01,
    warm_start: bool = True,
    distilled_weights: PolicyWeights | None = None,
    seed: int = 0,
) -> DraftPolicyNet:
    """Bounded PPO self-play (``float32``, CPU) from a warm-started net → a trained policy net.

    Each iteration rolls ``episodes_per_iter`` self-play drafts, computes advantages as the
    per-team return minus the batch baseline, and takes ``ppo_epochs`` clipped-surrogate steps.
    ``warm_start`` behaviour-clones the net to the distilled policy first (scarcity-aware start).
    M1-friendly: tiny net, four features, no GPU required.
    """
    torch.manual_seed(seed)
    net = (
        warm_start_net(distilled_weights, hidden=hidden, seed=seed)
        if warm_start
        else DraftPolicyNet(hidden=hidden)
    )
    env = DraftEnv(n_teams=n_teams, template=template, reward_fn=reward_fn)
    opt = torch.optim.Adam(net.parameters(), lr=lr)

    for it in range(n_iters):
        batch: list[_Step] = []
        for e in range(episodes_per_iter):
            steps, _ = env.rollout(net, seed=seed + 1 + it * episodes_per_iter + e)
            batch.extend(steps)
        if not batch:
            continue
        rets = np.array([st.ret for st in batch], dtype=np.float32)
        adv = rets - rets.mean()
        std = float(adv.std())
        adv = adv / std if std > 1e-8 else adv
        adv_t = torch.from_numpy(adv).float()
        old_logp = torch.tensor([st.logp for st in batch]).float()

        for _ in range(ppo_epochs):
            logps, entropies = [], []
            for st in batch:
                dist = Categorical(logits=net(st.features))
                logps.append(dist.log_prob(torch.tensor(st.action)))
                entropies.append(dist.entropy())
            logp = torch.stack(logps)
            entropy = torch.stack(entropies).mean()
            ratio = torch.exp(logp - old_logp)
            surr = torch.minimum(ratio * adv_t, torch.clamp(ratio, 1 - clip, 1 + clip) * adv_t)
            loss = -surr.mean() - entropy_coef * entropy
            opt.zero_grad()
            loss.backward()
            opt.step()
    return net


# --- backtest gate (degrade-neutral) ------------------------------------------------------
def _policy_edge_vs_raw(
    seed: int,
    policy: FastDraftPolicy | RLDraftPolicy,
    *,
    n_teams: int,
    template: tuple[str, ...],
) -> float:
    """Team-0 roster-value edge of ``policy`` vs a raw-VORP team-0 on the same seeded draft."""
    players = draft_universe(seed)
    field = OpponentField.uniform(n_teams - 1)

    def run(use_policy: bool) -> float:
        taken: set[str] = set()
        slots = {t: list(template) for t in range(n_teams)}
        roster0: list[tuple[str, float]] = []
        for rnd in range(len(template)):
            order = range(n_teams) if rnd % 2 == 0 else reversed(range(n_teams))
            for t in order:
                abp = _available(players, taken)
                if t == 0 and use_policy:
                    lb = live_draft_value({p: list(v) for p, v in abp.items()}, field)
                    pos_of = {pid: p for p, lst in abp.items() for pid, _ in lst}
                    pick = policy.pick(lb, slots[t], pos_of) or _pick_raw_vorp(abp, slots[t])
                else:
                    pick = _pick_raw_vorp(abp, slots[t])
                if pick is None:
                    continue
                pid, pos = pick
                taken.add(pid)
                if t == 0:
                    roster0.append((pid, players[pid][1]))
                _consume(slots[t], pos)
        return sum(v for _, v in roster0)

    return run(True) - run(False)


def evaluate_edge(
    rl: RLDraftPolicy,
    distilled: FastDraftPolicy,
    seeds: Sequence[int],
    *,
    n_teams: int = 6,
    template: tuple[str, ...] = SUPERFLEX_TEMPLATE,
) -> list[float]:
    """Per-seed RL-minus-distilled roster edge (each measured against the raw-VORP baseline)."""
    return [
        _policy_edge_vs_raw(s, rl, n_teams=n_teams, template=template)
        - _policy_edge_vs_raw(s, distilled, n_teams=n_teams, template=template)
        for s in seeds
    ]


def bootstrap_ci(
    sample: Sequence[float], *, seed: int = 0, n: int = 2000
) -> tuple[float, float]:
    """95% bootstrap confidence interval for the mean of ``sample``."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(sample, dtype=float)
    if arr.size == 0:
        return (0.0, 0.0)
    boots = [float(rng.choice(arr, arr.size, replace=True).mean()) for _ in range(n)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


@dataclass(frozen=True)
class LivePolicyResult:
    """The graded outcome the draft room consumes.

    ``policy`` is the one to use live: the RL policy iff it beat the distilled baseline (bootstrap
    CI of the edge clears 0), else the distilled fallback. ``beat_baseline`` records the verdict;
    ``ci``/``mean_edge`` expose the backtest so the degrade decision is auditable.
    """

    policy: FastDraftPolicy | RLDraftPolicy
    rl_policy: RLDraftPolicy
    distilled: FastDraftPolicy
    beat_baseline: bool
    mean_edge: float
    ci: tuple[float, float]


def select_live_policy(
    rl: RLDraftPolicy,
    distilled: FastDraftPolicy,
    edge: Sequence[float],
    *,
    seed: int = 0,
) -> LivePolicyResult:
    """Degrade-neutral gate: keep the RL policy only if its edge over distilled clears zero.

    A rel=degrade unit must never *lose* to the baseline it is optional over, so the fallback to
    the distilled policy is the default and the RL policy is promoted only on a bootstrap-CI win.
    """
    lo, hi = bootstrap_ci(edge, seed=seed)
    beat = lo > 0.0 and float(np.mean(edge)) > 0.0
    return LivePolicyResult(
        policy=rl if beat else distilled,
        rl_policy=rl,
        distilled=distilled,
        beat_baseline=beat,
        mean_edge=float(np.mean(edge)) if len(edge) else 0.0,
        ci=(lo, hi),
    )


def build_live_policy(
    *,
    train_seed: int = 0,
    eval_seeds: Sequence[int] | None = None,
    n_teams: int = 6,
    template: tuple[str, ...] = SUPERFLEX_TEMPLATE,
    reward_fn: RewardFn = starter_value_reward,
    distilled: FastDraftPolicy | None = None,
    **train_kw: object,
) -> LivePolicyResult:
    """One-call entry: warm-start + PPO self-play, grade vs distilled, return the winner.

    This is the surface the live draft room reads. On a degrade (RL fails to beat the distilled
    baseline) ``result.policy is result.distilled`` — the shipped fast policy stays live.
    """
    distilled = distilled or FastDraftPolicy()
    net = train_rl_policy(
        n_teams=n_teams, template=template, reward_fn=reward_fn,
        distilled_weights=distilled.weights, seed=train_seed, **train_kw,  # type: ignore[arg-type]
    )
    rl = RLDraftPolicy(net=net)
    seeds = list(eval_seeds) if eval_seeds is not None else list(range(100, 120))
    edge = evaluate_edge(rl, distilled, seeds, n_teams=n_teams, template=template)
    return select_live_policy(rl, distilled, edge, seed=train_seed)
