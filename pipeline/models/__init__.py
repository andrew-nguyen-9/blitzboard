"""Core modeling abstractions: scoring, LeagueRules, Projector, ValueEngine.

These define the interfaces the whole tool hangs off of (see docs/ARCHITECTURE.md).
P1 ships real projectors + a working VORP engine; Monte Carlo lands in P7.
"""
from .scoring import score_stats, score_kicking, score_defense, POSITION_FLOOR
from .league_rules import LeagueRules, load_league_rules
from .adp import fetch_ffc_adp, positional_order
from .projector import (
    Projection,
    Projector,
    HistoryStore,
    SeasonLine,
    HeuristicProjector,
    RegressionProjector,
    ConsensusProjector,
    EnsembleProjector,
)
from .special_teams import KickerProjector, DefenseProjector
from .predictability import Predictability, td_turnover_share
from .sentiment import SentimentScorer, VaderScorer, PlayerMatcher, SentimentResult
from .value_engine import ValueEngine, VorpEngine, MonteCarloEngine, PlayerValue

__all__ = [
    "score_stats",
    "POSITION_FLOOR",
    "LeagueRules",
    "load_league_rules",
    "Projection",
    "Projector",
    "HistoryStore",
    "SeasonLine",
    "HeuristicProjector",
    "RegressionProjector",
    "ConsensusProjector",
    "EnsembleProjector",
    "KickerProjector",
    "DefenseProjector",
    "Predictability",
    "td_turnover_share",
    "SentimentScorer",
    "VaderScorer",
    "PlayerMatcher",
    "SentimentResult",
    "score_kicking",
    "score_defense",
    "fetch_ffc_adp",
    "positional_order",
    "ValueEngine",
    "VorpEngine",
    "MonteCarloEngine",
    "PlayerValue",
]
