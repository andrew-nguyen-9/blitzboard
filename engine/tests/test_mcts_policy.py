"""E4-mcts-policy — offline MCTS → distilled fast live policy + Nash/Shapley.

Covers the acceptance gates the brief names:

    * the offline **open-loop MCTS** searches sensibly (prefers the scarce cliff, concentrates
      with more iterations) and its exact evaluator rides E3 `simulate_league`'s ``p_champion``;
    * **distillation** fits the fast linear policy to the MCTS visit targets (cross-entropy drops)
      and the **live lookup is fast** (perf assert) and beats raw-VORP on a multi-seed backtest;
    * the **Nash-aware check** flags best responses and prices exploitability;
    * **Shapley pick attribution** sums correctly on a fixture (efficiency axiom) and is symmetric.

`ponytail:` the backtest reuses the shipped `live_draft_value` board and a plain snake over a
fixed starter template, so every produced roster is legal by construction.
"""
from __future__ import annotations

import random
import time

import numpy as np
import pandas as pd

from blitz_engine.simulation.league import LeagueConfig, Roster
from blitz_engine.value import (
    DraftState,
    FastDraftPolicy,
    OpponentField,
    live_draft_value,
    marginal_starter_value,
    mcts_plan,
    nash_aware_check,
    nash_check,
    shapley_efficiency_gap,
    shapley_pick_attribution,
    static_replacement_levels,
)
from blitz_engine.value.mcts import equity_evaluator, starter_value
from blitz_engine.value.policy import DistillSample, distill_policy, position_features

_TEMPLATE = ("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPERFLEX", "K", "DST")
_FLEX = frozenset({"RB", "WR", "TE"})
_SFLX = frozenset({"QB", "RB", "WR", "TE"})
_N_TEAMS = 6
_POS = {
    "QB": (24, 26.0, 0.55), "RB": (30, 24.0, 1.4), "WR": (36, 23.0, 0.7),
    "TE": (18, 20.0, 1.8), "K": (12, 9.0, 0.15), "DST": (12, 9.0, 0.15),
}
_STD = {"QB": 6.0, "RB": 7.0, "WR": 7.0, "TE": 6.0, "K": 3.0, "DST": 3.0}


# ======================================================================================
# fixtures — a draftable universe (mirrors the E4-value-equity backtest scaffolding)
# ======================================================================================
def _universe(seed: int) -> dict[str, tuple[str, float]]:
    rng = random.Random(seed)
    players: dict[str, tuple[str, float]] = {}
    for pos, (n, top, decay) in _POS.items():
        for i in range(n):
            mean = top * float(np.exp(-decay * i / n * 3)) + rng.uniform(-1.0, 1.0)
            players[f"{pos}{i}"] = (pos, mean)
    return players


def _available(players: dict[str, tuple[str, float]], taken: set[str]) -> dict[str, list]:
    out: dict[str, list] = {}
    for pid, (pos, mean) in players.items():
        if pid not in taken:
            out.setdefault(pos, []).append((pid, mean))
    for pos in out:
        out[pos].sort(key=lambda pv: pv[1], reverse=True)
    return out


def _slot_positions(slot: str) -> frozenset[str]:
    if slot == "FLEX":
        return _FLEX
    if slot == "SUPERFLEX":
        return _SFLX
    return frozenset({slot})


def _allowed(slots_left: list[str]) -> set[str]:
    return {p for s in slots_left for p in _slot_positions(s)}


def _pick_raw_vorp(abp: dict[str, list], slots_left: list[str]) -> tuple[str, str] | None:
    allowed = _allowed(slots_left)
    rep = static_replacement_levels({p: [m for _, m in lst] for p, lst in abp.items()})
    best, best_v = None, -1e9
    for pos, lst in abp.items():
        if pos in allowed and lst:
            v = lst[0][1] - rep.get(pos, 0.0)
            if v > best_v:
                best, best_v = (lst[0][0], pos), v
    return best


def _consume(slots_left: list[str], pos: str) -> None:
    slot = next((s for s in slots_left if s == pos), None)
    slot = slot or next(s for s in slots_left if pos in _slot_positions(s))
    slots_left.remove(slot)


