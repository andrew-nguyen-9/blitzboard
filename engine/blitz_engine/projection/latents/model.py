"""`LatentModel` — the E1-latents estimator behind E1-core's `LatentHook` seam.

This is the object the projector is handed as its `latent=` hook. It fits, once, on a
player-game history frame, learns the four latent structures (`estimators.py`), and then
answers the seam call ``__call__(data) -> LatentContribution`` for any roster by placing those
learned effects on the current players and composing them on the log-opportunity / log-
efficiency scales the core adds them to.

rel=DEGRADE (optional, per spec §Release-policy). Two independent degrade paths:

  * **Ablation gate (per latent)** — the QB–WR chemistry latent is thin-data and drops itself
    wholesale unless its pairing signal beats a permutation test (`ChemistryLatent`).
  * **Degrade-neutral (whole model)** — if the fit has too little data to learn anything, or
    fails its own finiteness self-check, `enabled` is False and the hook returns all-zeros,
    so the base projection stays exactly valid. A missing latent can never worsen the fit.

The learned effects are exposed as plain dicts (`defense_strength` / `oline` / `ecosystem` /
`chemistry`) so **E3-correlation** (shared team/matchup latents drive residual correlation)
and the **SOS** read can consume the same opponent-adjusted defensive strengths.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import jax.numpy as jnp
import numpy as np

from blitz_engine.projection.latents.estimators import (
    ChemistryLatent,
    DefenseLatent,
    EcosystemLatent,
    OLineLatent,
    ResolveContext,
    _log_ypo,
)
from blitz_engine.projection.latents.shrinkage import clip_latent
from blitz_engine.projection.model import LatentContribution

if TYPE_CHECKING:
    import pandas as pd

    from blitz_engine.projection.model import ModelData

__all__ = ["LatentModel"]

_MIN_ROWS = 8  # below this the latents are noise → degrade the whole model to neutral
_GLOBAL_EFF_BOUND = 0.5  # final clip on the composed efficiency latent (log scale, ~×0.6..×1.65)
_GLOBAL_OPP_BOUND = 0.4  # final clip on the composed opportunity latent


class LatentModel:
    """Latent team/matchup/chemistry structures; a drop-in `LatentHook` for the projector.

    Construct via `LatentModel.fit(history, matchups=...)`, then pass the instance as
    ``HierarchicalProjector(..., latent=model)``. `matchups` (team → opponent) is optional and
    may be attached later with `with_matchups`; without it the opponent-adjusted defensive
    latent degrades to neutral (nothing to face).
    """

    def __init__(
        self,
        defense: DefenseLatent,
        oline: OLineLatent,
        ecosystem: EcosystemLatent,
        chemistry: ChemistryLatent,
        qb_of_team: dict[str, str],
        *,
        matchups: dict[str, str] | None = None,
        enabled: bool = True,
    ) -> None:
        self._defense = defense
        self._oline = oline
        self._ecosystem = ecosystem
        self._chemistry = chemistry
        self._qb_of_team = qb_of_team
        self._matchups = dict(matchups or {})
        self._enabled = enabled and self.check()

    # -- construction ----------------------------------------------------------
    @classmethod
    def fit(
        cls,
        history: pd.DataFrame,
        *,
        matchups: dict[str, str] | None = None,
        alpha: float = 0.05,
    ) -> LatentModel:
        """Fit the latent structures from a long player-game frame.

        Required columns: `player_id`, `position`, `team`, `opportunities`, `yards`.
        Optional: `opponent` (enables the defensive latent), `passer_id` (enables the QB–WR
        chemistry latent). An empty/too-small frame yields a fully-neutral (disabled) model —
        the degrade-neutral contract. `alpha` is the chemistry ablation significance level.
        """
        h = _prep(history)
        if h is None or len(h) < _MIN_ROWS:
            return cls._neutral(matchups)
        team = h["team"].to_numpy()
        pos = h["position"].to_numpy()
        pid = h["player_id"].to_numpy()
        log_ypo = _log_ypo(h["yards"].to_numpy(), h["opportunities"].to_numpy())
        opp = h["opponent"].to_numpy() if "opponent" in h else None
        passer = h["passer_id"].to_numpy() if "passer_id" in h else None

        defense = DefenseLatent.fit(team, opp, pos, log_ypo)
        oline = OLineLatent.fit(team, pos, log_ypo)
        ecosystem = EcosystemLatent.fit(team, log_ypo)
        chemistry = ChemistryLatent.fit(passer, pid, pos, log_ypo, alpha=alpha)
        qb_of_team = _primary_qbs(h)
        return cls(defense, oline, ecosystem, chemistry, qb_of_team, matchups=matchups)

    @classmethod
    def _neutral(cls, matchups: dict[str, str] | None) -> LatentModel:
        return cls(
            DefenseLatent({}), OLineLatent({}), EcosystemLatent({}),
            ChemistryLatent({}, significant=False), {}, matchups=matchups, enabled=False,
        )

    def with_matchups(self, matchups: dict[str, str]) -> LatentModel:
        """A copy of this fitted model bound to a new (team → opponent) schedule."""
        return LatentModel(
            self._defense, self._oline, self._ecosystem, self._chemistry,
            self._qb_of_team, matchups=matchups, enabled=self._enabled,
        )

    # -- the seam: LatentHook.__call__ -----------------------------------------
    def __call__(self, data: ModelData) -> LatentContribution:
        """Resolve the composed latent contribution for `data`'s player universe.

        Sums the four estimators on each scale, applies a final hard clip (the safety guard),
        and returns zeros when the model is disabled — so a degraded latent is a strict no-op
        on the base projection.
        """
        n = data.n_players
        if not self._enabled:
            zeros = jnp.zeros(n)
            return LatentContribution(opportunity=zeros, efficiency=zeros)
        ctx = self._resolve_context(data)
        opp_total = np.zeros(n)
        eff_total = np.zeros(n)
        for est in (self._defense, self._oline, self._ecosystem, self._chemistry):
            opp_raw, eff = est.contribution(ctx)
            opp_total += opp_raw
            eff_total += eff
        opp_c = np.array([clip_latent(x, _GLOBAL_OPP_BOUND) for x in opp_total], dtype=np.float32)
        eff_c = np.array([clip_latent(x, _GLOBAL_EFF_BOUND) for x in eff_total], dtype=np.float32)
        return LatentContribution(opportunity=jnp.asarray(opp_c), efficiency=jnp.asarray(eff_c))

    def _resolve_context(self, data: ModelData) -> ResolveContext:
        team_of = np.asarray(data.team_of_player)
        pos_of = np.asarray(data.pos_of_player)
        teams = [data.teams[i] for i in team_of]
        positions = [data.positions[i] for i in pos_of]
        return ResolveContext(
            player_ids=list(data.player_ids), positions=positions, teams=teams,
            matchups=self._matchups, qb_of_team=self._qb_of_team,
        )

    # -- self-check / degrade --------------------------------------------------
    def check(self) -> bool:
        """True iff the fit produced usable, finite latent structure (its own convergence gate).

        Every learned effect must be finite; at least one latent must carry signal. A failed
        check flips `enabled` off → the hook degrades to all-zeros (DEGRADE-NEUTRAL).
        """
        dicts = (self._defense.strength, self._oline.strength,
                 self._ecosystem.strength, self._chemistry.pair)
        values = [v for d in dicts for v in d.values()]
        if not values:
            return False
        return bool(np.all(np.isfinite(values)))

    @property
    def enabled(self) -> bool:
        """Whether the latent hook is live (False ⇒ degrade-neutral, all contributions 0)."""
        return self._enabled

    # -- war-room / downstream accessors (E3 correlation + SOS read these) ------
    def defense_strength(self) -> dict[tuple[str, str], float]:
        """Opponent-adjusted defensive strength per (team, position); >0 ⇒ generous defense."""
        return dict(self._defense.strength)

    def oline(self) -> dict[str, float]:
        """Per-team offensive-line effect (RB rush efficiency + partial pass floor)."""
        return dict(self._oline.strength)

    def ecosystem(self) -> dict[str, float]:
        """Per-team offensive-ecosystem efficiency lift."""
        return dict(self._ecosystem.strength)

    def chemistry(self) -> dict[tuple[str, str], float]:
        """QB–receiver chemistry lifts (empty when the ablation gate dropped the latent)."""
        return dict(self._chemistry.pair)

    @property
    def chemistry_significant(self) -> bool:
        """Whether the chemistry latent survived its ablation gate (False ⇒ it was dropped)."""
        return self._chemistry.significant


# -- history prep --------------------------------------------------------------
def _prep(history: pd.DataFrame) -> pd.DataFrame | None:
    """Validate + normalise the history frame; None if empty, ValueError on missing columns."""
    if history is None or len(history) == 0:
        return None
    need = {"player_id", "position", "team", "opportunities", "yards"}
    missing = need - set(history.columns)
    if missing:
        raise ValueError(f"latent history frame missing columns: {sorted(missing)}")
    import pandas as pd

    h = history.copy()
    for col in ("player_id", "position", "team"):
        h[col] = h[col].astype(str)
    for col in ("opponent", "passer_id"):
        if col in h.columns:
            h[col] = h[col].astype(str)
    h["opportunities"] = pd.to_numeric(h["opportunities"], errors="coerce")
    h["yards"] = pd.to_numeric(h["yards"], errors="coerce")
    return h.dropna(subset=["opportunities", "yards"])


def _primary_qbs(h: pd.DataFrame) -> dict[str, str]:
    """Each team's primary passer = the QB-position player with the most opportunities."""
    qbs = h[h["position"] == "QB"]
    if len(qbs) == 0:
        return {}
    by = qbs.groupby(["team", "player_id"])["opportunities"].sum().reset_index()
    top = by.sort_values("opportunities").groupby("team").last()
    return {str(team): str(row["player_id"]) for team, row in top.iterrows()}
