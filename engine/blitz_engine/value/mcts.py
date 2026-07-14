"""Offline MCTS over the season sim → an equity-scored draft plan (+ a Nash-aware check).

The live draft room must be cheap (`value.live_draft_value` is O(board) per pick), but a
*greedy* live board is myopic: it never reasons "if I pass this RB now, the field's run leaves
me the WR I actually wanted anyway". That look-ahead is a **search** problem, and search is
expensive — so we run it **offline** and distill the result into the fast live policy
(`policy.py`).

This module is that offline search. It is an **open-loop MCTS** over the draft MDP:

* a *decision* is which **position** I draft next (value-greedy within the position — take its
  best remaining player), so the branching factor is ≤ 6, not the whole board;
* between my turns the **opponent field** (`opponent.py`) depletes the board stochastically —
  each intervening pick samples a position from that GM's archetype mixture and removes its best
  remaining player. That randomness is *re-sampled every simulation* (open-loop), so the tree
  averages over the field instead of pretending the board is deterministic;
* a leaf roster is scored by an **equity evaluator**. The cheap default is scarcity-summed
  starter value; the exact, sim-priced one (`equity_evaluator`) re-uses E3 `simulate_league`'s
  ``p_champion`` — the same championship-equity objective the live proxy is calibrated to.

`ponytail:` open-loop MCTS folds the opponent stochasticity into the return, so the tree is keyed
only by *my* action history — no chance nodes, no belief-state cloning. The rollout and the
default leaf value both reuse the shipped scarcity math (`replacement`/`vona`), and the exact
evaluator is one `simulate_league` call. The Nash check is a pure function over the root's own
action values. Snake / superflex-half-PPR first.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from blitz_engine.simulation.league import LeagueConfig, Roster, simulate_league
from blitz_engine.value.opponent import OpponentField, TeamState
from blitz_engine.value.replacement import static_replacement_levels

# Default starter template for a superflex, half-PPR league (the format this unit targets).
SUPERFLEX_TEMPLATE: tuple[str, ...] = (
    "QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPERFLEX", "K", "DST",
)
_FLEX: frozenset[str] = frozenset({"RB", "WR", "TE"})
_SUPERFLEX: frozenset[str] = frozenset({"QB", "RB", "WR", "TE"})


def slot_positions(slot: str) -> frozenset[str]:
    """The set of positions a template slot accepts (FLEX/SUPERFLEX widen it)."""
    if slot == "FLEX":
        return _FLEX
    if slot == "SUPERFLEX":
        return _SUPERFLEX
    return frozenset({slot})


# A player on the board: (player_id, value in points·week⁻¹) — value units match E4-value-equity.
Candidate = tuple[str, float]
Pick = tuple[str, str, float]  # (player_id, position, value) placed on my roster


@dataclass(frozen=True)
class DraftState:
    """An open-loop draft node: the board, my remaining slots, and my picks so far.

    ``board`` maps position → its available ``(player_id, value)`` sorted **descending**. Only
    *my* decisions are represented; the opponent field's depletion is applied stochastically by
    `step` and re-sampled each simulation, so a state is cheap to branch (copy-on-write per
    position). Terminal when every starter slot is filled.
    """

    board: Mapping[str, tuple[Candidate, ...]]
    slots_left: tuple[str, ...]
    my_picks: tuple[Pick, ...] = ()

    def terminal(self) -> bool:
        """True once no starter slots remain to fill."""
        return not self.slots_left

    def legal_actions(self) -> list[str]:
        """Positions I can legally draft now: some open slot accepts them and the board has one."""
        open_positions = {p for s in self.slots_left for p in slot_positions(s)}
        return sorted(pos for pos in open_positions if self.board.get(pos))

    def _consume_slot(self, position: str) -> tuple[str, ...]:
        """Drop the most specific open slot that accepts ``position`` (keep flex slots free)."""
        exact = next((s for s in self.slots_left if s == position), None)
        slot = exact or next(s for s in self.slots_left if position in slot_positions(s))
        rest = list(self.slots_left)
        rest.remove(slot)
        return tuple(rest)

    def step(
        self,
        position: str,
        opponent_field: OpponentField,
        rng: np.random.Generator,
        *,
        opponent_counts: Sequence[TeamState] | None = None,
    ) -> DraftState:
        """Draft ``position`` (its best remaining player), then let the field deplete the board.

        The opponent depletion samples one position per intervening GM from
        `OpponentField.pick_position_sequence` and removes that position's current best — a
        value-greedy field, matching the scarcity assumptions in `vona`/`replacement`.
        """
        pid, val = self.board[position][0]
        new_board = _remove_top(self.board, position)
        my_picks = (*self.my_picks, (pid, position, val))
        slots_left = self._consume_slot(position)

        # Stochastic opponent depletion between my turns (open-loop: fresh sample each sim).
        top = {p: lst[0][1] for p, lst in new_board.items() if lst}
        for probs in opponent_field.pick_position_sequence(top, opponent_counts):
            opp_pos = _sample_position(probs, rng)
            if opp_pos is not None and new_board.get(opp_pos):
                new_board = _remove_top(new_board, opp_pos)
                top = {p: lst[0][1] for p, lst in new_board.items() if lst}
        return replace(self, board=new_board, slots_left=slots_left, my_picks=my_picks)


def _remove_top(
    board: Mapping[str, tuple[Candidate, ...]], position: str
) -> dict[str, tuple[Candidate, ...]]:
    """Copy-on-write: return ``board`` with ``position``'s best player removed."""
    out = dict(board)
    out[position] = board[position][1:]
    return out


