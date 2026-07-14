"""Altitude / dome factor (ported from ``pipeline/models/factors/environment.py``).

Two static, free-derivable venue effects keyed off where the game is played:

  * **Dome / closed roof** removes weather variance → a small, documented passing bump
    (QB/WR/TE).
  * **Altitude** (Denver, ~5280 ft) thins the air → more scoring/volume for the whole
    skill group.

Venue is resolved from ``ctx.context["venue_team"] = {team_code: host_team_code}`` against
the shared ``STADIUMS`` table. No venue → identity, so it never double-counts with the live
``WeatherFactor`` and is a true no-op on the context-free draft path.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.projection.factors.base import clamp, player_positions, player_teams

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

_PASS = ("QB", "WR", "TE")
_SKILL = ("QB", "RB", "WR", "TE")

# dome = fixed/retractable roof routinely closed; elevation in feet (only Denver is high).
# Keyed by CANONICAL team code. Ported verbatim from the interim pipeline venue table.
STADIUMS: dict[str, dict] = {
    "ARI": {"dome": True, "elev": 1070}, "ATL": {"dome": True, "elev": 1050},
    "BAL": {"dome": False, "elev": 33}, "BUF": {"dome": False, "elev": 600},
    "CAR": {"dome": False, "elev": 751}, "CHI": {"dome": False, "elev": 594},
    "CIN": {"dome": False, "elev": 490}, "CLE": {"dome": False, "elev": 571},
    "DAL": {"dome": True, "elev": 551}, "DEN": {"dome": False, "elev": 5280},
    "DET": {"dome": True, "elev": 600}, "GB": {"dome": False, "elev": 640},
    "HOU": {"dome": True, "elev": 50}, "IND": {"dome": True, "elev": 715},
    "JAX": {"dome": False, "elev": 16}, "KC": {"dome": False, "elev": 910},
    "LAC": {"dome": True, "elev": 130}, "LAR": {"dome": True, "elev": 130},
    "LV": {"dome": True, "elev": 2030}, "MIA": {"dome": False, "elev": 8},
    "MIN": {"dome": True, "elev": 830}, "NE": {"dome": False, "elev": 289},
    "NO": {"dome": True, "elev": 3}, "NYG": {"dome": False, "elev": 7},
    "NYJ": {"dome": False, "elev": 7}, "PHI": {"dome": False, "elev": 39},
    "PIT": {"dome": False, "elev": 728}, "SEA": {"dome": False, "elev": 20},
    "SF": {"dome": False, "elev": 20}, "TB": {"dome": False, "elev": 26},
    "TEN": {"dome": False, "elev": 385}, "WAS": {"dome": False, "elev": 200},
}


class AltitudeDomeFactor:
    """Bounded, degrade-neutral venue (dome + altitude) adjustment to opportunity."""

    name = "altitude_dome"

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        venue = ctx.context.get("venue_team") or {}
        teams = player_teams(ctx.data)
        positions = player_positions(ctx.data)
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        if not isinstance(venue, dict) or not venue:
            return out
        for i, (pos, team) in enumerate(zip(positions, teams, strict=True)):
            vt = venue.get(team)
            st = STADIUMS.get(vt) if isinstance(vt, str) else None
            if not st or pos not in _SKILL:
                continue
            m = 1.0
            if pos in _PASS and st["dome"]:
                m *= 1.02
            if st["elev"] >= 4000:  # thin air → more scoring for the whole offense
                m *= 1.03
            out[i] = clamp(m, 0.98, 1.06)
        return out
