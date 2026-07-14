"""The generative core: a 4-level hierarchical, two-stage NumPyro model.

Hierarchy (partial pooling at every level so rookies **borrow strength** from their
position/team instead of being fit on one noisy game):

    League ──▶ Team ──▶ Position ──▶ Player

Two-stage generative structure (brief §"Two-stage generative"):

    OPPORTUNITY   team_plays(pace) ─▶ per-player usage **share** (Dirichlet α) ─▶
                  player opportunities ~ NegBin(team_plays · share, conc)
    EFFICIENCY    yards ~ Gamma(mean = opp · yards-per-opp)   [conditioned on opp]
                  TDs   ~ Poisson(opp · td_rate)              [td_rate regressed hard]

Opportunity and efficiency are *separate* linear predictors so the two layers can be read
back independently (a WR's volume vs his catch efficiency) — E2/E3/E6 consume them apart.

The **Dirichlet share** is a first-class `numpyro.deterministic` site: dropping an injured
player's α to 0 renormalises the rest — E2 rebuilds redistribution straight from it.

Three EXTENSION SEAMS are baked in as *pre-resolved arrays* (the projector turns hooks
into arrays before calling the model, keeping the model pure & jit-friendly):

    factor_log_opp   bounded multiplicative factors  → added on the log-opportunity scale
    latent_opp/eff   latent injections (embeddings/GP) → added on each linear predictor
    talent_loc/scale player-talent prior              → the Normal prior on player effects

Every seam DEGRADES TO NEUTRAL: zeros (factors ⇒ ×1.0, latents ⇒ +0) and loc 0 / default
scale. A context-free player is projected by the plain hierarchy — a missing downstream
model can never make the base fit worse. See the `FactorHook` / `LatentHook` /
`TalentPriorHook` (in `priors.py`) protocols for what E1-factors/latents/talent implement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import jax
import jax.numpy as jnp
import numpyro
import numpyro.distributions as dist

from blitz_engine.projection.families import gamma_family, negbin_family, poisson_family
from blitz_engine.projection.priors import PriorSet, default_priors

if TYPE_CHECKING:
    import numpy as np

    Array = jax.Array

__all__ = [
    "FACTOR_BOUNDS",
    "FactorContext",
    "FactorHook",
    "LatentContribution",
    "LatentHook",
    "ModelData",
    "Seams",
    "projection_model",
]

#: Hard clamp on any single bounded-multiplicative factor (brief: "mult, bounded").
FACTOR_BOUNDS = (0.5, 2.0)


# ── input contract ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ModelData:
    """A tidy player-week design for the core (the input every feature layer targets).

    Player-indexed arrays (length P = distinct players) define the hierarchy; observation-
    indexed arrays (length N = player-week rows) are the likelihood targets. Build via
    `ModelData.from_frame` from a pandas frame with the documented columns, or `from_store`
    for a best-effort aggregation off the raw pbp table.
    """

    player_ids: list[str]
    positions: list[str]
    teams: list[str]
    # player → group index
    team_of_player: np.ndarray  # (P,) int
    pos_of_player: np.ndarray  # (P,) int
    n_teams: int
    n_positions: int
    # observation (player-week) arrays
    obs_player: np.ndarray  # (N,) int  → player index
    team_plays: np.ndarray  # (N,) float exposure (team offensive plays that week)
    opportunities: np.ndarray  # (N,) float observed touches (targets + carries)
    yards: np.ndarray  # (N,) float observed skill yards
    tds: np.ndarray  # (N,) float observed TDs
    obs_week: np.ndarray | None = None  # (N,) optional week label (for output joins)

    @property
    def n_players(self) -> int:
        return len(self.player_ids)

    @property
    def n_obs(self) -> int:
        return int(self.obs_player.shape[0])

    @classmethod
    def from_frame(
        cls, df, *, obs_df=None, player_col: str = "player_id"  # noqa: ANN001
    ) -> ModelData:
        """Build from a tidy player-week frame.

        Required columns: `player_id`, `position`, `team`, `team_plays`, `opportunities`,
        `yards`, `tds` (+ optional `week`). One row per player-week; the player→team/
        position hierarchy is taken from each player's most recent row in `df`.

        `df` fixes the *player universe / indexing*; `obs_df` (default `df`) supplies the
        *observation rows*. Passing a train slice as `df` and a test slice as `obs_df`
        (both over the same players) keeps posterior player effects aligned across a
        walk-forward split — the projector can fit on one and predict the other.
        """
        import numpy as np
        import pandas as pd

        d = df.copy()
        d[player_col] = d[player_col].astype(str)
        players = list(pd.unique(d[player_col]))
        p_index = {pid: i for i, pid in enumerate(players)}
        last = d.groupby(player_col, sort=False).last()
        positions = [str(last.loc[pid, "position"]) for pid in players]
        teams_per = [str(last.loc[pid, "team"]) for pid in players]
        team_names = list(dict.fromkeys(teams_per))
        pos_names = list(dict.fromkeys(positions))
        t_index = {t: i for i, t in enumerate(team_names)}
        pos_idx_map = {p: i for i, p in enumerate(pos_names)}

        o = (df if obs_df is None else obs_df).copy()
        o[player_col] = o[player_col].astype(str)
        o = o[o[player_col].isin(p_index)]  # only players in the universe
        week = o["week"].to_numpy(dtype=np.int32) if "week" in o.columns else None
        return cls(
            player_ids=players,
            positions=pos_names,
            teams=team_names,
            team_of_player=np.array([t_index[t] for t in teams_per], dtype=np.int32),
            pos_of_player=np.array([pos_idx_map[p] for p in positions], dtype=np.int32),
            n_teams=len(team_names),
            n_positions=len(pos_names),
            obs_player=o[player_col].map(p_index).to_numpy(dtype=np.int32),
            team_plays=o["team_plays"].to_numpy(dtype=np.float32),
            opportunities=o["opportunities"].to_numpy(dtype=np.float32),
            yards=o["yards"].to_numpy(dtype=np.float32),
            tds=o["tds"].to_numpy(dtype=np.float32),
            obs_week=week,
        )


# ── Extension seams: factor + latent hooks (talent hook lives in priors.py) ────
@dataclass(frozen=True)
class FactorContext:
    """What a factor hook sees: the model data + an optional per-player context frame.

    E1-factors reads role/ADP/Vegas/coaching (E0-sources tables) keyed to `data.player_ids`
    and returns a per-player raw multiplier. `context` is a free-form dict the wiring passes
    through (e.g. resolved Vegas totals) so a hook need not re-query the store itself.
    """

    data: ModelData
    context: dict[str, object]


@runtime_checkable
class FactorHook(Protocol):
    """SEAM (E1-factors). Per-player BOUNDED MULTIPLICATIVE adjustment to opportunity.

    Returns a raw multiplier array shape (n_players,). The projector clamps it to
    `FACTOR_BOUNDS` and applies it on the log scale (∏ factors). Degrade-neutral: a hook
    that knows nothing about a player returns 1.0 for them (⇒ no-op). Multiple hooks
    compose multiplicatively; each is independently bounded.
    """

    name: str

    def __call__(self, ctx: FactorContext) -> Array: ...


@dataclass(frozen=True)
class LatentContribution:
    """Additive latent contributions (log scale), per player, one per stage.

    `opportunity` and `efficiency` are each shape (n_players,); default 0 = no latent.
    E1-latents supplies low-rank team/player embeddings or a GP over weeks here.
    """

    opportunity: Array
    efficiency: Array


@runtime_checkable
class LatentHook(Protocol):
    """SEAM (E1-latents). Injects additive latent structure into the linear predictors.

    Returns a `LatentContribution` aligned to `data.player_ids`. Degrade-neutral: return
    zeros for players/dims it does not model. Added *before* the likelihood, so latents
    shift the mean, never the observation.
    """

    def __call__(self, data: ModelData) -> LatentContribution: ...


@dataclass(frozen=True)
class Seams:
    """The pre-resolved seam arrays the projector hands the pure model.

    All optional; each defaults to the neutral element. This is the concrete interface
    between hook resolution (projector) and the generative body (`projection_model`).
    """

    factor_log_opp: Array | None = None  # (P,) additive log-multiplier, clamped
    latent_opp: Array | None = None  # (P,) additive on log-opportunity
    latent_eff: Array | None = None  # (P,) additive on log-efficiency
    talent_loc: Array | None = None  # (P,) player-effect prior mean (opportunity)
    talent_scale: Array | None = None  # (P,) player-effect prior scale (opportunity)


# ── the generative model ───────────────────────────────────────────────────────
def _hier_effect(name: str, n: int, prior, plate_scale_name: str):  # noqa: ANN001, ANN202
    """Non-centred hierarchical Normal effect: HalfNormal scale × standard Normal z."""
    scale = numpyro.sample(plate_scale_name, dist.HalfNormal(prior.scale))
    with numpyro.plate(f"{name}_plate", n):
        z = numpyro.sample(f"{name}_z", dist.Normal(0.0, 1.0))
    return numpyro.deterministic(name, prior.loc + scale * z)


def projection_model(
    data: ModelData,
    *,
    priors: dict[str, PriorSet] | None = None,
    seams: Seams | None = None,
    predictive: bool = False,
) -> None:
    """Two-stage 4-level hierarchical model over player-week opportunity/efficiency/points.

    Registers the Dirichlet usage `share`, the separated `mu_opportunity` / `mu_yards`
    layers, `td_rate`, and the epistemic building blocks as deterministic sites so the
    projector can read every layer back from the posterior.

    `predictive=False` (fit): efficiency conditions on the *observed* opportunities and the
    stat sites are observed. `predictive=True` (posterior predictive): opportunities are
    forward-sampled from the Dirichlet-share exposure and efficiency uses that expected
    volume — this is the path that produces per-player-week predictive distributions.
    """
    pr = priors or default_priors()
    sm = seams or Seams()
    opp_pr, eff_pr = pr["opportunity"], pr["efficiency"]

    P = data.n_players
    team_of = jnp.asarray(data.team_of_player)
    pos_of = jnp.asarray(data.pos_of_player)
    obs_player = jnp.asarray(data.obs_player)
    team_plays = jnp.asarray(data.team_plays)
    opp_obs = jnp.asarray(data.opportunities)

    zeros_p = jnp.zeros(P)
    factor_log = sm.factor_log_opp if sm.factor_log_opp is not None else zeros_p
    lat_opp = sm.latent_opp if sm.latent_opp is not None else zeros_p
    lat_eff = sm.latent_eff if sm.latent_eff is not None else zeros_p
    talent_loc = sm.talent_loc if sm.talent_loc is not None else zeros_p
    talent_scale = (
        sm.talent_scale if sm.talent_scale is not None else jnp.full(P, opp_pr.player.scale)
    )

    # ---- OPPORTUNITY: appeal → Dirichlet α → team share → touches ----
    league_opp = numpyro.sample(
        "league_opportunity", dist.Normal(opp_pr.league.loc, opp_pr.league.scale)
    )
    team_opp = _hier_effect("team_opportunity", data.n_teams, opp_pr.team, "team_opp_scale")
    pos_opp = _hier_effect("pos_opportunity", data.n_positions, opp_pr.position, "pos_opp_scale")
    with numpyro.plate("player_opp_plate", P):
        player_opp = numpyro.sample("player_opportunity", dist.Normal(talent_loc, talent_scale))

    appeal = (
        league_opp + team_opp[team_of] + pos_opp[pos_of] + player_opp + lat_opp + factor_log
    )
    alpha = numpyro.deterministic("dirichlet_alpha", jnp.exp(appeal))  # (P,) Dirichlet conc
    team_alpha = jax.ops.segment_sum(alpha, team_of, num_segments=data.n_teams)
    share = numpyro.deterministic("share", alpha / team_alpha[team_of])  # (P,) usage share
    mu_opp = numpyro.deterministic("mu_opportunity", team_plays * share[obs_player])
    opp_conc = numpyro.sample("opp_concentration", dist.HalfNormal(opp_pr.dispersion_scale))
    numpyro.sample(
        "opportunities",
        negbin_family(mu_opp + 1e-3, opp_conc),
        obs=None if predictive else opp_obs,
    )
    # efficiency conditions on observed volume when fitting, expected volume when predicting
    opp_basis = mu_opp if predictive else opp_obs

    # ---- EFFICIENCY: yards-per-opportunity (Gamma) ----
    league_eff = numpyro.sample(
        "league_efficiency", dist.Normal(eff_pr.league.loc, eff_pr.league.scale)
    )
    pos_eff = _hier_effect("pos_efficiency", data.n_positions, eff_pr.position, "pos_eff_scale")
    with numpyro.plate("player_eff_plate", P):
        player_eff = numpyro.sample("player_efficiency", dist.Normal(0.0, eff_pr.player.scale))
    log_ypo = league_eff + pos_eff[pos_of] + player_eff + lat_eff
    ypo = numpyro.deterministic("yards_per_opp", jnp.exp(log_ypo))  # (P,)
    mu_yards = numpyro.deterministic("mu_yards", (opp_basis + 1e-3) * ypo[obs_player])
    yards_conc = numpyro.sample("yards_concentration", dist.HalfNormal(eff_pr.dispersion_scale))
    numpyro.sample(
        "yards",
        gamma_family(mu_yards + 1e-3, yards_conc),
        obs=None if predictive else jnp.asarray(data.yards) + 1e-3,
    )

    # ---- EFFICIENCY: TD rate, regressed HARD toward the positional mean ----
    pos_td_logit = numpyro.sample(
        "pos_td_logit", dist.Normal(-3.0, 1.0).expand([data.n_positions])  # ~5% base rate
    )
    # strong pooling: player TD deviation scale shrinks with td_regression (flags unsustainable TD%)
    with numpyro.plate("player_td_plate", P):
        player_td = numpyro.sample("player_td", dist.Normal(0.0, 1.0 / eff_pr.td_regression))
    td_rate = numpyro.deterministic(
        "td_rate", jax.nn.sigmoid(pos_td_logit[pos_of] + player_td)
    )  # (P,) per-opportunity TD probability
    mu_td = numpyro.deterministic("mu_td", (opp_basis + 1e-3) * td_rate[obs_player])
    numpyro.sample(
        "tds", poisson_family(mu_td), obs=None if predictive else jnp.asarray(data.tds)
    )


def clamp_factor(raw: Array, bounds: tuple[float, float] = FACTOR_BOUNDS) -> Array:
    """Clamp a raw factor multiplier to `bounds` and return its LOG (model works on log).

    `ponytail:` the whole bounded-multiplier contract is one clip + one log — the seam's
    safety guarantee (a factor can never blow a projection up) lives right here.
    """
    return jnp.log(jnp.clip(raw, bounds[0], bounds[1]))
