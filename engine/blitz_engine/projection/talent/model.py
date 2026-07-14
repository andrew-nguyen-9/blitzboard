"""`TalentModel` — the E1-talent true-talent estimator behind E1-core's talent-prior seam.

This is the object the projector is handed as its `talent_prior=` hook. It fits, once, on a
player-history frame and then answers the seam call
`__call__(player_ids, stage, default_scale) -> TalentPrior(loc, scale)` for any roster by
composing the sub-layers built in this package:

    career arc (GP + Kalman)  → a proven player's latent-talent level + epistemic width
    per-position aging curve   → an additive age haircut folded into the level
    HMM regime                 → the current breakout/steady/decline/hurt label (+ features)
    rookie prior               → wide draft-capital/archetype/college prior for no-history

Every path is **degrade-neutral** — a player the model has never seen returns loc 0.0 and
the stage's `default_scale`, so plugging this hook in can never make the base fit worse
(the seam's hard contract). The regime labels, aging accessor and rookie inputs are public
so **E2-survival** can read workload/regime for its hazard model.
"""
from __future__ import annotations

from dataclasses import dataclass

import jax.numpy as jnp
import numpy as np
import pandas as pd

from blitz_engine.projection.priors import TalentPrior
from blitz_engine.projection.talent.aging import AgingCurves
from blitz_engine.projection.talent.dynamics import CareerArc, fit_career_arc, learn_lengthscale
from blitz_engine.projection.talent.regime import RegimeFeatures, label_regime
from blitz_engine.projection.talent.rookie import RookiePrior, RookiePriors

__all__ = ["PlayerTalent", "TalentModel"]

_LOC_COEF = 0.5  # map standardised talent (z) → log-opportunity loc (bounded, gentle)
_LOC_CLIP = 1.5  # hard bound on any talent loc (keeps the prior weakly-informative)


@dataclass(frozen=True)
class PlayerTalent:
    """Everything the model knows about one veteran player (the E2-facing record)."""

    player_id: str
    position: str
    loc: float
    scale: float
    regime: RegimeFeatures
    arc: CareerArc


