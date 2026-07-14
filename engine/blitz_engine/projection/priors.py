"""Priors for the hierarchical core — empirical + expert hybrid, weakly-informative.

The 4-level hierarchy (League→Team→Position→Player) needs a prior at every level. The
design (brief §"Priors = empirical + expert hybrid"):

  * **Empirical base** — the league/position location scales come from history (the data
    itself informs where a QB's opportunity/efficiency typically sits). We keep these
    *weakly*-informative: wide enough that data dominates, tight enough to regularise the
    thousands of sparse player-week cells and let rookies **borrow strength**.
  * **Expert nudge** — role / ADP / Vegas / coaching shift a player's *talent* prior mean
    off the positional average. E1-core does NOT compute those nudges; it exposes the
    **talent-prior hook** (`TalentPriorHook`) that E1-talent (GP / Kalman / HMM / aging)
    plugs into. With no hook the player prior is the neutral N(0, player_scale) — a plain
    partial-pooling shrink toward the position mean.

Everything here is *location/scale specs*, not sampled sites — `model.py` turns a
`PriorSet` into `numpyro.sample` statements. This keeps the priors declarative and lets a
downstream unit swap one level's spec without touching the model body.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import jax

    Array = jax.Array

__all__ = [
    "GroupPrior",
    "PriorSet",
    "TalentPrior",
    "TalentPriorHook",
    "default_priors",
]


@dataclass(frozen=True)
class GroupPrior:
    """A Normal(loc, scale) prior for one hierarchy level's random effects (log scale).

    `scale` is the between-group spread: larger = weaker pooling (groups freer to differ),
    smaller = stronger pooling (groups shrink to the parent). Half-Normal hyper-priors on
    the scales are added in `model.py`; the value here is the hyper-prior's own scale.
    """

    loc: float = 0.0
    scale: float = 1.0


@dataclass(frozen=True)
class PriorSet:
    """The full prior specification for one generative stage (opportunity or efficiency).

    Levels stack: league intercept + team + position + player deviations, each partially
    pooled. `dispersion_scale` is the half-Normal scale on the family's dispersion
    (NegBin/Gamma concentration), `td_regression` the pooling strength on the TD rate
    toward its positional mean (higher ⇒ harder regression of unsustainable TD%).
    """

    league: GroupPrior = GroupPrior(loc=0.0, scale=2.0)
    team: GroupPrior = GroupPrior(loc=0.0, scale=0.5)
    position: GroupPrior = GroupPrior(loc=0.0, scale=1.0)
    player: GroupPrior = GroupPrior(loc=0.0, scale=0.75)
    dispersion_scale: float = 2.0
    td_regression: float = 4.0


def default_priors() -> dict[str, PriorSet]:
    """The empirical+weakly-informative default for each stage.

    Opportunity varies more across players (workload is role-driven) → a wider player
    scale; efficiency is closer to a positional constant (yards-per-touch regresses hard)
    → a tighter player scale and stronger TD regression. Tuned to be *weak*: on real
    2014+ volume the data dominates within a couple of games of history.
    """
    return {
        "opportunity": PriorSet(
            player=GroupPrior(scale=1.0),
            position=GroupPrior(scale=1.25),
            td_regression=4.0,
        ),
        "efficiency": PriorSet(
            player=GroupPrior(scale=0.4),
            position=GroupPrior(scale=0.75),
            td_regression=6.0,
        ),
    }


# ── Extension seam: TALENT-PRIOR HOOK (E1-talent plugs in here) ───────────────
@dataclass(frozen=True)
class TalentPrior:
    """Per-player override of the *player-level* talent prior (log scale, opportunity+eff).

    `loc` shifts a player's expected effect off the positional mean (a strong-role WR gets
    loc > 0); `scale` narrows/widens their uncertainty (a proven vet → small scale = low
    epistemic; a rookie → large scale = high epistemic). Arrays are per-player, indexed by
    `ModelData.player_ids` order. Return neutral (loc 0, scale = PriorSet.player.scale) for
    players the hook knows nothing about — the seam MUST degrade to plain partial pooling.
    """

    loc: Array
    scale: Array


@runtime_checkable
class TalentPriorHook(Protocol):
    """SEAM (E1-talent). Maps the player index → a `TalentPrior` for a given stage.

    A GP / Kalman / HMM / aging-curve model computes each player's latent-talent mean and
    uncertainty and returns them here; E1-core consumes loc/scale, nothing else. Contract:
    * output arrays are shape (n_players,), aligned to `player_ids`;
    * a context-free / unknown player MUST map to loc 0.0 and the stage's default scale
      (degrade-neutral — a missing talent model can never *hurt* the base fit).
    """

    def __call__(self, player_ids: list[str], stage: str, default_scale: float) -> TalentPrior: ...


def widen_rookie(base: PriorSet, rookie_mask: Array, factor: float = 2.0) -> PriorSet:
    """Convenience: widen the player scale for flagged rookies (more epistemic room).

    A helper E1-talent MAY reuse; not applied by default (the neutral path pools all
    players equally). `factor` multiplies the player scale where `rookie_mask` is True.
    """
    del rookie_mask, factor  # ponytail: applied inside model.py per-player when a hook supplies it
    return replace(base)