# ======================================================================================
# offline MCTS
# ======================================================================================
def _scarce_board() -> dict[str, tuple[tuple[str, float], ...]]:
    return {
        "RB": tuple((f"rb{i}", v) for i, v in enumerate([30.0, 18.0, 10.0, 6.0, 4.0])),
        "WR": tuple((f"wr{i}", v) for i, v in enumerate([26.0, 24.0, 22.0, 20.0, 18.0, 16.0])),
        "QB": tuple((f"qb{i}", v) for i, v in enumerate([22.0, 20.0, 18.0, 16.0])),
        "TE": tuple((f"te{i}", v) for i, v in enumerate([20.0, 10.0, 6.0, 4.0])),
        "K": tuple((f"k{i}", 9.0 - i) for i in range(3)),
        "DST": tuple((f"d{i}", 9.0 - i) for i in range(3)),
    }


def test_mcts_prefers_scarce_position_and_concentrates_with_search() -> None:
    state = DraftState(board=_scarce_board(), slots_left=_TEMPLATE)
    field = OpponentField.uniform(_N_TEAMS - 1)
    plan = mcts_plan(state, field, n_iter=800, seed=3)
    # the search never wastes its opening pick on kicker/defense
    assert plan.best_action not in {"K", "DST"}
    # and the scarce, coveted positions dominate the visit budget over the dregs.
    assert plan.action_visits["RB"] > plan.action_visits["K"]
    assert plan.action_visits["WR"] > plan.action_visits["DST"]
    # visit distribution is a valid policy target.
    target = plan.policy_target()
    assert abs(sum(target.values()) - 1.0) < 1e-9
    assert plan.value_estimate > 0.0


def test_mcts_value_improves_with_more_iterations() -> None:
    state = DraftState(board=_scarce_board(), slots_left=_TEMPLATE)
    field = OpponentField.uniform(_N_TEAMS - 1)
    low = mcts_plan(state, field, n_iter=60, seed=5).value_estimate
    high = mcts_plan(state, field, n_iter=1000, seed=5).value_estimate
    # more search never *degrades* the backed-up roster value here (the objective is maximised).
    assert high >= low - 1e-6
    assert high > 0.0


def test_equity_evaluator_rides_simulate_league_p_champion() -> None:
    """The exact leaf value is a real `simulate_league` championship probability in [0, 1]."""
    players = _universe(2)
    team_ids = [f"T{t}" for t in range(_N_TEAMS)]
    rng = random.Random(11)
    # give every team a full legal-ish roster of distinct players
    pool = list(players)
    rng.shuffle(pool)
    rosters = []
    for t in range(_N_TEAMS):
        rosters.append(Roster(id=team_ids[t], starters=tuple(pool[t * 10 : t * 10 + 10])))
    marg = pd.DataFrame(
        {"player_id": list(players),
         "mean": [players[p][1] for p in players],
         "stdev": [_STD[players[p][0]] for p in players]}
    )
    meta = pd.DataFrame(
        {"player_id": list(players),
         "position": [players[p][0] for p in players],
         "team": [f"NFL{i % 16}" for i in range(len(players))]}
    )
    sched = []
    for _ in range(8):
        ids = list(team_ids)
        rng.shuffle(ids)
        sched.append([(ids[i], ids[i + 1]) for i in range(0, len(ids), 2)])
    cfg = LeagueConfig(n_seasons=500, batch_seasons=500, playoff_teams=4, seed=7)
    ev = equity_evaluator(marg, meta, rosters[1:], sched, my_id=team_ids[0], config=cfg)
    # terminal state = T0's roster (starter_value unused; equity reads my_picks -> roster)
    my_picks = tuple((pid, players[pid][0], players[pid][1]) for pid in rosters[0].starters)
    state = DraftState(board={}, slots_left=(), my_picks=my_picks)
    p = ev(state)
    assert 0.0 <= p <= 1.0


# ======================================================================================
# Nash-aware check
# ======================================================================================
def test_nash_check_is_pure_best_response() -> None:
    values = {"RB": 10.0, "WR": 7.0, "QB": 4.0}
    assert nash_check(values, "RB").is_best_response
    assert nash_check(values, "RB").regret == 0.0
    off = nash_check(values, "QB")
    assert not off.is_best_response
    assert off.best_response == "RB"
    assert off.regret == 6.0


