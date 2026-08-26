"""Independent C03 complete-vector adversarial contract tests."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "c03_portfolio", ROOT / "scripts/v6BenchPortfolioPrototype.py"
)
assert SPEC and SPEC.loader
c03 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = c03
SPEC.loader.exec_module(c03)


@pytest.mark.parametrize("budget", [4, 8])
def test_enumerates_every_complete_budget_conserving_vector(budget: int) -> None:
    vectors = c03.enumerate_vectors(budget)
    assert len(vectors) == math.comb(budget + 5, 5)
    assert len({tuple(v[p] for p in c03.POSITIONS) for v in vectors}) == len(vectors)
    assert all(sum(v.values()) == budget and min(v.values()) >= 0 for v in vectors)


def test_flex_and_superflex_substitution_use_maximum_matching() -> None:
    vector = {"QB": 1, "RB": 1, "WR": 0, "TE": 0, "K": 0, "DST": 0}
    assert c03.maximum_hole_coverage(vector, ["QB", "FLEX"], "1qb") == 2
    assert c03.maximum_hole_coverage(vector, ["SUPERFLEX", "FLEX"], "superflex") == 2
    assert c03.maximum_hole_coverage(vector, ["QB", "QB2"], "2qb") == 1


def test_superflex_and_2qb_scarcity_raise_qb_portfolio_value() -> None:
    v = {"QB": 2, "RB": 1, "WR": 1, "TE": 0, "K": 0, "DST": 0}
    one = c03.League("one", 12, "1qb", 4, 0.0, 0)
    sf = c03.League("sf", 12, "superflex", 4, 0.0, 0)
    two = c03.League("two", 12, "2qb", 4, 0.0, 0)
    assert c03.portfolio_score(v, sf) > c03.portfolio_score(v, one)
    assert c03.portfolio_score(v, two) > c03.portfolio_score(v, sf)


def test_starter_fragility_ir_and_waiver_replaceability_are_live() -> None:
    v = {"QB": 1, "RB": 2, "WR": 1, "TE": 0, "K": 0, "DST": 0}
    shallow = c03.League("shallow", 10, "1qb", 4, 0.0, 1)
    scarce = c03.League("scarce", 14, "1qb", 4, 0.0, 1)
    no_ir = c03.League("no-ir", 10, "1qb", 4, 0.0, 0)
    assert c03.portfolio_score(v, scarce) > c03.portfolio_score(v, shallow)
    assert c03.portfolio_score(v, no_ir) > c03.portfolio_score(v, shallow)


def test_te_premium_and_contingency_correlation_are_live_soft_terms() -> None:
    balanced = {"QB": 1, "RB": 1, "WR": 1, "TE": 1, "K": 0, "DST": 0}
    correlated = {"QB": 0, "RB": 4, "WR": 0, "TE": 0, "K": 0, "DST": 0}
    standard = c03.League("std", 12, "1qb", 4, 0.0, 0)
    premium = c03.League("tep", 12, "1qb", 4, 0.5, 0)
    assert c03.portfolio_score(balanced, premium) > c03.portfolio_score(balanced, standard)
    assert c03.portfolio_score(balanced, standard) > c03.portfolio_score(correlated, standard)


@pytest.mark.parametrize("league", c03.MANDATORY_SYNTHETIC, ids=lambda x: x.key)
def test_complete_optimizer_is_feasible_and_old_independent_optima_are_not(league) -> None:
    vector, score = c03.best_complete_vector(league)
    old = c03.old_independent_bound_vector(league)
    assert sum(vector.values()) == league.bench_slots
    assert math.isfinite(score)
    assert sum(old.values()) != league.bench_slots, "counterfactual unexpectedly became a portfolio"


def test_blocked_slice_is_present_and_never_promoted_by_synthetic_receipt() -> None:
    receipt = c03.run_receipt()
    row = next(r for r in receipt["rows"] if r["league"]["key"] == c03.BLOCKED_SLICE)
    assert row["evidence_status"] == "unsupported"
    assert receipt["kind"] == "synthetic_not_promotion_evidence"
