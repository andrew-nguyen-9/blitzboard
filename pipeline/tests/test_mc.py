"""
Unit tests for predictability-aware Monte Carlo (v2.2.3.1 / VALUE_ENGINE.md).

Volatile (low-ρ) players must get correctly WIDER boom/bust ranges, and K/DEF must
use the same streamer replacement level as VORP so the engine toggle stays coherent.

Plain asserts (no pytest in the venv):  python tests/test_mc.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import LeagueRules, MonteCarloEngine  # noqa: E402
from models.projector import Projection  # noqa: E402

SCORING = {"passing": {"pt_per_yd": 0.04, "td": 4}, "rushing": {"pt_per_yd": 0.1, "td": 6},
           "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6}}
ROSTER = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1, "DST": 1, "K": 1, "_superflex": True}
RULES = LeagueRules(league_id="t", league_size=12, scoring=SCORING, roster_slots=ROSTER)


def _proj(pid, mean, rho=1.0, stdev_frac=0.35):
    stdev = mean * stdev_frac
    return Projection(player_id=pid, season=2025, source="ensemble", mean=mean, stdev=stdev,
                      floor=mean - 1.28 * stdev, ceiling=mean + 1.28 * stdev, predictability=rho)


def test_low_predictability_widens_boom_bust():
    """Two identical WRs except predictability — the volatile one gets a wider
    boom/bust spread once the distributions are predictability-aware."""
    proj, pos = {}, {}
    for i in range(6):  # filler so replacement is well-defined
        proj[f"WR{i}"] = _proj(f"WR{i}", 250, rho=0.9)
        pos[f"WR{i}"] = "WR"
    proj["steady"] = _proj("steady", 250, rho=0.95)
    proj["volatile"] = _proj("volatile", 250, rho=0.20)
    pos["steady"] = pos["volatile"] = "WR"
    res = {v.player_id: v for v in MonteCarloEngine(n_sims=20000, seed=7).compute(proj, pos, RULES)}
    steady_spread = res["steady"].boom - res["steady"].bust
    volatile_spread = res["volatile"].boom - res["volatile"].bust
    assert volatile_spread > steady_spread * 1.15, (volatile_spread, steady_spread)
    print(f"✓ low-ρ widens range: volatile spread={volatile_spread:.0f} "
          f"> steady spread={steady_spread:.0f}")


def test_mc_uses_streamer_replacement_for_kdef():
    """MC replacement for K/DEF matches VORP's streamer level (upper-middle), so the
    two engines price K/DEF coherently."""
    proj, pos = {}, {}
    for i in range(24):
        proj[f"K{i}"] = _proj(f"K{i}", 165 - i * 1.7, rho=0.22, stdev_frac=0.22)
        pos[f"K{i}"] = "K"
    res = {v.player_id: v for v in MonteCarloEngine(n_sims=4000, seed=3).compute(proj, pos, RULES)}
    k_means = sorted(p.mean for p in proj.values())
    median_k = k_means[len(k_means) // 2]
    best_k = min((v for v in res.values()), key=lambda v: v.rank)
    assert best_k.replacement >= median_k, (best_k.replacement, median_k)
    print(f"✓ MC K replacement ≥ median: {best_k.replacement:.1f} ≥ {median_k:.1f}")


def test_seed_makes_mc_deterministic():
    """A fixed seed makes Monte Carlo reproducible (so this suite isn't flaky)."""
    proj = {"a": _proj("a", 200, rho=0.6), "b": _proj("b", 180, rho=0.6)}
    pos = {"a": "RB", "b": "RB"}
    r1 = MonteCarloEngine(n_sims=3000, seed=42).compute(proj, pos, RULES)
    r2 = MonteCarloEngine(n_sims=3000, seed=42).compute(proj, pos, RULES)
    assert [v.value for v in r1] == [v.value for v in r2]
    print("✓ seeded MC is deterministic")


def main():
    test_low_predictability_widens_boom_bust()
    test_mc_uses_streamer_replacement_for_kdef()
    test_seed_makes_mc_deterministic()
    print("\nALL MONTE-CARLO TESTS PASSED ✅")


if __name__ == "__main__":
    main()