def _sample_position(probs: Mapping[str, float], rng: np.random.Generator) -> str | None:
    """Draw a position from a (possibly unnormalised) P(position) map; None if it's empty/zero."""
    items = [(p, max(0.0, float(w))) for p, w in probs.items()]
    total = sum(w for _, w in items)
    if total <= 0.0:
        return None
    r = rng.random() * total
    acc = 0.0
    for pos, w in items:
        acc += w
        if r <= acc:
            return pos
    return items[-1][0]


# --- leaf evaluators (the "equity score") --------------------------------------------------
Evaluator = Callable[[DraftState], float]


def starter_value(state: DraftState) -> float:
    """Cheap leaf value: total points·week⁻¹ of the roster I built (the fast equity proxy)."""
    return float(sum(v for _, _, v in state.my_picks))


def equity_evaluator(
    marginals: pd.DataFrame,
    players: pd.DataFrame,
    opponent_rosters: Sequence[Roster],
    schedule: Sequence[Sequence[tuple[str, str]]],
    *,
    my_id: str = "ME",
    config: LeagueConfig | None = None,
) -> Evaluator:
    """Exact, sim-priced leaf value: my roster's ``p_champion`` from E3 `simulate_league`.

    Builds ``my_id``'s roster from the terminal state's picks, drops it into the fixed opponent
    field, and returns championship probability — the true equity objective the live proxy is
    calibrated against. One sim per leaf, so use small ``config.n_seasons`` offline.
    """
    cfg = config or LeagueConfig()

    def _eval(state: DraftState) -> float:
        mine = Roster(id=my_id, starters=tuple(pid for pid, _, _ in state.my_picks))
        rosters = [mine, *opponent_rosters]
        res = simulate_league(marginals, players, rosters, schedule, config=cfg)
        return float(res.p_champion().get(my_id, 0.0))

    return _eval


# --- rollout policy (default-fast, used from a leaf to a terminal roster) -------------------
RolloutPolicy = Callable[[DraftState], str]


