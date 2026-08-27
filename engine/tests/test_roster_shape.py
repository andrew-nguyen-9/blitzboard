"""C03 schema-v2 roster-shape compatibility and soft-cost gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from blitz_engine.testing import matrix
from blitz_engine.value.bench_portfolio import BLOCKED_SLICE, POSITIONS
from blitz_engine.value.bench_shape import marginal_cost, resolve_bench_shape
from blitz_engine.value.roster_shape import bench_bounds, kdst_timing, to_requirements
from blitz_engine.value.roster_solver import Player, solve_roster

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/bench_shape.json"
MANDATORY = [
    "t10-1qb-half-te0.0-b4-ir0",
    "t10-superflex-half-te0.5-b8-ir1",
    "t10-2qb-ppr-te0.0-b8-ir0",
    "t12-1qb-ppr-te0.5-b8-ir0",
    "t12-superflex-std-te0.0-b4-ir1",
    "t12-2qb-half-te0.5-b8-ir1",
    "t14-1qb-half-te0.0-b4-ir1",
    "t14-superflex-ppr-te0.5-b8-ir0",
    BLOCKED_SLICE,
]


def test_schema_v2_is_soft_only_and_blocked_slice_is_explicit() -> None:
    data = json.loads(FIXTURE.read_text())
    assert data["schema_version"] == 2
    assert data["rows"][BLOCKED_SLICE]["evidence_status"] == "unsupported"
    rendered = json.dumps(data)
    assert not any(field in rendered for field in ('"hard_caps"', '"lo"', '"hi"'))


@pytest.mark.parametrize("key", MANDATORY)
def test_mandatory_shapes_conserve_budget_and_costs_are_finite(key: str) -> None:
    row = matrix.by_id(key)
    shape = resolve_bench_shape(key, row["bench_slots"])
    assert sum(shape.composition.values()) == row["bench_slots"]
    assert shape.hard_caps is None
    for position in POSITIONS:
        assert len(shape.soft_marginal_costs[position]) == row["bench_slots"] + 1
        assert marginal_cost(shape, position, row["bench_slots"] + 10) >= 0


@pytest.mark.parametrize("key", MANDATORY[:-1])
def test_measured_mandatory_rows_are_not_degraded(key: str) -> None:
    row = matrix.by_id(key)
    shape = resolve_bench_shape(key, row["bench_slots"])
    assert shape.evidence_status == "measured"
    assert not shape.degraded


def test_blocked_row_degrades_without_becoming_a_cap() -> None:
    shape = resolve_bench_shape(BLOCKED_SLICE, 4)
    assert shape.evidence_status == "unsupported"
    assert shape.degraded_reason == "unsupported_evidence"
    assert shape.hard_caps is None


@pytest.mark.parametrize("row", matrix.all(), ids=lambda row: row["id"])
def test_legacy_bounds_adapter_never_imposes_a_positional_cap(row: dict) -> None:
    bounds = bench_bounds(row)
    bench = int(row["bench_slots"])
    assert bounds.lo == {position: 0 for position in POSITIONS}
    assert bounds.hi == {position: bench for position in POSITIONS}


@pytest.mark.parametrize("key", MANDATORY)
def test_solver_requirements_do_not_translate_soft_costs_to_hard_bounds(key: str) -> None:
    row = matrix.by_id(key)
    requirements = to_requirements(row)
    assert requirements.bench_bounds == ()
    assert requirements.bench_floor() == {}
    assert requirements.bench_ceiling() == {}
    pool = [
        Player(id=f"{position}{index}", position=position, value=float(100 - index))
        for position in POSITIONS
        for index in range(20)
    ]
    lineup = solve_roster(pool, requirements, rounds_remaining=0)
    assert lineup.is_legal


def test_legacy_kdst_timing_is_explicitly_unmeasured_under_v2() -> None:
    timing = kdst_timing(matrix.by_id(MANDATORY[0]))
    assert not timing.measured
    assert timing.confidence == "low"
    assert timing.soft_penalty == 0.0
