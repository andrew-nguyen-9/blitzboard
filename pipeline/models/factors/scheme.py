"""
Team-scheme projection factors (E3).

Team-context adjustments — offensive pace and pass/run tendency — that reshape a
player's projection based on how his OFFENSE plays, not just his own line. Both
signals are FREE-derivable from nflverse play-by-play (plays per game, pass rate);
``pipeline/ingest/context_ingest.py`` computes the team aggregates and hydrates
them onto ``ctx.metadata``.

Same E3 degrade rule as ``environment.py``: no team data → identity, never a
crash. Effects are league-relative and clamped, so an average-pace / balanced
offense is a true no-op and only genuine outliers move a projection.
"""
from __future__ import annotations

from .base import MULTIPLIER, Factor, FactorContext

# league baselines (rough, stable public averages) the deltas are measured against
_LEAGUE_PLAYS_PER_GAME = 63.0
_LEAGUE_PASS_RATE = 0.58

_SKILL = ("QB", "RB", "WR", "TE")
_PASS_CATCHERS = ("QB", "WR", "TE")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class TeamPaceFactor(Factor):
    """Fast offenses run more plays → more fantasy volume for every skill player.

    Reads ``ctx.metadata['team_pace']`` (plays/game). Scales linearly around the
    league mean at ~35% pass-through (a 10% pace edge ≈ +3.5% volume), clamped to
    ±6%. Missing pace → identity."""

    kind = MULTIPLIER
    positions = _SKILL

    def compute(self, ctx: FactorContext) -> float:
        pace = ctx.metadata.get("team_pace")
        if not pace:
            return 1.0
        rel = (float(pace) - _LEAGUE_PLAYS_PER_GAME) / _LEAGUE_PLAYS_PER_GAME
        return _clamp(round(1.0 + rel * 0.35, 4), 0.94, 1.06)


class PassRateFactor(Factor):
    """Pass-heavy offenses lift QB/WR/TE and trim RB rushing volume.

    Reads ``ctx.metadata['pass_rate']`` (0-1). Pass-catchers scale UP with pass
    rate over expected, rushers scale DOWN — the two directions of the same team
    tendency. Clamped to ±5%; a balanced offense (league mean) → identity."""

    kind = MULTIPLIER
    positions = _SKILL

    def compute(self, ctx: FactorContext) -> float:
        pr = ctx.metadata.get("pass_rate")
        if not pr:
            return 1.0
        edge = (float(pr) - _LEAGUE_PASS_RATE)            # e.g. +0.05 = pass-heavy
        if ctx.position in _PASS_CATCHERS:
            return _clamp(round(1.0 + edge * 0.6, 4), 0.95, 1.05)
        # RB: rushing volume moves opposite the pass rate
        return _clamp(round(1.0 - edge * 0.6, 4), 0.95, 1.05)