def greedy_vorp_rollout(state: DraftState) -> str:
    """Default rollout: draft the legal position whose best player most beats static replacement.

    A cheap, scarcity-aware default (reuses `static_replacement_levels`) — good enough to give
    the search an informative return without a nested board recompute per rollout step.
    """
    legal = state.legal_actions()
    values_by_pos = {pos: [v for _, v in state.board.get(pos, ())] for pos in legal}
    rep = static_replacement_levels(values_by_pos)
    return max(legal, key=lambda pos: state.board[pos][0][1] - rep.get(pos, 0.0))


# --- the tree ------------------------------------------------------------------------------
@dataclass
class _Node:
    """One open-loop MCTS node: visit count, summed leaf value, and children by my action."""

    n: int = 0
    w: float = 0.0
    children: dict[str, _Node] = field(default_factory=dict)

    @property
    def value(self) -> float:
        return self.w / self.n if self.n else 0.0


@dataclass(frozen=True)
class MctsPlan:
    """The offline search result at a decision point.

    ``action_visits`` is the raw visit count per first-position (the distillation target);
    ``action_values`` is each first-position's mean terminal equity; ``best_action`` maximises
    visits (the robust-child choice); ``value_estimate`` is the root's backed-up value.
    """

    action_visits: dict[str, int]
    action_values: dict[str, float]
    best_action: str | None
    value_estimate: float

    def policy_target(self) -> dict[str, float]:
        """Visit distribution over first-positions — the soft target `policy.py` distills."""
        total = sum(self.action_visits.values()) or 1
        return {a: n / total for a, n in self.action_visits.items()}


def _uct_select(
    node: _Node, legal: Sequence[str], c: float, vmin: float, vmax: float
) -> str:
    """Pick the child maximising UCB1 among currently-legal actions.

    Q-values are min-max normalised to ``[0, 1]`` using the tree's observed value range so the
    exploration constant is meaningful regardless of the evaluator's scale (raw starter value in
    the tens, ``p_champion`` in ``[0, 1]``) — MuZero's normalisation trick.
    """
    log_n = math.log(node.n + 1)
    span = vmax - vmin

    def score(a: str) -> float:
        child = node.children[a]
        if child.n == 0:
            return math.inf
        q = (child.value - vmin) / span if span > 0 else 0.5
        return q + c * math.sqrt(log_n / child.n)

    return max(legal, key=score)


def mcts_plan(
    root: DraftState,
    opponent_field: OpponentField,
    *,
    evaluator: Evaluator = starter_value,
    rollout: RolloutPolicy = greedy_vorp_rollout,
    n_iter: int = 400,
    c_uct: float = 1.4,
    opponent_counts: Sequence[TeamState] | None = None,
    seed: int = 0,
) -> MctsPlan:
    """Run open-loop MCTS from ``root`` and return the equity-scored plan (offline entry point).

    Each of ``n_iter`` simulations descends the tree by UCT over *my* positions, applies my pick
    plus a freshly-sampled opponent depletion at every step, expands one new node, rolls out with
    ``rollout`` to a terminal roster, and backs up ``evaluator``'s equity score. The default
    evaluator is the fast starter-value proxy; pass `equity_evaluator` for the exact sim-priced
    objective. Returns visit counts (the distillation target) + per-action equity values.
    """
    rng = np.random.default_rng(seed)
    tree = _Node()
    vmin, vmax = math.inf, -math.inf
    for _ in range(n_iter):
        state = root
        node = tree
        path = [tree]
        # selection + one expansion
        while not state.terminal():
            legal = state.legal_actions()
            if not legal:
                break
            untried = [a for a in legal if a not in node.children]
            if untried:
                action = str(rng.choice(untried))
                child = _Node()
                node.children[action] = child
                state = state.step(action, opponent_field, rng, opponent_counts=opponent_counts)
                node = child
                path.append(node)
                break
            action = _uct_select(node, legal, c_uct, vmin, vmax)
            state = state.step(action, opponent_field, rng, opponent_counts=opponent_counts)
            node = node.children[action]
            path.append(node)
        # rollout to a terminal roster with the fast default policy
        while not state.terminal() and state.legal_actions():
            state = state.step(
                rollout(state), opponent_field, rng, opponent_counts=opponent_counts
            )
        value = evaluator(state)
        vmin, vmax = min(vmin, value), max(vmax, value)
        for nd in path:
            nd.n += 1
            nd.w += value

    visits = {a: child.n for a, child in tree.children.items()}
    values = {a: child.value for a, child in tree.children.items()}
    best = max(visits, key=lambda a: visits[a]) if visits else None
    return MctsPlan(
        action_visits=visits,
        action_values=values,
        best_action=best,
        value_estimate=tree.value,
    )


