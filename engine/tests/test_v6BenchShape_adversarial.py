"""Independent C03 shared bench-shape schema, parity, and fallback tests."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "c03_shape", ROOT / "scripts/v6BenchPortfolioPrototype.py"
)
assert SPEC and SPEC.loader
c03 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = c03
SPEC.loader.exec_module(c03)
CANONICAL = ROOT / "fixtures/bench_shape.json"


def valid_artifact() -> dict:
    composition = {"QB": 1, "RB": 1, "WR": 1, "TE": 1, "K": 0, "DST": 0}
    costs = {p: [0.0, 0.5, 1.5, 3.0, 5.0] for p in c03.POSITIONS}
    key = "t10-1qb-half-te0.0-b4-ir0"
    return {
        "schema_version": 2,
        "canonical_source_hash": "a" * 64,
        "rows": {
            key: {
                "league_config_key": key,
                "evidence_status": "interpolated",
                "bench_slots": 4,
                "composition": composition,
                "soft_marginal_costs": costs,
            }
        },
    }


def test_independent_validator_accepts_browser_safe_soft_contract() -> None:
    assert c03.validate_shape_artifact(valid_artifact()) == []


@pytest.mark.parametrize("status", ["interpolated", "unsupported"])
def test_non_measured_rows_cannot_claim_measured_provenance(status: str) -> None:
    artifact = valid_artifact()
    row = next(iter(artifact["rows"].values()))
    row["evidence_status"] = status
    row["n"] = 120
    assert any("claims measured provenance" in e for e in c03.validate_shape_artifact(artifact))


def test_hard_caps_are_forbidden_and_fallback_is_explicitly_soft() -> None:
    artifact = valid_artifact()
    next(iter(artifact["rows"].values()))["hard_caps"] = {"QB": 1}
    assert any("forbidden hard positional caps" in e for e in c03.validate_shape_artifact(artifact))
    fallback = c03.fallback_shape(8, "missing league key")
    assert fallback["degraded"] and fallback["evidence_status"] == "unsupported"
    assert fallback["hard_caps"] is None
    assert all(len(curve) == 9 for curve in fallback["soft_marginal_costs"].values())


def test_missing_and_malformed_evidence_degrades_explicitly() -> None:
    for reason in ("missing league key", "malformed canonical JSON", "hash mismatch"):
        fallback = c03.fallback_shape(4, reason)
        assert fallback["degraded_reason"] == reason
        assert all(
            all(isinstance(x, float) for x in curve)
            for curve in fallback["soft_marginal_costs"].values()
        )


def test_hash_is_exact_and_canonicalization_is_stable() -> None:
    a = {"z": 1, "a": {"y": 2, "x": 3}}
    b = {"a": {"x": 3, "y": 2}, "z": 1}
    assert c03.canonical_json_hash(a) == c03.canonical_json_hash(b)
    assert c03.canonical_json_hash({"z": 2}) != c03.canonical_json_hash(a)


@pytest.mark.xfail(strict=True, reason="C03 unimplemented: canonical fixture is legacy schema v1")
def test_canonical_fixture_satisfies_c03_schema() -> None:
    errors = c03.validate_shape_artifact(json.loads(CANONICAL.read_text()))
    assert errors == []


@pytest.mark.xfail(
    strict=True, reason="C03 unimplemented: browser-safe generated shape artifact absent"
)
def test_generated_typescript_artifact_has_exact_hash_and_no_node_runtime() -> None:
    generated = ROOT / "frontend/lib/generated/benchShape.generated.ts"
    text = generated.read_text()
    canonical = json.loads(CANONICAL.read_text())
    assert canonical["canonical_source_hash"] in text
    assert not any(token in text for token in ("node:", "readFile", "createHash", "process."))


def test_generation_check_mode_exists_and_is_documented() -> None:
    generator = ROOT / "scripts/generateBenchShapeArtifact.py"
    text = generator.read_text()
    assert "--check" in text and "canonical_source_hash" in text


@pytest.mark.xfail(
    strict=True, reason="known regression remains blocked until C03 evidence clears it"
)
def test_blocked_slice_is_explicitly_unsupported_in_canonical_shape() -> None:
    canonical = json.loads(CANONICAL.read_text())
    row = canonical["rows"][c03.BLOCKED_SLICE]
    assert row["evidence_status"] == "unsupported"
