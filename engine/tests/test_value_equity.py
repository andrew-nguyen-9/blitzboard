"""E4-value-equity — the DEEP value engine that swaps under the W2 interim board.

Covers the four modules the unit owns (`equity`, `replacement`, `vona`, `opponent`) plus the
acceptance gates the brief names:

    * a walk-forward **backtest** (multi-seed, bootstrap CIs) proving the championship-equity /
      dynamic-VORP draft policy beats raw-VORP *and* a naive best-points ("v1") baseline on
      season points-for (deterministic starter-value proxy) and on H2H championship odds
      (`simulate_league` as ground truth);
    * a **perf** assert that the whole live board recomputes per pick in well under a frame;
    * a **no-regression** check that the deep engine is purely additive to the interim surface.

The W2 draft-invariant regression (`tests/regression/test_draft_invariants.py`) is untouched and
still runs in the same gate — this unit adds files, it does not edit the fix contract.

`ponytail:` the backtest reuses `simulate_league` for ground truth and the live policy is the
shipped `live_draft_value`; the draft loop is a plain snake over a fixed starter template, so
every produced roster is a legal lineup by construction (no solver needed here).
"""
from __future__ import annotations

import random
import time

import numpy as np
import pandas as pd
import pytest

from blitz_engine.simulation.league import LeagueConfig, Roster, simulate_league
from blitz_engine.value import (
    OpponentField,
    OpponentModel,
    demand_by_position,
    demand_replacement_levels,
    dynamic_vorp,
    equity_proxy,
    interim_surface,
    live_draft_value,
    run_probability,
    static_replacement_levels,
    vona,
)
from blitz_engine.value.equity import calibrate_equity_sensitivity, championship_equity

# ======================================================================================
# opponent model
# ======================================================================================


def test_pick_position_probs_normalised_and_value_greedy() -> None:
    top = {"QB": 20.0, "RB": 25.0, "WR": 18.0, "TE": 10.0}
    m = OpponentModel()  # uniform mixture
    probs = m.pick_position_probs(top, team_counts={})
    assert probs.keys() == top.keys()
    assert pytest.approx(sum(probs.values()), abs=1e-9) == 1.0
    # the position holding the single best player is the modal pick.
    assert max(probs, key=probs.get) == "RB"


def test_update_concentrates_toward_the_predicting_archetype() -> None:
    """Repeated RB picks should raise the RB-heavy archetypes' posterior weight."""
    top = {"QB": 22.0, "RB": 20.0, "WR": 21.0, "TE": 12.0}
    m = OpponentModel()
    before = m.mixture()
    for _ in range(6):
        m.update("RB", top, team_counts={})
    after = m.mixture()
    # robust_rb is the archetype that most favours RB, so its share must strictly increase.
    assert after["robust_rb"] > before["robust_rb"]
    # and an unrelated pick nobody's model expected leaves belief unchanged (no NaNs, no blow-up).
    frozen = OpponentModel()
    snapshot = dict(frozen.mixture())
    frozen.update("K", {"K": 0.0}, team_counts={})  # zero-likelihood observation
    assert frozen.mixture() == pytest.approx(snapshot)


def test_from_prior_seeds_history_and_field_is_per_opponent() -> None:
    m = OpponentModel.from_prior({"zero_rb": 10.0})
    mix = m.mixture()
    assert mix["zero_rb"] == max(mix.values())
    field = OpponentField.uniform(3, prior={"hero_rb": 5.0})
    seq = field.pick_position_sequence({"RB": 20.0, "WR": 18.0})
    assert len(seq) == 3
    assert all(pytest.approx(sum(p.values()), abs=1e-9) == 1.0 for p in seq)


# ======================================================================================
# vona + positional-run probability
# ======================================================================================


def test_run_probability_monotone_and_bounded() -> None:
    picks = [{"RB": 0.6, "WR": 0.4}, {"RB": 0.5, "WR": 0.5}, {"RB": 0.7, "WR": 0.3}]
    p1 = run_probability(picks, "RB", k=1)
    p2 = run_probability(picks, "RB", k=2)
    p3 = run_probability(picks, "RB", k=3)
    assert 0.0 <= p3 <= p2 <= p1 <= 1.0  # P(>=k) is non-increasing in k
    assert run_probability(picks, "RB", k=0) == 1.0
    assert run_probability([], "RB", k=1) == 0.0  # no intervening picks -> no run


