"""
Environmental projection factors (E3).

Game-environment adjustments to a player's projection — temperature, wind,
precipitation, dome/outdoor, elevation — derived from FREE public data
(Open-Meteo weather, a static stadium table). Each factor is a pure ``Factor``
subclass (see ``factors/base.py`` + ``docs/modeling/FACTOR_CONTRACT.md``) and
reads its inputs ONLY from ``ctx.metadata`` (hydrated by
``pipeline/ingest/context_ingest.py``, an F2-style adapter).

DEGRADE CONTRACT (the E3 rule): a factor with no data returns its identity
(multiplier ``1.0`` / delta ``0.0``) — never a crash, never a guess. So in a run
without ingested context every factor here is a true no-op and regresses no
backtest; the adjustments only switch on once ``context_ingest`` supplies weather
+ venue metadata. Effects are clamped to a gentle band so a single game's weather
can never dominate a season projection.

The ``STADIUMS`` table (dome / elevation / lat-lon per canonical NFL team) is the
shared free-derivable venue source; ``context_ingest`` imports it too.
"""
from __future__ import annotations

from .base import DELTA, MULTIPLIER, Factor, FactorContext

# ── static, free-derivable venue data (public knowledge) ────────────────────
# dome = fixed or retractable roof routinely closed (weather-neutral indoors);
# elevation in feet (only Denver is materially high); lat/lon for weather lookup.
# Keyed by CANONICAL team code (post F3 roster-fix, see player_ingest).
STADIUMS: dict[str, dict] = {
    "ARI": {"dome": True,  "elev": 1070, "lat": 33.5277, "lon": -112.2626},
    "ATL": {"dome": True,  "elev": 1050, "lat": 33.7554, "lon": -84.4008},
    "BAL": {"dome": False, "elev": 33,   "lat": 39.2780, "lon": -76.6227},
    "BUF": {"dome": False, "elev": 600,  "lat": 42.7738, "lon": -78.7870},
    "CAR": {"dome": False, "elev": 751,  "lat": 35.2258, "lon": -80.8528},
    "CHI": {"dome": False, "elev": 594,  "lat": 41.8623, "lon": -87.6167},
    "CIN": {"dome": False, "elev": 490,  "lat": 39.0955, "lon": -84.5161},
    "CLE": {"dome": False, "elev": 571,  "lat": 41.5061, "lon": -81.6995},
    "DAL": {"dome": True,  "elev": 551,  "lat": 32.7473, "lon": -97.0945},
    "DEN": {"dome": False, "elev": 5280, "lat": 39.7439, "lon": -105.0201},
    "DET": {"dome": True,  "elev": 600,  "lat": 42.3400, "lon": -83.0456},
    "GB":  {"dome": False, "elev": 640,  "lat": 44.5013, "lon": -88.0622},
    "HOU": {"dome": True,  "elev": 50,   "lat": 29.6847, "lon": -95.4107},
    "IND": {"dome": True,  "elev": 715,  "lat": 39.7601, "lon": -86.1639},
    "JAX": {"dome": False, "elev": 16,   "lat": 30.3239, "lon": -81.6373},
    "KC":  {"dome": False, "elev": 910,  "lat": 39.0489, "lon": -94.4839},
    "LAC": {"dome": True,  "elev": 130,  "lat": 33.9535, "lon": -118.3392},
    "LAR": {"dome": True,  "elev": 130,  "lat": 33.9535, "lon": -118.3392},
    "LV":  {"dome": True,  "elev": 2030, "lat": 36.0909, "lon": -115.1833},
    "MIA": {"dome": False, "elev": 8,    "lat": 25.9580, "lon": -80.2389},
    "MIN": {"dome": True,  "elev": 830,  "lat": 44.9736, "lon": -93.2575},
    "NE":  {"dome": False, "elev": 289,  "lat": 42.0909, "lon": -71.2643},
    "NO":  {"dome": True,  "elev": 3,    "lat": 29.9511, "lon": -90.0812},
    "NYG": {"dome": False, "elev": 7,    "lat": 40.8135, "lon": -74.0745},
    "NYJ": {"dome": False, "elev": 7,    "lat": 40.8135, "lon": -74.0745},
    "PHI": {"dome": False, "elev": 39,   "lat": 39.9008, "lon": -75.1675},
    "PIT": {"dome": False, "elev": 728,  "lat": 40.4468, "lon": -80.0158},
    "SEA": {"dome": False, "elev": 20,   "lat": 47.5952, "lon": -122.3316},
    "SF":  {"dome": False, "elev": 20,   "lat": 37.4030, "lon": -121.9698},
    "TB":  {"dome": False, "elev": 26,   "lat": 27.9759, "lon": -82.5033},
    "TEN": {"dome": False, "elev": 385,  "lat": 36.1665, "lon": -86.7713},
    "WAS": {"dome": False, "elev": 200,  "lat": 38.9077, "lon": -76.8645},
}

