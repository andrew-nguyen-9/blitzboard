"""C03 schema-v2 roster-shape compatibility and soft-cost gates."""

from __future__ import annotations

import hashlib
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
C02C_FIXTURE = ROOT / "fixtures/bench_shape_c02c.json"
C02C_FIXTURE_SHA256 = "b672610e291aa97f5be7853c16c2e53db201f74638257acc40e7c129c46ad2ee"
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


@pytest.mark.parametrize("key", MANDATORY)
def test_uncleared_mandatory_rows_are_unsupported_and_degraded(key: str) -> None:
    row = matrix.by_id(key)
    shape = resolve_bench_shape(key, row["bench_slots"])
    assert shape.evidence_status == "unsupported"
    assert shape.degraded
    assert shape.degraded_reason == "unsupported_evidence"


def test_blocked_row_degrades_without_becoming_a_cap() -> None:
    shape = resolve_bench_shape(BLOCKED_SLICE, 4)
    assert shape.evidence_status == "unsupported"
    assert shape.degraded_reason == "unsupported_evidence"
    assert shape.hard_caps is None


def test_accepted_c02c_bounds_fixture_is_byte_identical() -> None:
    assert hashlib.sha256(C02C_FIXTURE.read_bytes()).hexdigest() == C02C_FIXTURE_SHA256


def _legacy_features(row: dict) -> tuple[float, float, float, float]:
    qb = {"1qb": 1.0, "superflex": 1.5, "2qb": 2.0}.get(str(row["qb_mode"]), 1.0)
    return float(row["teams"]), qb, float(row["bench_slots"]), float(row["ir_slots"])


def _accepted_c02c_bounds(row: dict) -> tuple[dict[str, int], dict[str, int], bool]:
    rows = json.loads(C02C_FIXTURE.read_text())["rows"]
    key = str(row["id"])
    if key in rows:
        bounds = rows[key]["bounds"]
        return dict(bounds["lo"]), dict(bounds["hi"]), True
    want = _legacy_features(row)
    scale = (1.0, 3.0, 0.5, 1.0)

    def distance(record: dict) -> tuple[float, str]:
        got = _legacy_features(record["row"])
        return (
            sum(
                weight * (left - right) ** 2
                for weight, left, right in zip(scale, want, got, strict=True)
            ),
            str(record["bounds"]["row_id"]),
        )

    nearest = min(rows.values(), key=distance)["bounds"]
    bench = int(row["bench_slots"])
    lo = {position: min(int(nearest["lo"][position]), bench) for position in POSITIONS}
    hi = {position: min(int(nearest["hi"][position]), bench) for position in POSITIONS}
    while sum(lo.values()) > bench:
        position = max(
            (candidate for candidate in POSITIONS if lo[candidate] > 0),
            key=lambda candidate: (lo[candidate], candidate),
        )
        lo[position] -= 1
    for position in POSITIONS:
        headroom = bench - (sum(lo.values()) - lo[position])
        hi[position] = max(lo[position], min(hi[position], headroom))
    return lo, hi, False


@pytest.mark.parametrize("row", matrix.all(), ids=lambda row: row["id"])
def test_every_legacy_bound_matches_accepted_c02c(row: dict) -> None:
    expected_lo, expected_hi, expected_measured = _accepted_c02c_bounds(row)
    actual = bench_bounds(row)
    assert actual.lo == expected_lo
    assert actual.hi == expected_hi
    assert actual.measured is expected_measured


@pytest.mark.parametrize("key", ["t10-2qb-ppr-te0.0-b8-ir1", BLOCKED_SLICE])
def test_legacy_bounds_adapter_preserves_measured_c02c_rows(key: str) -> None:
    legacy = json.loads(C02C_FIXTURE.read_text())["rows"][key]
    bounds = bench_bounds(matrix.by_id(key))
    assert bounds.as_dict() == legacy["bounds"]


@pytest.mark.parametrize("key", MANDATORY)
def test_solver_requirements_preserve_accepted_c02c_bounds(key: str) -> None:
    row = matrix.by_id(key)
    requirements = to_requirements(row)
    bounds = bench_bounds(row)
    assert requirements.bench_bounds == bounds.as_pairs()
    assert requirements.bench_floor() == {
        position: value for position, value in bounds.lo.items() if value > 0
    }
    assert requirements.bench_ceiling() == dict(bounds.hi)
    pool = [
        Player(id=f"{position}{index}", position=position, value=float(100 - index))
        for position in POSITIONS
        for index in range(20)
    ]
    lineup = solve_roster(pool, requirements, rounds_remaining=0)
    assert lineup.is_legal


def test_legacy_kdst_timing_preserves_accepted_c02c_measurement() -> None:
    key = "t10-2qb-ppr-te0.0-b8-ir1"
    legacy = json.loads(C02C_FIXTURE.read_text())["rows"][key]["kdst"]
    timing = kdst_timing(matrix.by_id(key))
    assert timing.cap_rounds_from_end == legacy["cap_rounds_from_end"]
    assert timing.soft_penalty == legacy["soft_penalty"]
    assert timing.measured
