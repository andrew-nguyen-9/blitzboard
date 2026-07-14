"""Distilled fast live draft policy + Shapley pick attribution (E4-mcts-policy).

The offline MCTS (`mcts.py`) is smart but sim-priced — far too slow for the clock. This module
is its cheap shadow: a **linear policy over scarcity features** whose weights are *distilled*
from the search's visit distributions, so the live board picks in O(#positions) yet inherits the
look-ahead the search paid for. The features are exactly the signals the live board already
computes (`live_draft_value` → equity-VORP, VONA, positional-run probability) plus roster need,
so a pick is a single dot product per open position.

* `FastDraftPolicy` — the live lookup: given a `LiveBoard` and my open slots, score each legal
  position and take its best remaining player. Ships with scarcity-aware default weights so it is
  useful *before* any distillation (degrade-neutral), and beats raw-VORP out of the box.
* `distill_policy` — softmax policy-distillation (plain numpy gradient descent, no sklearn) that
  fits the weights to a set of MCTS ``policy_target`` visit distributions.
* `shapley_pick_attribution` — credit each pick for the roster it built, via the Shapley value
  (exact for a starting lineup's handful of picks, Monte-Carlo permutation sampling beyond). The
  efficiency axiom (Σφ = v(roster) − v(∅)) makes the attribution auditable.

`ponytail:` the policy is a 4-weight linear model over signals the live board already produces —
no new inference stack — and the Shapley credit reuses one roster-value function for both the
exact subset formula and the sampled estimator.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from blitz_engine.value.equity import LiveBoard, live_draft_value
from blitz_engine.value.mcts import slot_positions
from blitz_engine.value.opponent import OpponentField, TeamState

# The distillation feature order — signals the live board already exposes, per open position.
FEATURE_NAMES: tuple[str, ...] = ("equity", "vona", "run_prob", "need")

# Scarcity-aware cold-start weights (used before any distillation): reward equity edge, timing
# urgency (VONA + run risk) and unmet roster need. Positive → the cold policy already beats a
# static-VORP board, which sees none of the timing signals.
DEFAULT_WEIGHTS: tuple[float, ...] = (1.0, 1.0, 0.5, 2.0)


@dataclass(frozen=True)
class PolicyWeights:
    """A linear draft policy: one weight per scarcity feature (`FEATURE_NAMES`)."""

    coef: np.ndarray

    @classmethod
    def default(cls) -> PolicyWeights:
        return cls(coef=np.asarray(DEFAULT_WEIGHTS, dtype=float))

    def as_dict(self) -> dict[str, float]:
        return {name: float(w) for name, w in zip(FEATURE_NAMES, self.coef, strict=True)}


def top_equity_by_position(
    board: LiveBoard, positions: Mapping[str, str]
) -> dict[str, float]:
    """The best (highest equity-VORP) available player's equity value at each position."""
    best: dict[str, float] = {}
    for pid, ev in board.equity_value.items():
        pos = positions.get(pid)
        if pos is None:
            continue
        if pos not in best or ev > best[pos]:
            best[pos] = ev
    return best


def position_features(
    board: LiveBoard, slots_left: Sequence[str], positions: Mapping[str, str]
) -> dict[str, np.ndarray]:
    """Per-open-position feature vectors (`FEATURE_NAMES` order) from a live board + my slots.

    Only positions that are *legal* now (an open slot accepts them and the board has a player)
    get a row. ``equity`` is the best-available player's equity-VORP; ``vona``/``run_prob`` are
    that position's timing pressure; ``need`` is the share of my open slots that accept it.
    ``positions`` maps ``player_id -> position`` (the live board carries no position column).
    """
    open_slots = list(slots_left)
    legal = {p for s in open_slots for p in slot_positions(s)}
    top_equity = top_equity_by_position(board, positions)
    n_open = len(open_slots) or 1

    feats: dict[str, np.ndarray] = {}
    for pos in legal:
        if pos not in board.vona or pos not in top_equity:
            continue
        need = sum(1 for s in open_slots if pos in slot_positions(s)) / n_open
        v = board.vona[pos]
        feats[pos] = np.array([top_equity[pos], v.vona, v.run_prob, need], dtype=float)
    return feats