class TalentModel:
    """True-talent estimator; a drop-in `TalentPriorHook` for `HierarchicalProjector`.

    Construct via `TalentModel.fit(history, draft=..., default_scale=...)`, then pass the
    instance as `HierarchicalProjector(..., talent_prior=model)`.
    """

    def __init__(
        self,
        veterans: dict[str, PlayerTalent],
        aging: AgingCurves,
        rookies: RookiePriors,
        default_scale: float,
    ) -> None:
        self._vets = veterans
        self.aging = aging
        self.rookies = rookies
        self._default_scale = default_scale

    # -- construction ----------------------------------------------------------
    @classmethod
    def fit(
        cls,
        history: pd.DataFrame,
        *,
        draft: pd.DataFrame | None = None,
        default_scale: float = 1.0,
        value_col: str = "value",
        time_col: str = "t",
        age_col: str | None = "age",
    ) -> TalentModel:
        """Fit talent dynamics from a long player-history frame.

        Required columns: `player_id`, `position`, `<value_col>` (a per-observation talent
        signal, e.g. usage or fantasy points/game) and `<time_col>` (a monotonic time index
        per player, e.g. season+week/22). Optional `<age_col>` enables the aging curve.
        An empty frame yields a fully-neutral model (every player degrades to the base prior).
        """
        h = _prep(history, value_col, time_col, age_col)
        aging = (
            AgingCurves.fit(h["position"].to_numpy(), h["_age"].to_numpy(), h["_val"].to_numpy())
            if age_col is not None and "_age" in h
            else AgingCurves()
        )
        # per-position standardisation + learned length-scale (adaptive recency)
        vets: dict[str, PlayerTalent] = {}
        arch: dict[str, float] = {}
        for pos, pos_df in h.groupby("position", sort=False):
            mu, sd = float(pos_df["_val"].mean()), float(pos_df["_val"].std()) or 1.0
            arch[str(pos)] = 0.0  # rookies start at the positional mean (z=0)
            series = [
                (g["_t"].to_numpy(), ((g["_val"] - mu) / sd).to_numpy())
                for _, g in pos_df.groupby("player_id", sort=False)
            ]
            ls = learn_lengthscale(series)
            for pid, g in pos_df.groupby("player_id", sort=False):
                vets[str(pid)] = cls._fit_player(str(pid), str(pos), g, mu, sd, ls,
                                                 default_scale, aging)
        rookies = RookiePriors(draft, arch, default_scale)
        return cls(vets, aging, rookies, default_scale)

    @staticmethod
    def _fit_player(
        pid: str, pos: str, g: pd.DataFrame, mu: float, sd: float, ls: float,
        default_scale: float, aging: AgingCurves,
    ) -> PlayerTalent:
        g = g.sort_values("_t")
        z = ((g["_val"] - mu) / sd).to_numpy()
        arc = fit_career_arc(g["_t"].to_numpy(), z, lengthscale=ls)
        regime = label_regime(z)
        age = float(g["_age"].iloc[-1]) if "_age" in g and pd.notna(g["_age"].iloc[-1]) else None
        aging_adj = aging.adjustment(pos, age)
        loc = float(np.clip(_LOC_COEF * arc.level + aging_adj, -_LOC_CLIP, _LOC_CLIP))
        # epistemic width scales the prior: confident (low GP std, long career) ⇒ tighter
        conf = 1.0 / (1.0 + max(arc.n_obs, 1) / 8.0)  # →0 as history grows
        width = 0.55 + 0.45 * float(np.clip(arc.epistemic, 0.0, 1.0)) + 0.3 * conf
        scale = float(np.clip(default_scale * width, 0.3 * default_scale, 1.5 * default_scale))
        return PlayerTalent(pid, pos, loc, scale, regime, arc)

    # -- the seam: TalentPriorHook.__call__ ------------------------------------
    def __call__(self, player_ids: list[str], stage: str, default_scale: float) -> TalentPrior:
        """Resolve the per-player talent prior for a stage, aligned to `player_ids`.

        Talent shifts the **opportunity** (usage/appeal) prior; other stages resolve neutral.
        Unknown players ⇒ loc 0.0, `default_scale` — the degrade-neutral contract.
        """
        n = len(player_ids)
        loc = np.zeros(n, dtype=np.float32)
        scale = np.full(n, default_scale, dtype=np.float32)
        if stage != "opportunity":
            return TalentPrior(loc=jnp.asarray(loc), scale=jnp.asarray(scale))
        for i, pid in enumerate(player_ids):
            vet = self._vets.get(str(pid))
            if vet is not None:
                loc[i], scale[i] = vet.loc, vet.scale
        return TalentPrior(loc=jnp.asarray(loc), scale=jnp.asarray(scale))

    # -- E2-facing accessors ---------------------------------------------------
    def player(self, player_id: str) -> PlayerTalent | None:
        """Full talent record (loc/scale + regime + career arc) for a player, or None."""
        return self._vets.get(str(player_id))

    def regime(self, player_id: str) -> RegimeFeatures | None:
        """Current regime label + leading-indicator features for a player (None if rookie)."""
        vet = self._vets.get(str(player_id))
        return vet.regime if vet is not None else None

    def regimes(self) -> dict[str, str]:
        """All veteran regime labels, keyed by player_id (E2 hazard grouping)."""
        return {pid: v.regime.label for pid, v in self._vets.items()}

    def aging_adjustment(self, position: str, age: float | None) -> float:
        """Per-position aging haircut (log scale) at an age — the aging-curve accessor."""
        return self.aging.adjustment(position, age)

    def rookie_prior(self, player_id: str, position: str) -> RookiePrior:
        """Rookie talent prior + its draft/archetype/college inputs for a player."""
        return self.rookies.get(player_id, position)

    @property
    def college_available(self) -> bool:
        """Whether CFBD college priors were available (False ⇒ degrade path was taken)."""
        return self.rookies.college_available


def _prep(
    history: pd.DataFrame, value_col: str, time_col: str, age_col: str | None
) -> pd.DataFrame:
    """Validate + normalise the history frame into the internal `_val/_t/_age` columns."""
    if history is None or len(history) == 0:
        return pd.DataFrame(columns=["player_id", "position", "_val", "_t"])
    need = {"player_id", "position", value_col, time_col}
    missing = need - set(history.columns)
    if missing:
        raise ValueError(f"history frame missing columns: {sorted(missing)}")
    h = history.copy()
    h["player_id"] = h["player_id"].astype(str)
    h["position"] = h["position"].astype(str)
    h["_val"] = pd.to_numeric(h[value_col], errors="coerce")
    h["_t"] = pd.to_numeric(h[time_col], errors="coerce")
    h = h.dropna(subset=["_val", "_t"])
    if age_col is not None and age_col in h.columns:
        h["_age"] = pd.to_numeric(h[age_col], errors="coerce")
    return h
