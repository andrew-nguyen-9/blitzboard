"""`blitz_engine.inseason` — the weekly in-season loop (E5).

Three matchup-aware decisions, each reusing an existing engine surface rather than a new model:

    waiver_bandit    Thompson-sampling waiver claims over ROS value posteriors (exploit vs
                     explore; wide posterior = flyer). `waiver.py`
    stream_position  matchup-driven streamer pick, win-prob-framed via the E5 lineup optimiser.
                     `streaming.py`
    propose_trades   fairness + Δequity win-win trade evaluator over E4fix starting-lineup value
                     and E4 equity sensitivity. `trade.py`
"""
from __future__ import annotations

from blitz_engine.inseason.streaming import (
    StreamBoard,
    StreamOption,
    stream_position,
)
from blitz_engine.inseason.trade import (
    TradeEval,
    TradeSide,
    evaluate_trade,
    propose_trades,
)
from blitz_engine.inseason.waiver import (
    WaiverBoard,
    WaiverCandidate,
    WaiverRec,
    waiver_bandit,
)

__all__ = [
    "WaiverCandidate",
    "WaiverRec",
    "WaiverBoard",
    "waiver_bandit",
    "StreamOption",
    "StreamBoard",
    "stream_position",
    "TradeSide",
    "TradeEval",
    "evaluate_trade",
    "propose_trades",
]
