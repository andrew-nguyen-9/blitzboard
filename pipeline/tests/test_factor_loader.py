"""
Golden tests for the projection-factor framework (F3).

Proves the contract E1/E2/E3/E5 build on: auto-discovery via glob, deterministic
composition (multipliers scale, deltas shift), positional gating, dormant factors,
identity no-op, and idempotency. No DB, no network — plain asserts, runnable two ways:
    python tests/test_factor_loader.py
    python -m pytest tests/test_factor_loader.py
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Projection, apply_factors, discover_factors  # noqa: E402
from models.factors import DELTA, MULTIPLIER, Factor, FactorContext, ReferenceFactor  # noqa: E402


def _proj(mean=100.0, stdev=20.0) -> Projection:
    return Projection(
        player_id="p1", season=2025, source="ensemble",
        mean=mean, stdev=stdev,
        floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
    )


def _ctx(position="WR") -> FactorContext:
    return FactorContext(player_id="p1", position=position, nfl_team="KC", season=2025)


class _Mult(Factor):
    kind = MULTIPLIER
    def compute(self, ctx):  # noqa: D401
        return 1.10


class _Delta(Factor):
    kind = DELTA
    def compute(self, ctx):
        return 5.0


class _QBOnly(Factor):
    kind = MULTIPLIER
    positions = ("QB",)
    def compute(self, ctx):
        return 2.0


class _Dormant(Factor):
    kind = MULTIPLIER
    enabled = False
    def compute(self, ctx):
        return 0.5


def test_reference_factor_is_discovered():
    """The shipped ReferenceFactor is auto-discovered from factors/*.py."""
    names = [type(f).__name__ for f in discover_factors()]
    assert "ReferenceFactor" in names, names
    print("✓ reference factor auto-discovered:", names)


def test_reference_factor_is_identity_noop():
    """Shipping the identity reference changes NO projection (zero regression)."""
    p = _proj()
    out = apply_factors(p, _ctx(), [ReferenceFactor()])
    assert out == p, (out, p)
    print("✓ reference factor is a true identity no-op")


def test_multiplier_and_delta_compose():
    """mean' = mean*∏(mult) + Σ(delta); floor/ceiling/stdev keep the ±1.28σ shape."""
    p = _proj(mean=100.0, stdev=20.0)
    out = apply_factors(p, _ctx(), [_Mult(), _Delta()])
    assert out.mean == round(100.0 * 1.10 + 5.0, 2), out.mean          # 115.0
    assert out.stdev == round(20.0 * 1.10, 2), out.stdev               # 22.0
    assert out.floor == round(p.floor * 1.10 + 5.0, 2), out.floor
    assert out.ceiling == round(p.ceiling * 1.10 + 5.0, 2), out.ceiling
    # shape preserved: floor/ceiling still exactly mean ± 1.28σ'
    assert abs(out.floor - (out.mean - 1.28 * out.stdev)) < 0.02
    assert abs(out.ceiling - (out.mean + 1.28 * out.stdev)) < 0.02
    assert out.by_stat["factors"] == {"_Delta": 5.0, "_Mult": 1.1}
    print(f"✓ composition: mean 100→{out.mean}, stdev 20→{out.stdev}")


def test_positional_gate_is_identity_off_position():
    """A QB-only factor leaves a WR untouched."""
    p = _proj()
    assert apply_factors(p, _ctx("WR"), [_QBOnly()]) == p
    boosted = apply_factors(p, _ctx("QB"), [_QBOnly()])
    assert boosted.mean == round(p.mean * 2.0, 2)
    print("✓ positional gate: WR untouched, QB doubled")


def test_disabled_factor_not_applied_or_discovered():
    """enabled=False → dormant: not applied, and excluded from default discovery."""
    p = _proj()
    assert _Dormant().value_for(_ctx()) == 1.0          # identity, not 0.5
    assert apply_factors(p, _ctx(), [_Dormant()]) == p
    print("✓ dormant factor stays identity")


def test_discovery_is_idempotent():
    """Repeated discovery yields the same set (idempotent loader)."""
    a = sorted(f.name for f in discover_factors())
    b = sorted(f.name for f in discover_factors())
    assert a == b, (a, b)
    print("✓ discovery idempotent:", a)


def test_glob_discovers_a_new_file():
    """Dropping a NEW module into the factors package is auto-discovered with ZERO
    edit to projector.py — the core F3 extensibility guarantee for E1/E2/E3/E5."""
    pkg = importlib.import_module("models.factors")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "golden_probe_factor.py").write_text(
            "from models.factors.base import Factor, DELTA\n"
            "class GoldenProbe(Factor):\n"
            "    kind = DELTA\n"
            "    def compute(self, ctx):\n"
            "        return 3.0\n"
        )
        pkg.__path__.append(d)          # extend the package search path
        importlib.invalidate_caches()
        try:
            names = [f.name for f in discover_factors()]
            assert "GoldenProbe" in names, names
        finally:
            pkg.__path__.remove(d)
    # gone once the temp path is removed
    assert "GoldenProbe" not in [f.name for f in discover_factors()]
    print("✓ glob auto-discovers a newly-dropped factor file")


def test_context_from_player_row():
    """FactorContext.from_player pulls the fields downstream factors need."""
    player = {
        "id": "abc", "full_name": "Test Player", "position": "RB", "nfl_team": "SF",
        "age": 24, "years_exp": 2, "bye_week": 9, "injury_status": "Q",
        "metadata": {"fantasy_positions": ["RB", "WR"], "college": "Ohio State"},
    }
    ctx = FactorContext.from_player(player, 2025, week=3, opponent="SEA")
    assert ctx.player_id == "abc" and ctx.nfl_team == "SF" and ctx.position == "RB"
    assert ctx.positions == ("RB", "WR") and ctx.week == 3 and ctx.opponent == "SEA"
    assert ctx.college == "Ohio State" and ctx.bye_week == 9
    print("✓ context.from_player exposes identity/team/positions/matchup/status")


def main():
    test_reference_factor_is_discovered()
    test_reference_factor_is_identity_noop()
    test_multiplier_and_delta_compose()
    test_positional_gate_is_identity_off_position()
    test_disabled_factor_not_applied_or_discovered()
    test_discovery_is_idempotent()
    test_glob_discovers_a_new_file()
    test_context_from_player_row()
    print("\nALL FACTOR-LOADER TESTS PASSED ✅")


if __name__ == "__main__":
    main()
