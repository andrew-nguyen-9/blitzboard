"""E5 — BettingFactor ablation + bound tests, and the odds adapter degrade path.

The headline is the ABLATION test: a projection with vs. without the betting
factor differs by AT MOST the documented ``NUDGE_CAP`` — betting can never swing
the model significantly. No DB, no network — pure asserts, runnable two ways:
    python tests/test_betting_factor.py
    python -m pytest tests/test_betting_factor.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Projection, apply_factors  # noqa: E402
from models.factors import FactorContext  # noqa: E402
from models.factors.betting import NUDGE_CAP, BettingFactor  # noqa: E402
from adapters.odds import OddsAdapter  # noqa: E402


def _ctx(position="WR", betting=None) -> FactorContext:
    meta = {"betting": betting} if betting is not None else {}
    return FactorContext(player_id="p1", position=position, nfl_team="KC", season=2025, metadata=meta)


def _proj(mean=100.0, stdev=20.0) -> Projection:
    return Projection(
        player_id="p1", season=2025, source="ensemble",
        mean=mean, stdev=stdev,
        floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
    )


# ── factor: identity when there is no signal ────────────────────────────────
def test_identity_without_betting_metadata():
    assert BettingFactor().value_for(_ctx()) == 1.0


def test_identity_when_team_total_missing():
    assert BettingFactor().value_for(_ctx(betting={"confidence": 1.0})) == 1.0


def test_identity_off_offense_positions():
    # A defense is outside the whitelist → untouched even with a strong signal.
    assert BettingFactor().value_for(_ctx(position="DEF", betting={"team_total": 35})) == 1.0


# ── factor: bounded no matter how extreme the input ─────────────────────────
def test_multiplier_is_hard_capped():
    for tt in (0, 10, 22.5, 35, 100, 10_000, -50):
        v = BettingFactor().value_for(_ctx(betting={"team_total": tt, "confidence": 1.0}))
        assert 1.0 - NUDGE_CAP <= v <= 1.0 + NUDGE_CAP, (tt, v)


def test_direction_and_confidence_scaling():
    f = BettingFactor()
    hot = f.value_for(_ctx(betting={"team_total": 30, "confidence": 1.0}))
    cold = f.value_for(_ctx(betting={"team_total": 15, "confidence": 1.0}))
    assert hot > 1.0 > cold
    # Confidence 0 collapses the nudge to identity; partial confidence sits between.
    assert f.value_for(_ctx(betting={"team_total": 30, "confidence": 0.0})) == 1.0
    half = f.value_for(_ctx(betting={"team_total": 30, "confidence": 0.5}))
    assert 1.0 < half < hot


# ── ABLATION: with vs without the factor, on a real projection ──────────────
def test_ablation_effect_within_documented_bound():
    """model(with betting) vs model(without) differ by at most NUDGE_CAP."""
    strong = _ctx(betting={"team_total": 33.0, "confidence": 1.0})  # a big favorite
    base = _proj(mean=100.0)
    without = apply_factors(base, strong, [])
    with_bet = apply_factors(base, strong, [BettingFactor()])
    rel = abs(with_bet.mean - without.mean) / without.mean
    assert rel <= NUDGE_CAP + 1e-9, rel
    assert rel > 0  # it DID move (not a silent no-op when a signal exists)
    # And it is logged as its own signal, never folded in silently.
    assert "BettingFactor" in with_bet.by_stat.get("factors", {})


def test_ablation_is_symmetric_and_small():
    underdog = _ctx(betting={"team_total": 12.0, "confidence": 1.0})
    base = _proj(mean=100.0)
    with_bet = apply_factors(base, underdog, [BettingFactor()])
    assert with_bet.mean < 100.0
    assert abs(with_bet.mean - 100.0) / 100.0 <= NUDGE_CAP + 1e-9


# ── odds adapter: F2 degrade + pure normalize ───────────────────────────────
_ODDS_FIXTURE = [{
    "id": "evt1",
    "commence_time": "2025-09-08T00:20:00Z",
    "home_team": "Kansas City Chiefs",
    "away_team": "Baltimore Ravens",
    "bookmakers": [
        {"key": "dk", "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "Kansas City Chiefs", "price": -150},
                {"name": "Baltimore Ravens", "price": 130}]},
            {"key": "spreads", "outcomes": [
                {"name": "Kansas City Chiefs", "point": -3.5},
                {"name": "Baltimore Ravens", "point": 3.5}]},
            {"key": "totals", "outcomes": [
                {"name": "Over", "point": 47.5}, {"name": "Under", "point": 47.5}]},
        ]},
        {"key": "fd", "markets": [
            {"key": "spreads", "outcomes": [{"name": "Kansas City Chiefs", "point": -2.5}]},
            {"key": "totals", "outcomes": [{"name": "Over", "point": 48.5}]},
        ]},
    ],
}]


def test_odds_requires_key_and_degrades():
    os.environ.pop("ODDS_API_KEY", None)
    a = OddsAdapter()
    assert a.requires_key == "ODDS_API_KEY"
    assert a.enabled is False
    assert a.run() == []  # no key → no fetch, no write, no raise


def test_odds_normalize_is_pure_consensus():
    rows = OddsAdapter().normalize(_ODDS_FIXTURE)
    assert len(rows) == 1
    r = rows[0]
    assert r["event_id"] == "evt1"
    assert r["home_spread"] == -3.0   # median(-3.5, -2.5)
    assert r["total"] == 48.0         # median(47.5, 48.5)
    assert r["home_ml"] == -150
    assert r["book_count"] == 2


def test_odds_normalize_degrades_on_junk():
    assert OddsAdapter().normalize(None) == []
    assert OddsAdapter().normalize({}) == []
    assert OddsAdapter().normalize([{"id": "x", "bookmakers": []}]) == []  # no markets → skip


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ok test_betting_factor")