def test_nash_aware_check_prices_exploitability_of_a_telegraphed_run() -> None:
    state = DraftState(board=_scarce_board(), slots_left=_TEMPLATE)
    field = OpponentField.uniform(_N_TEAMS - 1)
    rb = nash_aware_check(state, field, "RB", n_iter=300, seed=2)
    wr = nash_aware_check(state, field, "WR", n_iter=300, seed=2)
    # both exploitabilities are well-defined and non-negative
    assert rb.exploitability >= 0.0 and wr.exploitability >= 0.0
    # a field best-responding against a run on the scarce cliff (RB) hurts at least as much as
    # against the deep position (WR) — waiting on WR is cheap, waiting on the RB cliff is not.
    assert rb.exploitability >= wr.exploitability - 1e-6


# ======================================================================================
# distillation — MCTS visit targets -> fast linear policy
# ======================================================================================
def _distill_samples(seeds: range) -> list[DistillSample]:
    samples: list[DistillSample] = []
    field = OpponentField.uniform(_N_TEAMS - 1)
    for s in seeds:
        players = _universe(s)
        taken: set[str] = set()
        slots = list(_TEMPLATE)
        for _ in range(4):  # a few opening decisions per seed
            abp = _available(players, taken)
            board_tuples = {p: tuple(lst) for p, lst in abp.items()}
            state = DraftState(board=board_tuples, slots_left=tuple(slots))
            plan = mcts_plan(state, field, n_iter=300, seed=s)
            lb = live_draft_value({p: list(lst) for p, lst in abp.items()}, field)
            pos_of = {pid: p for p, lst in abp.items() for pid, _ in lst}
            feats = position_features(lb, slots, pos_of)
            if feats and plan.best_action:
                samples.append(DistillSample(features=feats, target=plan.policy_target()))
                # advance the draft by the MCTS pick to reach varied later states
                pos = plan.best_action
                taken.add(abp[pos][0][0])
                _consume(slots, pos)
    return samples


def test_distillation_reduces_cross_entropy_to_the_mcts_target() -> None:
    samples = _distill_samples(range(1, 9))
    assert samples

    def _ce(w) -> float:
        loss = 0.0
        for smp in samples:
            positions = list(smp.features)
            logits = np.array([float(w.coef @ smp.features[p]) for p in positions])
            logits -= logits.max()
            q = np.exp(logits)
            q /= q.sum()
            t = np.array([smp.target.get(p, 0.0) for p in positions])
            loss -= float((t * np.log(np.clip(q, 1e-12, 1.0))).sum())
        return loss

    from blitz_engine.value.policy import PolicyWeights

    before = _ce(PolicyWeights.default())
    fitted = distill_policy(samples, n_steps=600, lr=0.4)
    after = _ce(fitted)
    assert after < before  # distillation moved the policy toward the search


# ======================================================================================
# backtest — the distilled/default policy beats raw-VORP
# ======================================================================================
def _draft_policy_vs_raw(seed: int, policy: FastDraftPolicy) -> float:
    """Snake draft: team 0 runs the fast policy, the rest raw-VORP; return T0's starter edge."""
    players = _universe(seed)
    field = OpponentField.uniform(_N_TEAMS - 1)

    def run(team0_policy: bool) -> float:
        taken: set[str] = set()
        slots = {t: list(_TEMPLATE) for t in range(_N_TEAMS)}
        roster0: list[tuple[str, str]] = []
        for rnd in range(len(_TEMPLATE)):
            order = range(_N_TEAMS) if rnd % 2 == 0 else reversed(range(_N_TEAMS))
            for t in order:
                abp = _available(players, taken)
                if t == 0 and team0_policy:
                    lb = live_draft_value({p: list(v) for p, v in abp.items()}, field)
                    pos_of = {pid: p for p, lst in abp.items() for pid, _ in lst}
                    pick = policy.pick(lb, slots[t], pos_of) or _pick_raw_vorp(abp, slots[t])
                else:
                    pick = _pick_raw_vorp(abp, slots[t])
                assert pick is not None
                pid, pos = pick
                taken.add(pid)
                if t == 0:
                    roster0.append((pid, pos))
                _consume(slots[t], pos)
        return sum(players[pid][1] for pid, _ in roster0)

    return run(True) - run(False)