@dataclass
class FastDraftPolicy:
    """The distilled live policy: score open positions by a linear model, take the best player.

    ``weights`` default to the scarcity-aware cold start; call `distill_policy` to fit them to
    MCTS. ``pick`` is the fast live lookup — one dot product per open position over a board the
    draft room already computed.
    """

    weights: PolicyWeights = field(default_factory=PolicyWeights.default)

    def action_scores(
        self, board: LiveBoard, slots_left: Sequence[str], positions: Mapping[str, str]
    ) -> dict[str, float]:
        """Linear score for each legal open position (higher = draft here)."""
        feats = position_features(board, slots_left, positions)
        return {pos: float(self.weights.coef @ vec) for pos, vec in feats.items()}

    def pick(
        self, board: LiveBoard, slots_left: Sequence[str], positions: Mapping[str, str]
    ) -> tuple[str, str] | None:
        """Fast live lookup → ``(player_id, position)`` to draft, or None if nothing is legal."""
        scores = self.action_scores(board, slots_left, positions)
        if not scores:
            return None
        pos = max(scores, key=lambda p: scores[p])
        top = _best_available(board, pos, positions)
        return (top, pos) if top is not None else None

    def pick_live(
        self,
        players_by_position: Mapping[str, Sequence[tuple[str, float]]],
        opponent_field: OpponentField,
        slots_left: Sequence[str],
        *,
        opponent_counts: Sequence[TeamState] | None = None,
        sensitivity: float = 1.0,
    ) -> tuple[str, str] | None:
        """Full live path: build the equity board then pick (the draft room's one-call entry)."""
        board = live_draft_value(
            players_by_position, opponent_field,
            opponent_counts=opponent_counts, sensitivity=sensitivity,
        )
        positions = {pid: pos for pos, lst in players_by_position.items() for pid, _ in lst}
        return self.pick(board, slots_left, positions)


def _best_available(
    board: LiveBoard, position: str, positions: Mapping[str, str]
) -> str | None:
    """Highest-equity available player at ``position`` (the value-greedy pick within it)."""
    best_pid, best_ev = None, -math.inf
    for pid, ev in board.equity_value.items():
        if positions.get(pid) == position and ev > best_ev:
            best_pid, best_ev = pid, ev
    return best_pid


# --- distillation --------------------------------------------------------------------------
@dataclass(frozen=True)
class DistillSample:
    """One training example: per-position features and the MCTS visit distribution to match."""

    features: Mapping[str, np.ndarray]  # position -> feature vector
    target: Mapping[str, float]  # position -> MCTS visit probability (sums to 1)


def distill_policy(
    samples: Sequence[DistillSample],
    *,
    init: PolicyWeights | None = None,
    lr: float = 0.5,
    n_steps: int = 400,
    l2: float = 1e-3,
) -> PolicyWeights:
    """Fit linear policy weights to MCTS visit distributions by softmax cross-entropy (numpy).

    Minimises Σ_state CE(softmax(features·w), MCTS_target) + L2, by full-batch gradient descent.
    Standardises features across the sample so no single signal dominates the scale, then folds
    the standardisation back so the returned `PolicyWeights` apply to raw features. Starts from
    ``init`` (default: the scarcity-aware cold weights).
    """
    rows = [vec for s in samples for vec in s.features.values()]
    if not rows:
        return init or PolicyWeights.default()
    mat = np.stack(rows)
    mean, std = mat.mean(axis=0), mat.std(axis=0)
    std = np.where(std > 1e-9, std, 1.0)

    w = (init or PolicyWeights.default()).coef.astype(float).copy() * std  # into standardised space
    for _ in range(n_steps):
        grad = l2 * w
        for s in samples:
            positions = list(s.features)
            if not positions:
                continue
            x = np.stack([(s.features[p] - mean) / std for p in positions])
            q = _softmax(x @ w)
            t = np.array([s.target.get(p, 0.0) for p in positions])
            grad += x.T @ (q - t)
        w -= lr * grad / max(1, len(samples))
    return PolicyWeights(coef=w / std)