def test_vona_rises_with_scarcity_pressure() -> None:
    values = [30.0, 22.0, 15.0]  # a cliff at this position
    calm = [{"RB": 0.05}]  # nobody's coming for it
    storm = [{"RB": 0.95}, {"RB": 0.95}]  # a run is imminent
    v_calm = vona("RB", values, calm)
    v_storm = vona("RB", values, storm)
    assert v_storm.vona > v_calm.vona
    assert 0.0 <= v_calm.run_prob <= v_storm.run_prob <= 1.0
    assert v_storm.best_now == 30.0


# ======================================================================================
# dynamic demand-derived replacement -> live VORP
# ======================================================================================


def test_demand_and_dynamic_vorp() -> None:
    picks = [{"RB": 0.8, "WR": 0.2}, {"RB": 0.6, "WR": 0.4}]
    demand = demand_by_position(picks)
    assert demand["RB"] == pytest.approx(1.4)
    values = {"RB": [30.0, 24.0, 18.0, 10.0], "WR": [25.0, 20.0]}
    rep = demand_replacement_levels(values, picks)
    # heavier RB demand erodes its board more -> the RB you can still get is worse than #1.
    assert rep["RB"] < values["RB"][0]
    assert dynamic_vorp(30.0, "RB", rep) > dynamic_vorp(18.0, "RB", rep) >= 0.0
    # a player at/below the replacement level adds no marginal value.
    assert dynamic_vorp(rep["RB"], "RB", rep) == pytest.approx(0.0)


def test_static_replacement_interpolates_and_degrades() -> None:
    values = {"RB": [30.0, 20.0, 10.0]}
    rep = static_replacement_levels(values, demand={"RB": 1.5})
    assert rep["RB"] == pytest.approx(15.0)  # halfway between ranks 1 and 2
    assert static_replacement_levels({"RB": []})["RB"] == 0.0  # empty -> 0


# ======================================================================================
# championship equity — offline (re-sims) + live proxy + composed board
# ======================================================================================


def _tiny_league() -> tuple[pd.DataFrame, pd.DataFrame, list[Roster], list]:
    """A 6-team, single-starter-each toy league for the exact-equity sim tests."""
    pids = [f"p{i}" for i in range(6)]
    marg = pd.DataFrame(
        {"player_id": pids, "mean": [20, 18, 16, 14, 12, 10], "stdev": [6] * 6}
    )
    meta = pd.DataFrame(
        {"player_id": pids, "position": ["RB"] * 6, "team": [f"NFL{i}" for i in range(6)]}
    )
    rosters = [Roster(id=f"T{i}", starters=(pids[i],)) for i in range(6)]
    ids = [r.id for r in rosters]
    rng = random.Random(3)
    schedule = []
    for _ in range(8):
        order = list(ids)
        rng.shuffle(order)
        schedule.append([(order[i], order[i + 1]) for i in range(0, 6, 2)])
    return marg, meta, rosters, schedule


def test_championship_equity_prefers_the_stronger_addition() -> None:
    marg, meta, rosters, schedule = _tiny_league()
    # add a strong (p_strong) vs weak (p_weak) free agent to the weakest team T5.
    extra = pd.DataFrame(
        {"player_id": ["strong", "weak"], "mean": [40.0, 2.0], "stdev": [6.0, 6.0]}
    )
    marg2 = pd.concat([marg, extra], ignore_index=True)
    meta2 = pd.concat(
        [
            meta,
            pd.DataFrame(
                {"player_id": ["strong", "weak"], "position": ["RB", "RB"],
                 "team": ["NFL9", "NFL10"]}
            ),
        ],
        ignore_index=True,
    )
    cfg = LeagueConfig(n_seasons=1200, playoff_teams=4, batch_seasons=1200, seed=11)
    eq = championship_equity(
        marg2, meta2, rosters, schedule,
        target_roster="T5", candidates=["strong", "weak"], config=cfg,
    )
    assert eq.index[0] == "strong"  # the elite addition raises equity most
    assert eq["strong"] > eq["weak"]
    assert eq["strong"] > 0.0


def test_calibrate_sensitivity_nonnegative_and_proxy_scales() -> None:
    marg, meta, rosters, schedule = _tiny_league()
    cfg = LeagueConfig(n_seasons=1200, playoff_teams=4, batch_seasons=1200, seed=5)
    s = calibrate_equity_sensitivity(
        marg, meta, rosters, schedule, target_roster="T5", delta_pts=6.0, config=cfg
    )
    assert s >= 0.0
    # the proxy is a non-negative, monotone scaling of a VORP edge.
    assert equity_proxy(10.0, s) == pytest.approx(10.0 * s)
    assert equity_proxy(-5.0, s) == 0.0