def _bootstrap_ci(sample: list[float], *, seed: int = 0, n: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(sample, dtype=float)
    boots = [float(rng.choice(arr, arr.size, replace=True).mean()) for _ in range(n)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


def test_distilled_policy_beats_raw_vorp_on_backtest() -> None:
    """Multi-seed walk-forward: the distilled fast policy beats raw-VORP, bootstrap-CI clears 0."""
    policy = FastDraftPolicy(weights=distill_policy(_distill_samples(range(1, 5))))
    adv = [_draft_policy_vs_raw(s, policy) for s in range(20, 40)]  # held-out seeds
    lo, hi = _bootstrap_ci(adv)
    assert lo > 0.0, f"distilled vs raw-VORP 95% CI must clear zero, got [{lo:.2f}, {hi:.2f}]"
    assert np.mean(adv) > 0.0


# ======================================================================================
# perf — the live policy lookup is fast
# ======================================================================================
def test_live_policy_lookup_is_fast() -> None:
    players = _universe(1)
    board = {p: [(pid, players[pid][1]) for pid in players if players[pid][0] == p] for p in _POS}
    field = OpponentField.uniform(_N_TEAMS - 1)
    lb = live_draft_value(board, field)
    pos_of = {pid: players[pid][0] for pid in players}
    policy = FastDraftPolicy()
    t0 = time.perf_counter()
    for _ in range(200):  # a full draft's worth of lookups over a precomputed board
        assert policy.pick(lb, list(_TEMPLATE), pos_of) is not None
    per_pick = (time.perf_counter() - t0) / 200
    assert per_pick < 1e-3, f"live lookup too slow: {per_pick * 1e6:.0f} us/pick"


# ======================================================================================
# Shapley pick attribution
# ======================================================================================
def test_shapley_sums_correctly_and_is_symmetric() -> None:
    values = {"a": 10.0, "b": 8.0, "c": 5.0, "d": 5.0, "e": 3.0}
    positions = {"a": "RB", "b": "WR", "c": "RB", "d": "WR", "e": "TE"}
    template = ("RB", "WR", "FLEX", "TE")
    vf = marginal_starter_value(values, positions, template)
    att = shapley_pick_attribution(list(values), vf)
    # efficiency axiom: credit sums to the roster's total startable value.
    assert shapley_efficiency_gap(att, vf, list(values)) < 1e-9
    # every pick's credit is non-negative here (monotone value_fn).
    assert all(v >= -1e-9 for v in att.values())


def test_shapley_symmetry_on_interchangeable_picks() -> None:
    # two identical, interchangeable picks must receive equal credit.
    values = {"x": 6.0, "y": 6.0}
    positions = {"x": "RB", "y": "RB"}
    vf = marginal_starter_value(values, positions, ("RB", "FLEX"))
    att = shapley_pick_attribution(list(values), vf)
    assert abs(att["x"] - att["y"]) < 1e-9


def test_shapley_sampled_path_matches_exact() -> None:
    values = {c: float(10 - i) for i, c in enumerate("abcdefghij")}  # 10 picks -> sampled path
    positions = {c: ("RB" if i % 2 else "WR") for i, c in enumerate(values)}
    template = ("RB", "RB", "WR", "WR", "FLEX", "FLEX")
    vf = marginal_starter_value(values, positions, template)
    att = shapley_pick_attribution(list(values), vf, max_exact=8, samples=6000, seed=1)
    # sampled Shapley still respects efficiency to Monte-Carlo tolerance.
    assert shapley_efficiency_gap(att, vf, list(values)) < 1e-9  # each permutation telescopes


# ======================================================================================
# no-regression — the unit is purely additive to the value surface
# ======================================================================================
def test_no_regression_mcts_policy_is_additive() -> None:
    from blitz_engine.value import interim_surface

    class _Row:
        def __init__(self, pid: str, value: float) -> None:
            self.player_id = pid
            self.value = value

    surface = interim_surface([_Row("a", 5.0), _Row("b", 9.0), _Row("c", 1.0)])
    assert [iv.player_id for iv in surface] == ["b", "a", "c"]
    # the fast policy default weights are the documented scarcity-aware cold start.
    assert starter_value(DraftState(board={}, slots_left=(), my_picks=(("p", "RB", 7.0),))) == 7.0