def _softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max()
    e = np.exp(z)
    return e / (e.sum() or 1.0)


# --- Shapley pick attribution --------------------------------------------------------------
ValueFn = Callable[[frozenset[str]], float]


def shapley_pick_attribution(
    items: Sequence[str],
    value_fn: ValueFn,
    *,
    max_exact: int = 8,
    samples: int = 4000,
    seed: int = 0,
) -> dict[str, float]:
    """Shapley credit for each pick's contribution to the roster's value (``value_fn``).

    ``value_fn(subset)`` scores any subset of the picks (e.g. the best legal-lineup value from
    just those players). Exact subset formula for ≤ ``max_exact`` picks (a starting lineup),
    Monte-Carlo permutation sampling beyond. Satisfies efficiency exactly on the exact path —
    Σφ == value(all) − value(∅) — which `shapley_efficiency_gap` audits.
    """
    ids = list(items)
    n = len(ids)
    if n == 0:
        return {}
    if n <= max_exact:
        return _shapley_exact(ids, value_fn)
    return _shapley_sampled(ids, value_fn, samples=samples, seed=seed)


def _shapley_exact(ids: list[str], value_fn: ValueFn) -> dict[str, float]:
    """Exact Shapley by the weighted-marginal subset formula (n! not enumerated for n≤8)."""
    n = len(ids)
    phi = dict.fromkeys(ids, 0.0)
    fact = [math.factorial(k) for k in range(n + 1)]
    for i in ids:
        rest = [j for j in ids if j != i]
        for r in range(len(rest) + 1):
            weight = fact[r] * fact[n - r - 1] / fact[n]
            for combo in combinations(rest, r):
                s = frozenset(combo)
                phi[i] += weight * (value_fn(s | {i}) - value_fn(s))
    return phi


def _shapley_sampled(
    ids: list[str], value_fn: ValueFn, *, samples: int, seed: int
) -> dict[str, float]:
    """Monte-Carlo Shapley: average each pick's marginal over random join orders."""
    rng = np.random.default_rng(seed)
    phi = dict.fromkeys(ids, 0.0)
    for _ in range(samples):
        order = list(ids)
        rng.shuffle(order)
        s: frozenset[str] = frozenset()
        prev = value_fn(s)
        for i in order:
            s2 = s | {i}
            v = value_fn(s2)
            phi[i] += v - prev
            s, prev = s2, v
    return {i: phi[i] / samples for i in ids}


def shapley_efficiency_gap(
    attribution: Mapping[str, float], value_fn: ValueFn, items: Sequence[str]
) -> float:
    """Audit: |Σφ − (value(all) − value(∅))| — should be ~0 (exact) / tiny (sampled)."""
    total = value_fn(frozenset(items)) - value_fn(frozenset())
    return abs(sum(attribution.values()) - total)


def marginal_starter_value(
    values: Mapping[str, float], positions: Mapping[str, str], template: Sequence[str]
) -> ValueFn:
    """Build a ``value_fn`` = best legal-lineup value fillable from a subset of picks.

    Greedy legal fill against ``template`` (most-specific slot first): each pick's marginal is
    what it adds to the startable lineup, so Shapley credit tracks *startability*, not raw value.
    """
    order = sorted(template, key=lambda s: len(slot_positions(s)))  # specific slots first

    def _value(subset: frozenset[str]) -> float:
        avail = sorted(
            (pid for pid in subset if pid in values),
            key=lambda pid: values[pid], reverse=True,
        )
        used: set[str] = set()
        total = 0.0
        for slot in order:
            accepts = slot_positions(slot)
            pick = next(
                (pid for pid in avail if pid not in used and positions.get(pid) in accepts),
                None,
            )
            if pick is not None:
                used.add(pick)
                total += values[pick]
        return total

    return _value
