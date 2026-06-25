"""
Unit tests for predictability-discounted VORP + streamer replacement
(v2.2.2 / SCORING.md "three coordinated changes", VALUE_ENGINE.md).

Plain asserts (no pytest in the venv):
    python tests/test_vorp_discount.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import LeagueRules, VorpEngine  # noqa: E402
from models.projector import Projection  # noqa: E402
from models.value_engine import f_predictability  # noqa: E402

SCORING = {"passing": {"pt_per_yd": 0.04, "td": 4, "int": -2},
           "rushing": {"pt_per_yd": 0.1, "td": 6},
           "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6}}
ROSTER = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1, "DST": 1, "K": 1, "_superflex": True}
RULES = LeagueRules(league_id="t", league_size=12, scoring=SCORING, roster_slots=ROSTER)


def _proj(pid, mean, rho=1.0, stdev_frac=0.35):
    stdev = mean * stdev_frac
    return Projection(player_id=pid, season=2025, source="ensemble", mean=mean, stdev=stdev,
                      floor=mean - 1.28 * stdev, ceiling=mean + 1.28 * stdev, predictability=rho)


def _run(projections, positions, k=1.0, **kw):
    return {v.player_id: v for v in VorpEngine(discount_k=k, **kw).compute(projections, positions, RULES)}


def test_f_predictability_is_rho_to_the_k():
    """f(ρ)=ρ^k: bounded, monotone-increasing in ρ, and None means no discount."""
    assert f_predictability(1.0, 1.0) == 1.0
    assert abs(f_predictability(0.5, 1.0) - 0.5) < 1e-9
    assert abs(f_predictability(0.5, 2.0) - 0.25) < 1e-9
    assert f_predictability(None, 1.0) == 1.0          # missing ρ ⇒ undiscounted
    assert f_predictability(0.3, 1.0) < f_predictability(0.6, 1.0) < f_predictability(0.9, 1.0)
    assert 0.0 <= f_predictability(0.0, 1.0) <= 1.0
    print("✓ f(ρ)=ρ^k: bounded, monotone, None⇒1.0")


def _offense():
    proj, pos = {}, {}
    for i in range(24):
        for p, base in (("QB", 360), ("RB", 280), ("WR", 270), ("TE", 200)):
            pid = f"{p}{i}"
            proj[pid] = _proj(pid, base - i * 6, rho=0.8)
            pos[pid] = p
    return proj, pos


def _kdef(rho=0.22):
    proj, pos = {}, {}
    for i in range(24):
        kp, dp = f"K{i}", f"D{i}"
        proj[kp] = _proj(kp, 165 - i * 1.7, rho=rho, stdev_frac=0.22)
        proj[dp] = _proj(dp, 150 - i * 2.8, rho=rho, stdev_frac=0.38)
        pos[kp], pos[dp] = "K", "DST"
    return proj, pos


def test_streamer_replacement_lifts_kdef_baseline():
    """K/DEF replacement sits at the streamer percentile (upper-middle), not the
    12th-best — so the gap between 'elite' and 'replacement' collapses."""
    proj, pos = _kdef()
    res = _run(proj, pos)
    k_means = sorted([proj[p].mean for p in proj if pos[p] == "K"])
    median_k = k_means[len(k_means) // 2]
    best_k = min((res[p] for p in res if pos[p] == "K"), key=lambda v: v.rank)
    assert best_k.replacement >= median_k, (best_k.replacement, median_k)
    print(f"✓ streamer replacement ≥ median: K repl={best_k.replacement:.1f} ≥ median={median_k:.1f}")


def test_best_kdef_ranks_in_last_rounds():
    """No K or D/ST should out-rank a startable offensive player (SCORING.md sanity)."""
    proj, pos = _offense()
    kp, kpos = _kdef()
    proj.update(kp); pos.update(kpos)
    res = _run(proj, pos)
    best_kdef_rank = min(res[p].rank for p in res if pos[p] in ("K", "DST"))
    n_offense = sum(1 for p in pos.values() if p in ("QB", "RB", "WR", "TE"))
    assert best_kdef_rank > 24, f"a K/DST ranked {best_kdef_rank} — inside startable range"
    assert best_kdef_rank > n_offense * 0.5
    print(f"✓ best K/DST overall rank = {best_kdef_rank} (well outside startable range)")


def test_bigleg_kicker_edges_ahead_within_band():
    """Bounded league signal: a big-leg kicker beats a weak one — but both stay
    compressed far below a startable offensive player."""
    proj, pos = _offense()
    proj["Kbig"] = _proj("Kbig", 165, rho=0.22, stdev_frac=0.22)
    proj["Kweak"] = _proj("Kweak", 140, rho=0.22, stdev_frac=0.22)
    pos["Kbig"] = pos["Kweak"] = "K"
    res = _run(proj, pos)
    assert res["Kbig"].value > res["Kweak"].value
    mid_rb = res["RB10"].value
    assert res["Kbig"].value < mid_rb, (res["Kbig"].value, mid_rb)
    print(f"✓ big-leg K {res['Kbig'].value:.1f} > weak K {res['Kweak'].value:.1f}, "
          f"both ≪ mid RB {mid_rb:.1f}")


def test_no_offense_reorder_under_uniform_predictability():
    """The discount must not regress offense: with uniform ρ it scales every premium
    by the same factor, so the offensive draft order is identical to undiscounted."""
    proj, pos = _offense()
    undiscounted = _run(proj, pos, k=0.0)   # ρ^0 = 1 ⇒ no discount
    discounted = _run(proj, pos, k=1.0)     # uniform ρ ⇒ constant factor
    order_u = sorted((p for p in pos), key=lambda p: undiscounted[p].rank)
    order_d = sorted((p for p in pos), key=lambda p: discounted[p].rank)
    assert order_u == order_d, "discount reordered offense under uniform ρ"
    print("✓ uniform-ρ discount preserves offensive order (no regression)")


def main():
    test_f_predictability_is_rho_to_the_k()
    test_streamer_replacement_lifts_kdef_baseline()
    test_best_kdef_ranks_in_last_rounds()
    test_bigleg_kicker_edges_ahead_within_band()
    test_no_offense_reorder_under_uniform_predictability()
    print("\nALL VORP-DISCOUNT TESTS PASSED ✅")


if __name__ == "__main__":
    main()
