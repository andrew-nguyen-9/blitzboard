"""Self-check for the season-long Monte Carlo simulator (v3 Epic 12.2).

Injury must lower season totals, week-to-week variance must widen the interval, a fixed
seed must reproduce, and a calibrated input must land actuals in P10-P90 ≈ 80% of the time.

    python tests/test_season_sim.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SeasonSimulator, SimInput  # noqa: E402
from models.season_sim import injury_rate_for  # noqa: E402


def test_injury_lowers_season_total():
    """Same usage/variance, more injury risk ⇒ lower expected season total + fewer games."""
    healthy = SimInput("healthy", "WR", ppg_mean=15.0, ppg_stdev=6.0, injury_rate=0.0)
    fragile = SimInput("fragile", "WR", ppg_mean=15.0, ppg_stdev=6.0, injury_rate=0.30)
    out = {o.player_id: o for o in SeasonSimulator(n_sims=8000, seed=1).simulate([healthy, fragile])}
    assert out["fragile"].proj_mean < out["healthy"].proj_mean, (out["fragile"], out["healthy"])
    assert out["fragile"].games_exp < out["healthy"].games_exp
    print(f"✓ injury lowers total: fragile={out['fragile'].proj_mean:.0f} < "
          f"healthy={out['healthy'].proj_mean:.0f}")


def test_variance_widens_interval():
    """Same mean/availability, higher per-game σ ⇒ wider P10-P90 boom/bust spread."""
    steady = SimInput("steady", "RB", ppg_mean=12.0, ppg_stdev=2.0, injury_rate=0.05)
    volatile = SimInput("volatile", "RB", ppg_mean=12.0, ppg_stdev=8.0, injury_rate=0.05)
    out = {o.player_id: o for o in SeasonSimulator(n_sims=8000, seed=2).simulate([steady, volatile])}
    assert out["volatile"].boom_bust > out["steady"].boom_bust * 1.5, (out["volatile"], out["steady"])
    print(f"✓ variance widens range: volatile spread={out['volatile'].boom_bust:.0f} "
          f"> steady spread={out['steady'].boom_bust:.0f}")


def test_seed_is_deterministic():
    p = [SimInput("a", "QB", 18.0, 5.0), SimInput("b", "TE", 9.0, 4.0)]
    r1 = SeasonSimulator(n_sims=3000, seed=42).simulate(p)
    r2 = SeasonSimulator(n_sims=3000, seed=42).simulate(p)
    assert [o.proj_mean for o in r1] == [o.proj_mean for o in r2]
    print("✓ seeded season sim is deterministic")


def test_interval_is_calibrated():
    """A genuinely calibrated input: when we sample actual seasons from the SAME process the
    simulator models, ~80% of them must fall inside the predicted P10-P90 band."""
    import numpy as np
    sim = SeasonSimulator(n_sims=20000, seed=7)
    inp = SimInput("p", "WR", ppg_mean=14.0, ppg_stdev=6.0, injury_rate=0.08)
    o = sim.simulate([inp])[0]
    # Draw 5000 "true" seasons from the same generative model and check empirical coverage.
    rng = np.random.default_rng(99)
    avail = 1.0 - injury_rate_for("WR", 0.08)
    games = rng.binomial(17, avail, size=5000).astype(float)
    actual = np.clip(rng.normal(games * 14.0, np.sqrt(games) * 6.0), 0.0, None)
    coverage = float(((actual >= o.floor) & (actual <= o.ceiling)).mean())
    assert 0.74 <= coverage <= 0.86, coverage
    print(f"✓ P10-P90 interval calibrated: coverage={coverage:.2f} (≈0.80)")


def main():
    test_injury_lowers_season_total()
    test_variance_widens_interval()
    test_seed_is_deterministic()
    test_interval_is_calibrated()
    print("\nALL SEASON-SIM TESTS PASSED ✅")


if __name__ == "__main__":
    main()
