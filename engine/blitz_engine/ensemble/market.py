"""Market / consensus as informative prior **and** benchmark — "learn our edge over it".

The Vegas+ADP+FantasyPros consensus is the sharpest cheap signal available, so the ensemble
uses it two ways:

  * as an **informative-prior member** (`MarketBenchmark.member`) that joins the BMA blend —
    the stack starts from the market and only moves off it where its own skill earns the move;
  * as the **benchmark** the blend must beat out-of-sample. `market_edge` walk-forwards the
    ensemble and the raw market line over identical folds and reports our edge (market MAE −
    ensemble MAE) with a paired sign-flip p-value. `beats_market` / truthiness is the release
    signal: if the ensemble can't beat the market it has learned no edge and should be dropped.

`ponytail:` the market predictor is just `backtest.fantasypros_predictor`; the edge test reuses
the E7 `walk_forward` + `paired_permutation_p` machinery — no new stats.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from blitz_engine.backtest import (
    fantasypros_predictor,
    paired_permutation_p,
    walk_forward,
    walk_forward_splits,
)
from blitz_engine.ensemble.members import EnsembleMember, market_member

if TYPE_CHECKING:
    from blitz_engine.backtest.harness import Predictor

__all__ = ["MarketBenchmark", "MarketEdge", "market_edge"]


def _as_predictor(model: Predictor | EnsembleMember) -> Predictor:
    return model.as_predictor() if isinstance(model, EnsembleMember) else model


@dataclass(frozen=True)
class MarketEdge:
    """Our out-of-sample edge over the market line, with a paired-permutation p-value."""

    ensemble_mae: float
    market_mae: float
    p_value: float
    n_obs: int

    @property
    def edge(self) -> float:
        """Market MAE − ensemble MAE; > 0 ⇒ we beat the consensus."""
        return self.market_mae - self.ensemble_mae

    @property
    def beats_market(self) -> bool:
        return self.edge > 0.0

    def __bool__(self) -> bool:
        """Truthy iff the ensemble beats the market — the "we have an edge" release signal."""
        return self.beats_market


def market_edge(
    candidate: Predictor | EnsembleMember,
    market: Predictor | EnsembleMember,
    frame: pd.DataFrame,
    *,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    seed: int = 0,
) -> MarketEdge:
    """Walk-forward `candidate` vs the `market` line on shared folds → our `MarketEdge`."""
    folds = walk_forward_splits(frame, time_col=time_col, min_train_periods=min_train_periods)
    cand = walk_forward(frame, _as_predictor(candidate), scoring=scoring, splits=folds)
    mkt = walk_forward(frame, _as_predictor(market), scoring=scoring, splits=folds)
    p = paired_permutation_p(mkt.errors - cand.errors, seed=seed)
    return MarketEdge(
        ensemble_mae=cand.mae, market_mae=mkt.mae, p_value=float(p), n_obs=int(cand.errors.size)
    )


class MarketBenchmark:
    """Accessor for the consensus line: prior member, benchmark predictor, and edge test.

    `projections` carries `player_id`, the time column, and `points_col` (the consensus points
    per player-season) — the shape `backtest.fantasypros_predictor` consumes.
    """

    def __init__(
        self,
        projections: pd.DataFrame,
        *,
        points_col: str = "proj_points",
        time_col: str = "season",
    ) -> None:
        self._projections = projections
        self._points_col = points_col
        self._time_col = time_col

    def predictor(self) -> Predictor:
        """The raw market line as an E7 `Predictor` (the benchmark)."""
        return fantasypros_predictor(
            self._projections, time_col=self._time_col, points_col=self._points_col
        )

    def member(self, *, name: str = "market", sigma: float | None = None) -> EnsembleMember:
        """The market as an informative-prior ensemble member."""
        return market_member(
            self._projections,
            name=name,
            points_col=self._points_col,
            time_col=self._time_col,
            sigma=sigma,
        )

    def spread(self) -> float:
        """Cross-sectional stdev of the consensus points (a default market sigma)."""
        col = self._projections[self._points_col]
        return float(np.std(col)) if len(col) else 1.0

    def edge_of(
        self,
        candidate: Predictor | EnsembleMember,
        frame: pd.DataFrame,
        *,
        scoring: dict | None = None,
        min_train_periods: int = 1,
        seed: int = 0,
    ) -> MarketEdge:
        """Our out-of-sample edge of `candidate` over this market line on `frame`."""
        return market_edge(
            candidate,
            self.predictor(),
            frame,
            scoring=scoring,
            time_col=self._time_col,
            min_train_periods=min_train_periods,
            seed=seed,
        )
