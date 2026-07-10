"""
Backtest / evidence harness for the E3 advanced-math factors.

Extends the frozen backtest harness the F3 way — a NEW ``test_*`` file, no edit to
``pipeline/backtest/**``. For EACH implemented E3 factor it establishes the two
verdicts the factor catalog records:

  1. NEUTRAL (no regression) — with no ingested context metadata (exactly the state
     of every historical-backtest player) the factor is a true identity, so the
     ensemble projection is byte-identical with and without the E3 factors. This is
     the "does not regress value" guarantee the DoD demands.
  2. HELPS (correct direction) — once ``context_ingest`` supplies weather / venue /
     scheme metadata, the factor moves the projection in the documented direction
     and stays inside its clamp band.

Runnable two ways:
    python tests/test_factor_backtest.py
    python -m pytest tests/test_factor_backtest.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Projection, apply_factors, discover_factors  # noqa: E402
from models.factors import FactorContext  # noqa: E402
from models.factors.environment import (  # noqa: E402
    STADIUMS,
    DomeBoostFactor,
    KickingConditionsFactor,
    WeatherPassingFactor,
    WeatherRushingFactor,
)
from models.factors.scheme import PassRateFactor, TeamPaceFactor  # noqa: E402
from ingest.context_ingest import build_report, ingest, team_metadata  # noqa: E402

_E3 = (
    WeatherPassingFactor, WeatherRushingFactor, KickingConditionsFactor,
    DomeBoostFactor, TeamPaceFactor, PassRateFactor,
)


def _proj(mean=100.0, stdev=20.0) -> Projection:
    return Projection(
        player_id="p1", season=2025, source="ensemble", mean=mean, stdev=stdev,
        floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
    )


def _ctx(position="WR", metadata=None) -> FactorContext:
    return FactorContext(
        player_id="p1", position=position, nfl_team="KC", season=2025,
        metadata=metadata or {},
    )


# ── (1) NEUTRAL: no data ⇒ identity ⇒ zero backtest regression ───────────────
def test_all_e3_factors_are_discovered():
    names = {f.name for f in discover_factors()}
    for cls in _E3:
        assert cls.__name__ in names, (cls.__name__, sorted(names))
    print("✓ all E3 factors auto-discovered:", sorted(cls.__name__ for cls in _E3))


def test_each_factor_is_identity_without_context():
    """No metadata → every E3 factor returns its identity (the historical-backtest
    state: no weather/scheme data). This IS the no-regression evidence."""
    for cls in _E3:
        f = cls()
        for pos in ("QB", "RB", "WR", "TE", "K"):
            assert f.value_for(_ctx(pos)) == f.identity(), (cls.__name__, pos)
    print("✓ every E3 factor is identity with no context (no backtest regression)")


def test_ensemble_projection_unchanged_by_e3_factors():
    """Backtest guarantee: applying the discovered factor set to a context-free
    player leaves the projection byte-identical (net identity)."""
    p = _proj()
    factors = [f for f in discover_factors() if type(f) in _E3]
    assert apply_factors(p, _ctx("WR"), factors) == p
    assert apply_factors(p, _ctx("K"), factors) == p
    print("✓ context-free projection unchanged by the E3 factor set")


# ── (2) HELPS: fed real context ⇒ correct, bounded direction ─────────────────
def test_weather_passing_penalized_in_cold_wind_precip():
    bad = {"temp_f": 15, "wind_mph": 25, "precip": True, "indoor": False}
    m = WeatherPassingFactor().compute(_ctx("WR", {"weather": bad}))
    assert 0.85 <= m < 1.0, m
    # indoor cancels the penalty
    assert WeatherPassingFactor().compute(_ctx("WR", {"weather": {**bad, "indoor": True}})) == 1.0
    print(f"✓ weather passing: harsh outdoor → {m}, indoor → 1.0")


def test_weather_rushing_boosted_when_passing_suppressed():
    bad = {"temp_f": 15, "wind_mph": 25, "precip": True, "indoor": False}
    m = WeatherRushingFactor().compute(_ctx("RB", {"weather": bad}))
    assert 1.0 < m <= 1.04, m
    print(f"✓ weather rushing: harsh outdoor → {m} (mirror of passing)")


def test_dome_boost_only_indoors():
    assert DomeBoostFactor().compute(_ctx("QB", {"weather": {"indoor": True}})) == 1.02
    assert DomeBoostFactor().compute(_ctx("QB", {"weather": {"indoor": False}})) == 1.0
    assert DomeBoostFactor().compute(_ctx("QB")) == 1.0
    print("✓ dome boost: +2% indoors only")


def test_altitude_helps_kickers_at_denver():
    assert STADIUMS["DEN"]["elev"] >= 5000
    hi = KickingConditionsFactor().compute(_ctx("K", {"venue_team": "DEN"}))
    lo = KickingConditionsFactor().compute(_ctx("K", {"venue_team": "MIA"}))
    assert hi > 1.0 and lo == 1.0, (hi, lo)
    print(f"✓ kicking: Denver altitude → {hi}, sea-level → {lo}")


def test_pace_and_pass_rate_move_the_right_way():
    fast = TeamPaceFactor().compute(_ctx("WR", {"team_pace": 70.0}))
    slow = TeamPaceFactor().compute(_ctx("WR", {"team_pace": 56.0}))
    assert fast > 1.0 > slow, (fast, slow)
    heavy_wr = PassRateFactor().compute(_ctx("WR", {"pass_rate": 0.66}))
    heavy_rb = PassRateFactor().compute(_ctx("RB", {"pass_rate": 0.66}))
    assert heavy_wr > 1.0 > heavy_rb, (heavy_wr, heavy_rb)
    print(f"✓ pace {slow}/{fast}; pass-rate WR {heavy_wr} vs RB {heavy_rb}")


def test_effects_are_clamped():
    """Even absurd inputs stay inside each factor's documented band (no runaway)."""
    storm = {"temp_f": -40, "wind_mph": 99, "precip": True, "indoor": False}
    assert WeatherPassingFactor().compute(_ctx("WR", {"weather": storm})) >= 0.85
    assert TeamPaceFactor().compute(_ctx("WR", {"team_pace": 200.0})) <= 1.06
    assert PassRateFactor().compute(_ctx("WR", {"pass_rate": 1.0})) <= 1.05
    print("✓ all effects clamped to their documented bands")