# --- Nash-aware check ----------------------------------------------------------------------
@dataclass(frozen=True)
class NashCheck:
    """Is my pick a best response to the opponent field, and how exploitable is it?

    ``regret`` = value of the best first-action minus the chosen action's (≥ 0);
    ``is_best_response`` is ``regret <= tol``. ``exploitability`` (optional) is how much equity a
    field that *best-responds against my chosen position* (hammers its run) strips versus the
    nominal mixed field — small means the pick is equilibrium-robust, not a scarcity gamble.
    """

    chosen: str
    best_response: str
    regret: float
    is_best_response: bool
    exploitability: float = 0.0


def nash_check(
    action_values: Mapping[str, float], chosen: str, *, tol: float = 1e-9
) -> NashCheck:
    """Pure best-response test over precomputed first-action equity values (from `mcts_plan`)."""
    if not action_values:
        return NashCheck(chosen, chosen, 0.0, True)
    best = max(action_values, key=lambda a: action_values[a])
    regret = float(action_values[best] - action_values.get(chosen, action_values[best]))
    return NashCheck(
        chosen=chosen,
        best_response=best,
        regret=max(0.0, regret),
        is_best_response=regret <= tol,
    )


def nash_aware_check(
    root: DraftState,
    opponent_field: OpponentField,
    chosen: str,
    *,
    evaluator: Evaluator = starter_value,
    rollout: RolloutPolicy = greedy_vorp_rollout,
    n_iter: int = 400,
    c_uct: float = 1.4,
    seed: int = 0,
    tol: float = 1e-9,
) -> NashCheck:
    """Full Nash check: search for the best response, then price how exploitable ``chosen`` is.

    Exploitability compares the chosen action's equity under the nominal field against a field
    that *adversarially runs the chosen position* (every intervening GM targets it), i.e. the
    field's best response to my telegraphing that pick. A pick that survives the adversarial run
    is Nash-robust; one that collapses was banking on the field cooperating.
    """
    plan = mcts_plan(
        root, opponent_field, evaluator=evaluator, rollout=rollout,
        n_iter=n_iter, c_uct=c_uct, seed=seed,
    )
    base = nash_check(plan.action_values, chosen, tol=tol)
    nominal = plan.action_values.get(chosen, 0.0)

    adversary = _adversarial_field(opponent_field, chosen)
    adv_plan = mcts_plan(
        root, adversary, evaluator=evaluator, rollout=rollout,
        n_iter=n_iter, c_uct=c_uct, seed=seed + 1,
    )
    adv_value = adv_plan.action_values.get(chosen, nominal)
    return replace(base, exploitability=max(0.0, nominal - adv_value))


@dataclass
class _AdversarialModel:
    """A degenerate opponent that always drafts one target position (the field's best response)."""

    target: str

    def pick_position_probs(
        self, top_value_by_pos: Mapping[str, float], _team_counts: TeamState
    ) -> dict[str, float]:
        if self.target in top_value_by_pos:
            return {self.target: 1.0}
        return dict.fromkeys(top_value_by_pos, 1.0)  # target gone → don't distort the board


def _adversarial_field(field_: OpponentField, target: str) -> OpponentField:
    """A same-sized field where every GM hammers ``target`` — the exploiter of a telegraph."""
    models = [_AdversarialModel(target) for _ in field_.models]
    return OpponentField(models=models)  # type: ignore[arg-type]