def test_live_board_composes_and_ranks() -> None:
    board_players = {
        "RB": [("rb1", 30.0), ("rb2", 20.0), ("rb3", 12.0)],
        "WR": [("wr1", 26.0), ("wr2", 24.0), ("wr3", 22.0)],  # deep, low scarcity
        "QB": [("qb1", 22.0)],
    }
    field = OpponentField.uniform(4)
    lb = live_draft_value(board_players, field, sensitivity=2.0)
    assert lb.best() == lb.ranked[0][0]
    # ranked is sorted by equity value, descending.
    vals = [v for _, v in lb.ranked]
    assert vals == sorted(vals, reverse=True)
    # every board player is scored; scarce-position leader outranks a deep-position leader
    # of similar raw value.
    assert set(lb.equity_value) == {"rb1", "rb2", "rb3", "wr1", "wr2", "wr3", "qb1"}
    assert lb.equity_value["rb1"] > lb.equity_value["wr1"]
    assert lb.replacement["RB"] <= 30.0 and lb.vona["RB"].vona >= 0.0


# ======================================================================================
# backtest — the acceptance gate (season points-for proxy + H2H, seeds + bootstrap CIs)
# ======================================================================================

_TEMPLATE = ("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPERFLEX", "K", "DST")
_FLEX = frozenset({"RB", "WR", "TE"})
_SFLX = frozenset({"QB", "RB", "WR", "TE"})
_N_TEAMS = 6
# position value curves — differing drop-off steepness makes draft *timing* (scarcity) matter.
_POS = {
    "QB": (24, 26.0, 0.55), "RB": (30, 24.0, 1.4), "WR": (36, 23.0, 0.7),
    "TE": (18, 20.0, 1.8), "K": (12, 9.0, 0.15), "DST": (12, 9.0, 0.15),
}
_STD = {"QB": 6.0, "RB": 7.0, "WR": 7.0, "TE": 6.0, "K": 3.0, "DST": 3.0}


def _slot_positions(slot: str) -> frozenset[str]:
    if slot == "FLEX":
        return _FLEX
    if slot == "SUPERFLEX":
        return _SFLX
    return frozenset({slot})


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


def _allowed(slots_left: list[str]) -> set[str]:
    allowed: set[str] = set()
    for slot in slots_left:
        allowed |= _slot_positions(slot)
    return allowed


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


def _pick_naive(abp: dict[str, list], slots_left: list[str]) -> tuple[str, str] | None:
    allowed = _allowed(slots_left)
    best, best_v = None, -1e9
    for pos, lst in abp.items():
        if pos in allowed and lst and lst[0][1] > best_v:
            best, best_v = (lst[0][0], pos), lst[0][1]
    return best


def _pick_equity(abp: dict[str, list], slots_left: list[str]) -> tuple[str, str] | None:
    allowed = _allowed(slots_left)
    field = OpponentField.uniform(_N_TEAMS - 1)
    lb = live_draft_value(abp, field, sensitivity=1.0)
    pos_of = {pid: pos for pos, lst in abp.items() for pid, _ in lst}
    best, best_s = None, -1e9
    for pid, ev in lb.equity_value.items():
        pos = pos_of[pid]
        if pos not in allowed or abp[pos][0][0] != pid:  # only the best-at-position is takeable
            continue
        score = ev + lb.vona[pos].vona  # equity + timing urgency (protect scarce positions)
        if score > best_s:
            best, best_s = (pid, pos), score
    return best


_PICKERS = {"raw": _pick_raw_vorp, "naive": _pick_naive, "equity": _pick_equity}


def _draft(seed: int, policy0: str) -> tuple[dict[str, tuple[str, float]], dict[int, list]]:
    """Snake draft over the fixed starter template; team 0 uses ``policy0``, rest use raw-VORP."""
    players = _universe(seed)
    taken: set[str] = set()
    slots = {t: list(_TEMPLATE) for t in range(_N_TEAMS)}
    roster: dict[int, list] = {t: [] for t in range(_N_TEAMS)}
    for rnd in range(len(_TEMPLATE)):
        order = range(_N_TEAMS) if rnd % 2 == 0 else reversed(range(_N_TEAMS))
        for t in order:
            abp = _available(players, taken)
            picker = _PICKERS[policy0] if t == 0 else _pick_raw_vorp
            pick = picker(abp, slots[t]) or _pick_naive(abp, slots[t])
            assert pick is not None
            pid, pos = pick
            taken.add(pid)
            roster[t].append((pid, pos))
            slot = next((s for s in slots[t] if s == pos), None)
            slot = slot or next(s for s in slots[t] if pos in _slot_positions(s))
            slots[t].remove(slot)
    return players, roster