# positions whose production runs through the passing game (weather-sensitive)
_PASSGAME = ("QB", "WR", "TE")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _weather(ctx: FactorContext) -> dict | None:
    """The per-game weather blob context_ingest hydrates, or None (→ identity).

    Shape: ``{"temp_f": float, "wind_mph": float, "precip": bool, "indoor": bool}``.
    Any missing key degrades that sub-effect to neutral. Indoor games (dome, roof
    closed) are weather-neutral regardless of the outdoor reading."""
    w = ctx.metadata.get("weather")
    return w if isinstance(w, dict) and w else None


class WeatherPassingFactor(Factor):
    """Cold, wind, and precipitation suppress the passing game (QB/WR/TE).

    Multiplier built from documented directional effects, each clamped small and
    combined multiplicatively, floored at 0.85 so one nasty game can't erase a
    projection. Indoor / no-weather → identity.

    Free source: Open-Meteo forecast (keyless) via context_ingest; backtest verdict
    in docs/modeling/FACTOR_CATALOG.md."""

    kind = MULTIPLIER
    positions = _PASSGAME

    def compute(self, ctx: FactorContext) -> float:
        w = _weather(ctx)
        if w is None or w.get("indoor"):
            return 1.0
        m = 1.0
        temp = w.get("temp_f")
        if temp is not None and temp < 32:                 # freezing: ~1%/5°F below
            m *= 1.0 - _clamp((32 - temp) / 5 * 0.01, 0.0, 0.06)
        wind = w.get("wind_mph")
        if wind is not None and wind > 15:                 # gusty: ~1%/mph over 15
            m *= 1.0 - _clamp((wind - 15) * 0.01, 0.0, 0.08)
        if w.get("precip"):                                # rain/snow
            m *= 0.97
        return _clamp(round(m, 4), 0.85, 1.0)


class WeatherRushingFactor(Factor):
    """Bad passing weather nudges game-script toward the run (RB), a mild boost.

    The mirror of ``WeatherPassingFactor``: capped at +4%, identity indoors / with
    no weather."""

    kind = MULTIPLIER
    positions = ("RB",)

    def compute(self, ctx: FactorContext) -> float:
        w = _weather(ctx)
        if w is None or w.get("indoor"):
            return 1.0
        boost = 0.0
        wind = w.get("wind_mph")
        if wind is not None and wind > 15:
            boost += _clamp((wind - 15) * 0.004, 0.0, 0.02)
        temp = w.get("temp_f")
        if temp is not None and temp < 32:
            boost += 0.01
        if w.get("precip"):
            boost += 0.01
        return _clamp(round(1.0 + boost, 4), 1.0, 1.04)


class KickingConditionsFactor(Factor):
    """Kicker adjustment: wind/cold hurt, altitude (Denver) helps.

    Elevation is read from the static ``STADIUMS`` table via
    ``ctx.metadata['venue_team']`` (the home team code context_ingest resolves for
    the week); no venue → no altitude term. Identity when nothing is known."""

    kind = MULTIPLIER
    positions = ("K",)

    def compute(self, ctx: FactorContext) -> float:
        m = 1.0
        w = _weather(ctx)
        if w is not None and not w.get("indoor"):
            wind = w.get("wind_mph")
            if wind is not None and wind > 15:
                m *= 1.0 - _clamp((wind - 15) * 0.008, 0.0, 0.08)
            temp = w.get("temp_f")
            if temp is not None and temp < 32:
                m *= 1.0 - _clamp((32 - temp) / 5 * 0.005, 0.0, 0.03)
        venue = ctx.metadata.get("venue_team")
        elev = (STADIUMS.get(venue) or {}).get("elev", 0) if venue else 0
        if elev >= 4000:                                   # thin air → longer FGs
            m *= 1.04
        return _clamp(round(m, 4), 0.88, 1.06)


class DomeBoostFactor(Factor):
    """Indoor games remove weather variance → a small, documented passing bump.

    Applies only when ``weather.indoor`` is truthy (dome / closed roof); identity
    everywhere else so it never double-counts with the outdoor weather factors."""

    kind = MULTIPLIER
    positions = _PASSGAME

    def compute(self, ctx: FactorContext) -> float:
        w = _weather(ctx)
        return 1.02 if (w is not None and w.get("indoor")) else 1.0
