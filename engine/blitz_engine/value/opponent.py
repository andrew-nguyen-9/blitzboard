"""Opponent model — a live-updated mixture over draft strategy archetypes (E4-deep).

Every rival GM is modelled as an unknown mix of a few named strategies (BPA, Zero-RB,
Hero-RB, Robust-RB, Need-based). Each archetype is just a function that, given the board and
a team's current roster, returns a probability over *which position* the team drafts next.
The opponent model carries a Dirichlet-style weight vector over the archetypes (seeded by
league history), and every observed pick nudges those weights toward the archetypes that
predicted it — a plain Bayesian posterior update, no framework.

`ponytail:` the archetypes are small pure functions and the update is one line of Bayes; the
whole model is a weight vector + a lookup. Its only output the rest of E4 needs is
``pick_position_probs`` — P(next pick is each position) — which drives demand-derived
replacement (`replacement.py`) and positional-run probability (`vona.py`).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE", "K", "DST")

# A roster's positional need target for a default superflex, half-PPR league — how many of
# each position a "balanced" team wants. Need-based archetypes score against this.
DEFAULT_TARGET_COUNTS: Mapping[str, int] = {
    "QB": 2, "RB": 5, "WR": 5, "TE": 2, "K": 1, "DST": 1,
}

# (roster state a team exposes to the archetypes) -----------------------------------------
TeamState = Mapping[str, int]  # position -> count already on the team


def _softmax(scores: Mapping[str, float]) -> dict[str, float]:
    """Numerically-stable softmax over a position->score map (missing positions dropped)."""
    if not scores:
        return {}
    hi = max(scores.values())
    exp = {k: 2.718281828459045 ** (v - hi) for k, v in scores.items()}
    z = sum(exp.values()) or 1.0
    return {k: v / z for k, v in exp.items()}


# -- archetypes: (available_top_value_by_pos, team_counts) -> P(pick position) -------------
Archetype = Callable[[Mapping[str, float], TeamState], dict[str, float]]


def _best_player_available(top: Mapping[str, float], _team: TeamState) -> dict[str, float]:
    """BPA: pick the position holding the single best remaining player (value-greedy)."""
    return _softmax({pos: v for pos, v in top.items()})


def _need_based(top: Mapping[str, float], team: TeamState) -> dict[str, float]:
    """Need: weight value by the *unmet* share of each position's target roster count."""
    scored = {
        pos: v * max(0.0, 1.0 - team.get(pos, 0) / max(DEFAULT_TARGET_COUNTS.get(pos, 1), 1))
        for pos, v in top.items()
    }
    return _softmax(scored)


def _positional_bias(bias: Mapping[str, float]) -> Archetype:
    """Build a value-greedy archetype that multiplicatively biases certain positions.

    ``bias`` > 1 favours a position, < 1 avoids it (until the team already has some, when the
    avoidance relaxes — a Zero-RB drafter still takes RBs eventually). Used for the RB-shaped
    strategies that define the archetype spread.
    """

    def _f(top: Mapping[str, float], team: TeamState) -> dict[str, float]:
        scored = {}
        for pos, v in top.items():
            b = bias.get(pos, 1.0)
            if b < 1.0 and team.get(pos, 0) >= 1:  # avoidance relaxes once we own one
                b = 1.0
            scored[pos] = v * b
        return _softmax(scored)

    return _f


# The archetype registry — league-history priors weight these.
ARCHETYPES: dict[str, Archetype] = {
    "bpa": _best_player_available,
    "need": _need_based,
    "zero_rb": _positional_bias({"RB": 0.35, "WR": 1.4, "TE": 1.2}),
    "hero_rb": _positional_bias({"RB": 1.5, "WR": 1.1}),
    "robust_rb": _positional_bias({"RB": 1.8, "WR": 0.9}),
}
_ARCH_NAMES: tuple[str, ...] = tuple(ARCHETYPES)


