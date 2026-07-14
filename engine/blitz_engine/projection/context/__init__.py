"""`blitz_engine.projection.context` — E1 context signals over the core seams (E1-core).

Two OPTIONAL, degrade-neutral context providers that plug straight into E1-core's DI seams
without touching the generative model:

    SentimentPrior          sentiment → bounded talent-prior mean NUDGE + variance WIDENER
                            (implements `TalentPriorHook`; VADER fallback ← transformer upgrade)
    VegasGameScriptFactor   a LEARNED nonlinear line→outcome map → bounded opportunity factor
                            (implements `FactorHook`; GATED on ODDS_API_KEY, else neutral)

Both are neutral for any player/team they don't know and switch fully off when their signal
is absent, so a missing sentiment feed or odds key can never worsen the base fit.
"""
from __future__ import annotations

from blitz_engine.projection.context.sentiment import (
    Scored,
    Scorer,
    SentimentPrior,
    SentimentSignal,
    TransformerScorer,
    aggregate_signals,
    resolve_scorer,
    score_and_aggregate,
)
from blitz_engine.projection.context.vegas import (
    GameScriptMapping,
    VegasGameScriptFactor,
    team_lines_from_odds,
)

__all__ = [
    "GameScriptMapping",
    "Scored",
    "Scorer",
    "SentimentPrior",
    "SentimentSignal",
    "TransformerScorer",
    "VegasGameScriptFactor",
    "aggregate_signals",
    "resolve_scorer",
    "score_and_aggregate",
    "team_lines_from_odds",
]
