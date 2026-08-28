from __future__ import annotations

import math

import numpy as np
import pytest

from blitz_engine.testing import matrix
from blitz_engine.value.bench_portfolio import (
    BLOCKED_SLICE,
    POSITIONS,
    enumerate_feasible_vectors,
    maximum_hole_coverage,
    measure_portfolio,
    portfolio_score,
    select_portfolio,
)


@pytest.mark.parametrize(("bench", "expected"), [(4, 126), (8, 1287)])
def test_complete_vector_enumeration(bench: int, expected: int) -> None:
    vectors = enumerate_feasible_vectors(bench)
    assert len(vectors) == expected
    assert len({tuple(v[p] for p in POSITIONS) for v in vectors}) == expected
    assert all(sum(v.values()) == bench for v in vectors)


def test_lineup_substitution_is_maximum_matched() -> None:
    vector = {"QB": 1, "RB": 1, "WR": 0, "TE": 0, "K": 0, "DST": 0}
    assert maximum_hole_coverage(vector, ["SUPERFLEX", "FLEX"], "superflex") == 2
    assert maximum_hole_coverage(vector, ["QB", "QB2"], "2qb") == 1


@pytest.mark.parametrize(
    "key",
    [
        "t10-1qb-half-te0.0-b4-ir0",
        "t10-superflex-half-te0.5-b8-ir1",
        "t10-2qb-ppr-te0.0-b8-ir0",
        "t12-1qb-ppr-te0.5-b8-ir0",
        "t12-superflex-std-te0.0-b4-ir1",
        "t12-2qb-half-te0.5-b8-ir1",
        "t14-1qb-half-te0.0-b4-ir1",
        "t14-superflex-ppr-te0.5-b8-ir0",
        BLOCKED_SLICE,
    ],
)
def test_mandatory_selection_conserves_budget_and_costs_are_finite(key: str) -> None:
    row = matrix.by_id(key)
    selected = select_portfolio(row)
    assert sum(selected.composition.values()) == row["bench_slots"]
    assert selected.vectors_evaluated == math.comb(row["bench_slots"] + 5, 5)
    assert all(
        len(curve) == row["bench_slots"] + 1
        for curve in selected.soft_marginal_costs.values()
    )
    assert all(
        np.isfinite(x) and x >= 0
        for curve in selected.soft_marginal_costs.values()
        for x in curve
    )


def test_config_dimensions_are_live() -> None:
    vector = {"QB": 2, "RB": 1, "WR": 1, "TE": 0, "K": 0, "DST": 0}
    one = matrix.by_id("t10-1qb-half-te0.0-b4-ir0")
    sf = matrix.by_id("t12-superflex-std-te0.0-b4-ir1")
    assert portfolio_score(vector, sf) > portfolio_score(vector, one)


def test_c02c_adapter_is_deterministic_on_one_cheap_pair() -> None:
    row = matrix.by_id("t10-1qb-half-te0.0-b4-ir0")
    kw = {"seasons": [2018], "board_seeds": [101], "season_seeds": [202]}
    first = measure_portfolio(row, **kw)
    second = measure_portfolio(row, **kw)
    assert first["selection"] == second["selection"]
    assert first["metrics"] == second["metrics"]
    assert first["lineup_illegal_count"] == second["lineup_illegal_count"] == 0