@dataclass
class OpponentModel:
    """Per-opponent mixture over strategy archetypes, updated live from observed picks.

    ``weights`` is an unnormalised non-negative vector over ``ARCHETYPES`` (a Dirichlet-style
    pseudo-count). Construct from a league-history prior via `from_prior`; call `update` after
    every pick the opponent makes; read `pick_position_probs` to get P(next pick = position).
    """

    weights: dict[str, float] = field(
        default_factory=lambda: {name: 1.0 for name in _ARCH_NAMES}
    )
    learn_rate: float = 1.0  # how hard an observed pick pulls the mixture (pseudo-count add)

    @classmethod
    def from_prior(cls, prior: Mapping[str, float] | None = None, *, learn_rate: float = 1.0):
        """Seed the mixture from league-history archetype shares (unknown archetypes → 0)."""
        w = {name: 1e-3 for name in _ARCH_NAMES}  # tiny floor so no archetype is impossible
        for name, val in (prior or {}).items():
            if name in w:
                w[name] = max(1e-3, float(val))
        return cls(weights=w, learn_rate=learn_rate)

    def mixture(self) -> dict[str, float]:
        """Normalised archetype posterior — the current belief over this GM's strategy."""
        z = sum(self.weights.values()) or 1.0
        return {name: w / z for name, w in self.weights.items()}

    def pick_position_probs(
        self, top_value_by_pos: Mapping[str, float], team_counts: TeamState
    ) -> dict[str, float]:
        """P(this opponent's next pick is each position), marginalised over the archetypes.

        ``top_value_by_pos``: best remaining player value per position (the board frontier).
        ``team_counts``: how many of each position the opponent already rosters.
        """
        mix = self.mixture()
        out: dict[str, float] = {pos: 0.0 for pos in top_value_by_pos}
        for name, arch in ARCHETYPES.items():
            m = mix[name]
            if m <= 0.0:
                continue
            for pos, p in arch(top_value_by_pos, team_counts).items():
                out[pos] += m * p
        z = sum(out.values()) or 1.0
        return {pos: p / z for pos, p in out.items()}

    def update(
        self, picked_position: str, top_value_by_pos: Mapping[str, float], team_counts: TeamState
    ) -> None:
        """Bayesian nudge: reweight archetypes by how well they predicted the observed pick.

        Posterior ∝ prior × likelihood, where each archetype's likelihood is the probability
        it assigned to ``picked_position`` on the board the opponent faced. Implemented as a
        pseudo-count add (scaled by ``learn_rate``) so the mixture concentrates monotonically.
        """
        mix = self.mixture()
        like = {
            name: ARCHETYPES[name](top_value_by_pos, team_counts).get(picked_position, 0.0)
            for name in _ARCH_NAMES
        }
        post = {name: mix[name] * like[name] for name in _ARCH_NAMES}
        z = sum(post.values())
        if z <= 0.0:  # pick no archetype expected (e.g. a reach) — leave belief unchanged
            return
        for name in _ARCH_NAMES:
            self.weights[name] += self.learn_rate * post[name] / z


@dataclass
class OpponentField:
    """The set of opposing GMs between you and your next pick — one model each.

    ``pick_position_sequence`` returns, for each intervening opponent pick in draft order, its
    P(position) distribution — exactly the input positional-run probability and demand need.
    """

    models: list[OpponentModel]

    @classmethod
    def uniform(cls, n_opponents: int, prior: Mapping[str, float] | None = None):
        """A field of ``n_opponents`` identical models seeded from the same history prior."""
        return cls(models=[OpponentModel.from_prior(prior) for _ in range(n_opponents)])

    def pick_position_sequence(
        self,
        top_value_by_pos: Mapping[str, float],
        team_counts_by_opponent: Sequence[TeamState] | None = None,
    ) -> list[dict[str, float]]:
        """P(position) for each upcoming opponent pick, in the order they pick.

        ``team_counts_by_opponent`` (optional, parallel to ``models``) lets each opponent's
        need react to its own roster; omitted → every opponent treated as empty-rostered.
        """
        counts = team_counts_by_opponent or [{} for _ in self.models]
        return [
            m.pick_position_probs(top_value_by_pos, counts[i] if i < len(counts) else {})
            for i, m in enumerate(self.models)
        ]