# ── context_ingest: artifact + degrade path ──────────────────────────────────
def test_report_covers_all_teams_and_is_degrade_safe():
    """Offline ingest emits a complete, neutral, self-describing artifact."""
    rep = ingest(2025, week=3, fetch_weather=False)
    assert rep["degraded"] is True and set(rep["teams"]) == set(STADIUMS)
    # a domed team is weather-neutral even with no forecast
    assert rep["teams"]["MIN"]["metadata"]["weather"] == {"indoor": True}
    # an outdoor team with no forecast carries no weather key → factor stays identity
    assert "weather" not in rep["teams"]["GB"]["metadata"]
    print("✓ offline report: 32 teams, degrade-safe, self-describing")


def test_team_metadata_is_factor_ready():
    meta = team_metadata("DEN", {"temp_f": 20, "wind_mph": 18, "precip": False}, {"team_pace": 68.0})
    ctx = _ctx("K", meta)
    # the same metadata drives the real factors end-to-end
    assert KickingConditionsFactor().compute(ctx) != 1.0     # altitude + cold/wind
    assert TeamPaceFactor().compute(_ctx("WR", meta)) > 1.0  # fast pace
    print("✓ team_metadata feeds the factors directly")


def test_build_report_is_deterministic_ignoring_timestamp():
    a = build_report(2025, 1, {}, {})
    b = build_report(2025, 1, {}, {})
    a.pop("generated_at"); b.pop("generated_at")
    assert a == b
    print("✓ report is deterministic (idempotent ingest)")


def main():
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("\nALL E3 FACTOR-BACKTEST TESTS PASSED ✅")


if __name__ == "__main__":
    main()
