"""
E2 — CollegeProspectFactor golden tests (F3 factor contract).

Proves: auto-discovery, rookie/skill-position gating, identity degrade with no
college context (so NO backtest regresses), bounded shade, and monotonicity in the
prospect score. No DB, no network.

    python tests/test_college_factor.py   |   python -m pytest tests/test_college_factor.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Projection, apply_factors, discover_factors  # noqa: E402
from models.factors import FactorContext  # noqa: E402
from models.factors.college import CollegeProspectFactor, SPREAD  # noqa: E402


def _ctx(position="RB", years_exp=0, score=None) -> FactorContext:
    meta = {}
    if score is not None:
        meta["college_production"] = {"prospect_score": score, "college": "Test U"}
    return FactorContext(
        player_id="p1", position=position, positions=(position,),
        nfl_team="KC", season=2025, years_exp=years_exp, metadata=meta,
    )


def _proj(mean=100.0, stdev=20.0) -> Projection:
    return Projection(
        player_id="p1", season=2025, source="ensemble", mean=mean, stdev=stdev,
        floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
    )


def test_factor_is_discovered():
    names = [type(f).__name__ for f in discover_factors()]
    assert "CollegeProspectFactor" in names, names
    print("✓ college factor auto-discovered")


def test_identity_without_college_context():
    """A rookie with no college_production metadata → identity (the degrade path)."""
    assert CollegeProspectFactor().value_for(_ctx(score=None)) == 1.0
    print("✓ no college context → identity 1.0")


def test_identity_for_non_rookie():
    """A veteran (years_exp > 1) is untouched even WITH a strong college signal."""
    f = CollegeProspectFactor()
    assert f.value_for(_ctx(years_exp=5, score=1.0)) == 1.0
    print("✓ veterans untouched")


def test_identity_off_skill_positions():
    f = CollegeProspectFactor()
    assert f.value_for(_ctx(position="K", score=1.0)) == 1.0
    assert f.value_for(_ctx(position="DEF", score=1.0)) == 1.0
    print("✓ K/DEF untouched")


def test_identity_when_experience_unknown():
    """years_exp None → we never guess rookie status → identity."""
    assert CollegeProspectFactor().value_for(_ctx(years_exp=None, score=1.0)) == 1.0
    print("✓ unknown experience → identity")


def test_neutral_score_is_identity():
    assert CollegeProspectFactor().value_for(_ctx(score=0.5)) == 1.0
    print("✓ neutral prospect_score 0.5 → 1.0")


def test_bounded_and_monotonic():
    f = CollegeProspectFactor()
    lo = f.value_for(_ctx(score=0.0))
    hi = f.value_for(_ctx(score=1.0))
    mid = f.value_for(_ctx(score=0.75))
    assert lo == round(1.0 - SPREAD, 4) and hi == round(1.0 + SPREAD, 4)
    assert lo < 1.0 < mid < hi                      # monotonic increasing in score
    # out-of-range scores are clamped, not extrapolated
    assert f.value_for(_ctx(score=5.0)) == hi
    print(f"✓ bounded [{lo}, {hi}], monotonic, clamped")


def test_composes_onto_projection():
    """End-to-end: a strong prospect lifts a rookie's flat-prior projection."""
    p = _proj(mean=100.0)
    out = apply_factors(p, _ctx(score=1.0), [CollegeProspectFactor()])
    assert out.mean == round(100.0 * (1.0 + SPREAD), 2)
    assert out.by_stat["factors"]["CollegeProspectFactor"] == round(1.0 + SPREAD, 4)
    print("✓ composes onto projection:", out.mean)


def main():
    for fn in [
        test_factor_is_discovered, test_identity_without_college_context,
        test_identity_for_non_rookie, test_identity_off_skill_positions,
        test_identity_when_experience_unknown, test_neutral_score_is_identity,
        test_bounded_and_monotonic, test_composes_onto_projection,
    ]:
        fn()
    print("\nALL COLLEGE-FACTOR TESTS PASSED ✅")


if __name__ == "__main__":
    main()
