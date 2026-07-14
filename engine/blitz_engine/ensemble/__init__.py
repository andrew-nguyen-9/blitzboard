"""`blitz_engine.ensemble` — the stacked, BMA-weighted model ensemble (E8 surfaces read this).

The projection core (E1) is one member of an ensemble, not the whole model. This package
blends diverse base learners into a single calibrated forecast that must beat every member —
and the market — out of sample, or it is dropped (the brief's block-release rule):

    from blitz_engine.ensemble import (
        StackedEnsemble, gbm_member, nn_member, bayesian_member, MarketBenchmark,
    )

    market = MarketBenchmark(consensus_df)                 # Vegas+ADP+FantasyPros
    members = [bayesian_member(scoring), gbm_member(scoring),
               nn_member(scoring), market.member()]        # 4-family roster
    ens = StackedEnsemble(members=members, scoring=scoring) # BMA-weighted by OOS skill

    assert calibrated(ens.quantiles(train, test), y)       # E7 calibration gate
    assert no_regression(ens.as_predictor(), frame=hist, scoring=scoring)
    assert market.edge_of(ens.as_predictor(), hist, scoring=scoring)   # we beat the market

Surfaces:
  * **members** — `bayesian_member` (E1 core), `gbm_member` (LightGBM|numpy GBRT),
    `nn_member` (torch MLP), `market_member`; all `EnsembleMember`s emitting
    `MemberPrediction(mean, stdev)` and usable as E7 predictors via `.as_predictor()`.
  * **BMA** — `bma_weights` (softmax of per-member OOS log-score; Σ=1), `bma_skill`.
  * **stack** — `StackedEnsemble` / `ensemble_predictor` (convex Gaussian-mixture blend),
    `quantiles_frame` (→ `calibrated()`).
  * **market** — `MarketBenchmark` (prior member + benchmark accessor), `market_edge`.
"""
from __future__ import annotations

from blitz_engine.ensemble.bma import bma_skill, bma_weights, softmax_weights
from blitz_engine.ensemble.market import MarketBenchmark, MarketEdge, market_edge
from blitz_engine.ensemble.members import (
    CallableMember,
    EnsembleMember,
    GBMMember,
    MemberPrediction,
    NNMember,
    PredictorMember,
    bayesian_member,
    gbm_member,
    market_member,
    nn_member,
)
from blitz_engine.ensemble.stack import StackedEnsemble, ensemble_predictor, quantiles_frame

__all__ = [
    "CallableMember",
    "EnsembleMember",
    "GBMMember",
    "MarketBenchmark",
    "MarketEdge",
    "MemberPrediction",
    "NNMember",
    "PredictorMember",
    "StackedEnsemble",
    "bayesian_member",
    "bma_skill",
    "bma_weights",
    "ensemble_predictor",
    "gbm_member",
    "market_edge",
    "market_member",
    "nn_member",
    "quantiles_frame",
    "softmax_weights",
]
