"""`HierarchicalProjector` — the NUTS runner + posterior-predictive projection surface.

This is the engine's implementation of the spine `Projector` (ARCHITECTURE.md §Core
abstractions): it emits **distributions** per player-week, not point estimates. It:

  1. resolves the extension seams (factor / latent / talent hooks → plain arrays),
  2. fits the `projection_model` with NumPyro **NUTS** (JAX-CPU, float32, sequential
     chains — the M1/16 GB budget: chains stream one at a time, never all in RAM),
  3. runs the HARD convergence `gate` (R-hat / ESS / divergences) — a failed fit RAISES
     and can never reach a snapshot,
  4. draws the posterior predictive per player-week, splitting **epistemic** (parameter)
     from **aleatoric** (irreducible) uncertainty, and exposing the opportunity /
     efficiency / Dirichlet-share layers separately,
  5. writes raw draws → local Parquet (via `ParquetStore`) and quantiles+summaries → the
     `Snapshot` tables (raw draws NEVER leave the local box).

`walk_forward_compare` is the *minimal* backtest the brief requires: fit on the earlier
weeks, predict the held-out week, and assert the hierarchical engine does not regress
against a shrink-to-mean baseline (the behaviour of the interim pipeline projector). E7
generalises this into the full ablation / benchmark harness.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import jax
import jax.numpy as jnp
import numpy as np
import pandas as pd
from numpyro.infer import MCMC, NUTS, Predictive, init_to_median

from blitz_engine.config import EngineConfig, load_config
from blitz_engine.projection.convergence import ConvergenceReport, gate
from blitz_engine.projection.families import ScoringWeights
from blitz_engine.projection.model import (
    FACTOR_BOUNDS,
    FactorContext,
    ModelData,
    Seams,
    clamp_factor,
    projection_model,
)
from blitz_engine.projection.priors import PriorSet, default_priors

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from blitz_engine.projection.model import FactorHook, LatentHook
    from blitz_engine.projection.priors import TalentPriorHook
    from blitz_engine.snapshot import Snapshot
    from blitz_engine.store import ParquetStore

__all__ = [
    "BacktestResult",
    "HierarchicalProjector",
    "Projection",
    "walk_forward_compare",
]

# posterior-predictive return sites (sampled stats + the readable-back layers)
_RETURN_SITES = (
    "opportunities", "yards", "tds",
    "mu_opportunity", "mu_yards", "mu_td",
    "yards_per_opp", "td_rate", "share", "dirichlet_alpha",
)


@dataclass
class Projection:
    """Per-player-week posterior-predictive output — the projector's product.

    `quantiles` is the publishable per-row distribution (floor/ceiling/tails + the
    epistemic/aleatoric split); `shares` is the per-player Dirichlet usage accessor E2
    redistributes from; `opportunity`/`efficiency` expose the two stages separately.
    `draws_path` points at the local Parquet of raw points draws (None if not persisted).
    """

    quantiles: pd.DataFrame
    shares: pd.DataFrame
    opportunity: pd.DataFrame
    efficiency: pd.DataFrame
    convergence: ConvergenceReport
    draws_path: Path | None = None

    def to_snapshot(self, **kw: object) -> Snapshot:
        """Assemble a `Snapshot` (values = quantiles, quantiles = quantiles). Corr/mc left
        to E3; passes through any extra Snapshot kwargs (version, as_of…)."""
        from blitz_engine.snapshot import Snapshot

        empty = pd.DataFrame()
        return Snapshot(
            values=self.quantiles,
            quantiles=self.quantiles,
            corr_matrix=empty,
            mc_probs=empty,
            **kw,  # type: ignore[arg-type]
        )


@dataclass
class BacktestResult:
    """Walk-forward compare verdict: hierarchical engine vs a shrink-to-mean baseline."""

    engine_mae: float
    baseline_mae: float
    holdout_week: int
    n_players: int
    tolerance: float = 0.02

    @property
    def no_regression(self) -> bool:
        """True iff the engine is no worse than the baseline (within tolerance)."""
        return self.engine_mae <= self.baseline_mae * (1.0 + self.tolerance)


class HierarchicalProjector:
    """Fit + posterior-predict the two-stage hierarchical core; the spine `Projector`.

    Seams are dependency-injected: pass a `talent_prior` hook (E1-talent), `latent` hook
    (E1-latents) and/or `factors` (E1-factors). All default to neutral, so the base engine
    runs standalone. Nothing here implements those models — it only wires their outputs
    into the generative core.
    """

    def __init__(
        self,
        config: EngineConfig | None = None,
        *,
        priors: dict[str, PriorSet] | None = None,
        scoring: dict | None = None,
        factors: Sequence[FactorHook] = (),
        latent: LatentHook | None = None,
        talent_prior: TalentPriorHook | None = None,
        floor_ceiling: tuple[float, float] = (0.10, 0.90),
        tails: tuple[float, float] = (0.01, 0.99),
    ) -> None:
        self.config = config or load_config()
        self.priors = priors or default_priors()
        self.weights = ScoringWeights.from_scoring(scoring or {})
        self.factors = tuple(factors)
        self.latent = latent
        self.talent_prior = talent_prior
        self.floor_ceiling = floor_ceiling
        self.tails = tails
        self._mcmc: MCMC | None = None
        self._data: ModelData | None = None
        self._seams: Seams = Seams()
        self._report: ConvergenceReport | None = None

    # -- seam resolution (hooks → plain arrays the pure model consumes) --------
    def _resolve_seams(self, data: ModelData, context: dict | None = None) -> Seams:
        """Turn injected hooks into the neutral-by-default `Seams` arrays.

        Every hook is optional and MUST degrade to neutral for unknown players; this method
        also enforces the factor bound (`clamp_factor`) so a factor can never blow up a fit.
        """
        P = data.n_players
        seams = Seams()

        if self.factors:
            ctx = FactorContext(data=data, context=context or {})
            log_mult = jnp.zeros(P)
            for hook in self.factors:
                log_mult = log_mult + clamp_factor(jnp.asarray(hook(ctx)), FACTOR_BOUNDS)
            seams = _replace(seams, factor_log_opp=log_mult)

        if self.latent is not None:
            contrib = self.latent(data)
            seams = _replace(
                seams,
                latent_opp=jnp.asarray(contrib.opportunity),
                latent_eff=jnp.asarray(contrib.efficiency),
            )

        if self.talent_prior is not None:
            default_scale = self.priors["opportunity"].player.scale
            tp = self.talent_prior(data.player_ids, "opportunity", default_scale)
            seams = _replace(
                seams, talent_loc=jnp.asarray(tp.loc), talent_scale=jnp.asarray(tp.scale)
            )

        return seams

    # -- fit -------------------------------------------------------------------
    def fit(
        self,
        data: ModelData,
        *,
        num_warmup: int = 500,
        num_samples: int = 500,
        num_chains: int = 2,
        context: dict | None = None,
        enforce_gate: bool = True,
        target_accept_prob: float = 0.9,
    ) -> ConvergenceReport:
        """Run NUTS and (by default) enforce the HARD convergence gate.

        Chains run sequentially (`chain_method="sequential"`) to hold the 16 GB budget.
        Returns the convergence report; RAISES `ConvergenceError` when `enforce_gate` and
        the fit is unconverged — that is the publish block.
        """
        seams = self._resolve_seams(data, context)
        kernel = NUTS(
            projection_model, target_accept_prob=target_accept_prob, init_strategy=init_to_median
        )
        mcmc = MCMC(
            kernel,
            num_warmup=num_warmup,
            num_samples=num_samples,
            num_chains=num_chains,
            chain_method="sequential",
            progress_bar=False,
        )
        mcmc.run(
            jax.random.PRNGKey(self.config.seed),
            data,
            priors=self.priors,
            seams=seams,
            extra_fields=("diverging",),
        )
        self._mcmc, self._data, self._seams = mcmc, data, seams

        grouped = mcmc.get_samples(group_by_chain=True)
        n_div = int(np.asarray(mcmc.get_extra_fields()["diverging"]).sum())
        report = gate(grouped, n_divergences=n_div) if enforce_gate else _check(grouped, n_div)
        self._report = report
        return report

    # -- predict ---------------------------------------------------------------
    def predict(
        self, data: ModelData | None = None, *, store: ParquetStore | None = None,
        draws_table: str = "projection_draws",
    ) -> Projection:
        """Posterior-predictive distributions per player-week (+ epistemic/aleatoric split).

        Uses the same player universe/indexing the fit saw. Writes raw points draws to the
        local `store` when given (never exported), and always returns the quantile summary.
        """
        if self._mcmc is None or self._report is None:
            raise RuntimeError("call fit() before predict()")
        data = data if data is not None else self._data
        assert data is not None
        seams = self._resolve_seams(data)

        samples = self._mcmc.get_samples()
        pred = Predictive(
            projection_model, posterior_samples=samples, return_sites=list(_RETURN_SITES)
        )
        draws = pred(
            jax.random.PRNGKey(self.config.seed + 1),
            data, priors=self.priors, seams=seams, predictive=True,
        )

        w = self.weights
        # full predictive points (epistemic + aleatoric) from sampled stats
        points = np.asarray(w.points(yards=draws["yards"], tds=draws["tds"]))  # (S, N)
        # mean-only points (epistemic) from the deterministic means
        points_mean = np.asarray(w.points(yards=draws["mu_yards"], tds=draws["mu_td"]))  # (S, N)

        lo, hi = self.floor_ceiling
        tlo, thi = self.tails
        qs = np.quantile(points, [tlo, lo, 0.5, hi, thi], axis=0)  # (5, N)
        mean = points.mean(axis=0)
        epistemic = points_mean.std(axis=0)
        total_var = points.var(axis=0)
        aleatoric = np.sqrt(np.clip(total_var - epistemic**2, 0.0, None))

        pid = [data.player_ids[i] for i in data.obs_player]
        week = data.obs_week if data.obs_week is not None else np.full(data.n_obs, -1)
        quantiles = pd.DataFrame({
            "player_id": pid, "week": week,
            "mean": mean, "p1": qs[0], "floor": qs[1], "p50": qs[2], "ceiling": qs[3], "p99": qs[4],
            "stdev": np.sqrt(total_var), "epistemic_sd": epistemic, "aleatoric_sd": aleatoric,
        })

        # separately-accessible layers (per obs) + the Dirichlet-share accessor (per player)
        opportunity = pd.DataFrame({
            "player_id": pid, "week": week,
            "mu_opportunity": np.asarray(draws["mu_opportunity"]).mean(axis=0),
        })
        efficiency = pd.DataFrame({
            "player_id": pid, "week": week,
            "yards_per_opp": np.asarray(draws["yards_per_opp"]).mean(axis=0)[data.obs_player],
            "td_rate": np.asarray(draws["td_rate"]).mean(axis=0)[data.obs_player],
        })
        shares = pd.DataFrame({
            "player_id": data.player_ids,
            "team": [data.teams[t] for t in data.team_of_player],
            "share": np.asarray(draws["share"]).mean(axis=0),
            "dirichlet_alpha": np.asarray(draws["dirichlet_alpha"]).mean(axis=0),
        })

        draws_path = None
        if store is not None:
            wide = pd.DataFrame(points.T, columns=[f"d{i}" for i in range(points.shape[0])])
            wide.insert(0, "week", week)
            wide.insert(0, "player_id", pid)
            draws_path = store.write_parquet(draws_table, wide)

        return Projection(
            quantiles=quantiles, shares=shares, opportunity=opportunity,
            efficiency=efficiency, convergence=self._report, draws_path=draws_path,
        )

    def project(self, data: ModelData, **fit_kw: object) -> Projection:
        """Convenience: fit then predict on the same data (the one-call spine entrypoint)."""
        self.fit(data, **fit_kw)  # type: ignore[arg-type]
        return self.predict(data)


# -- helpers -------------------------------------------------------------------
def _replace(seams: Seams, **kw: object) -> Seams:
    from dataclasses import replace

    return replace(seams, **kw)  # type: ignore[arg-type]


def _check(grouped: dict, n_div: int) -> ConvergenceReport:
    from blitz_engine.projection.convergence import check

    return check(grouped, n_divergences=n_div)


def _points_from_frame(df: pd.DataFrame, weights: ScoringWeights) -> np.ndarray:
    return np.asarray(
        weights.points(yards=df["yards"].to_numpy(), tds=df["tds"].to_numpy())
    )


# -- minimal walk-forward compare (E7 generalises) -----------------------------
def walk_forward_compare(
    frame: pd.DataFrame,
    *,
    holdout_week: int | None = None,
    config: EngineConfig | None = None,
    scoring: dict | None = None,
    projector_factory: Callable[[], HierarchicalProjector] | None = None,
    tolerance: float = 0.02,
    **fit_kw: object,
) -> BacktestResult:
    """Fit on weeks < `holdout_week`, predict it, and check no-regression vs baseline.

    Baseline = the train **shrink-to-positional-mean** predictor — the regularisation core
    of the interim `pipeline/models/projector.py` (which shrinks a player toward his
    positional mean). The hierarchical engine keeps player-specific usage/efficiency, so it
    should beat that pooled baseline (lower MAE). Returns a `BacktestResult`;
    `.no_regression` is what the DoD test asserts.
    """
    cfg = config or load_config()
    weights = ScoringWeights.from_scoring(scoring or {})
    holdout = holdout_week if holdout_week is not None else int(frame["week"].max())
    train = frame[frame["week"] < holdout]
    test = frame[frame["week"] == holdout]
    common = set(train["player_id"].astype(str)) & set(test["player_id"].astype(str))
    test = test[test["player_id"].astype(str).isin(common)].copy()

    # baseline: shrink each player to his positional train mean (interim projector behaviour)
    train = train.copy()
    train["_pts"] = _points_from_frame(train, weights)
    pos_mean = train.groupby(train["position"].astype(str))["_pts"].mean()
    actual = _points_from_frame(test, weights)
    test_pid = test["player_id"].astype(str).to_numpy()
    test_pos = test["position"].astype(str).to_numpy()
    baseline_pred = np.array([pos_mean.get(p, train["_pts"].mean()) for p in test_pos])
    baseline_mae = float(np.mean(np.abs(baseline_pred - actual)))

    # engine: fit on train universe, predict the holdout rows. A backtest is a diagnostic,
    # not a publish, so the hard convergence gate is off here (the publish path keeps it).
    make = projector_factory or (lambda: HierarchicalProjector(cfg, scoring=scoring))
    proj = make()
    train_data = ModelData.from_frame(train)
    fit_kw.setdefault("enforce_gate", False)
    proj.fit(train_data, **fit_kw)  # type: ignore[arg-type]
    test_data = ModelData.from_frame(train, obs_df=test)
    out = proj.predict(test_data)
    pred_by_pid = out.quantiles.groupby("player_id")["mean"].mean()
    engine_pred = np.array([pred_by_pid.get(p, np.nan) for p in test_pid])
    mask = ~np.isnan(engine_pred)
    engine_mae = float(np.mean(np.abs(engine_pred[mask] - actual[mask])))

    return BacktestResult(
        engine_mae=engine_mae, baseline_mae=baseline_mae,
        holdout_week=holdout, n_players=int(mask.sum()), tolerance=tolerance,
    )