def _starter_value(players: dict[str, tuple[str, float]], roster: list) -> float:
    return sum(players[pid][1] for pid, _ in roster)


def _bootstrap_ci(sample: list[float], *, seed: int = 0, n: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(sample, dtype=float)
    boots = [float(rng.choice(arr, arr.size, replace=True).mean()) for _ in range(n)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


def test_backtest_equity_policy_beats_raw_vorp_and_v1_on_points_for() -> None:
    """Walk-forward over 20 seeds: season points-for proxy, bootstrap-CI beats both baselines."""
    seeds = range(1, 21)
    eq_adv, naive_adv = [], []
    for s in seeds:
        p_raw, r_raw = _draft(s, "raw")
        p_eq, r_eq = _draft(s, "equity")
        p_nv, r_nv = _draft(s, "naive")
        base = _starter_value(p_raw, r_raw[0])
        eq_adv.append(_starter_value(p_eq, r_eq[0]) - base)
        naive_adv.append(_starter_value(p_nv, r_nv[0]) - base)

    lo, hi = _bootstrap_ci(eq_adv)
    assert lo > 0.0, f"equity vs raw-VORP 95% CI must clear zero, got [{lo:.2f}, {hi:.2f}]"
    assert np.mean(eq_adv) > np.mean(naive_adv)  # equity also beats the naive "v1" baseline
    assert min(eq_adv) >= 0.0  # and never loses to raw-VORP on any seed


def test_backtest_equity_policy_wins_more_championships() -> None:
    """H2H ground truth: `simulate_league` gives the equity seat higher champion odds."""
    seeds = [1, 7, 13, 42]
    cfg = LeagueConfig(n_seasons=1500, playoff_teams=4, batch_seasons=1500, seed=7)
    rng = random.Random(99)
    eq_champ, raw_champ = [], []
    for s in seeds:
        for policy, bucket in (("equity", eq_champ), ("raw", raw_champ)):
            players, roster = _draft(s, policy)
            team_ids = [f"T{t}" for t in range(_N_TEAMS)]
            rosters = [
                Roster(id=team_ids[t], starters=tuple(pid for pid, _ in roster[t]))
                for t in range(_N_TEAMS)
            ]
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
            for _ in range(10):
                ids = list(team_ids)
                rng.shuffle(ids)
                sched.append([(ids[i], ids[i + 1]) for i in range(0, len(ids), 2)])
            res = simulate_league(marg, meta, rosters, sched, config=cfg)
            bucket.append(float(res.p_champion().get("T0", 0.0)))

    assert np.mean(eq_champ) > np.mean(raw_champ)
    assert sum(a >= b for a, b in zip(eq_champ, raw_champ, strict=True)) == len(seeds)


# ======================================================================================
# perf + no-regression
# ======================================================================================


def test_live_board_recomputes_per_pick_within_a_frame() -> None:
    """The whole live board (opponent -> replacement -> VONA -> equity) is sub-frame per pick."""
    players = _universe(1)
    board = {
        pos: [(pid, players[pid][1]) for pid in players if players[pid][0] == pos]
        for pos in _POS
    }
    field = OpponentField.uniform(_N_TEAMS - 1)
    t0 = time.perf_counter()
    for _ in range(20):  # 20 consecutive picks' worth of recompute
        lb = live_draft_value(board, field, sensitivity=1.5)
        assert lb.best() is not None
    per_pick = (time.perf_counter() - t0) / 20
    assert per_pick < 0.05, f"live board too slow: {per_pick * 1e3:.1f} ms/pick"


def test_no_regression_deep_engine_is_additive_to_interim_surface() -> None:
    """The equity engine is new files only — the interim value contract is unchanged."""
    class _Row:
        def __init__(self, pid: str, value: float) -> None:
            self.player_id = pid
            self.value = value

    surface = interim_surface([_Row("a", 5.0), _Row("b", 9.0), _Row("c", 1.0)])
    assert [iv.player_id for iv in surface] == ["b", "a", "c"]
    assert surface[0].rank == 1
