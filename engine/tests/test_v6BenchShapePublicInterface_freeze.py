"""C03 public-interface freeze: cheap structural checks before implementation exists."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / ".orchestrator-v6/prep"
SCHEMA = PREP / "C03-public-interface-v1.schema.json"
TYPES = PREP / "C03-public-interface-v1.ts"
DOC = PREP / "C03-public-interface-v1.md"
POSITIONS = {"QB", "RB", "WR", "TE", "K", "DST"}


def test_frozen_schema_is_closed_version_two_and_soft_only() -> None:
    schema = json.loads(SCHEMA.read_text())
    assert schema["properties"]["schema_version"] == {"const": 2}
    assert schema["additionalProperties"] is False
    assert set(schema["$defs"]["positionCounts"]["required"]) == POSITIONS
    assert set(schema["$defs"]["softMarginalCosts"]["required"]) == POSITIONS
    rendered = json.dumps(schema)
    assert not any(field in rendered for field in ('"hard_caps"', '"lo"', '"hi"'))


def test_evidence_union_prevents_nonmeasured_rows_claiming_samples() -> None:
    defs = json.loads(SCHEMA.read_text())["$defs"]
    assert "n_pairs" in defs["measuredProvenance"]["properties"]
    for name in ("interpolatedProvenance", "unsupportedProvenance"):
        assert "n_pairs" not in defs[name]["properties"]
        assert "seeds" not in defs[name]["properties"]
    assert defs["row"]["properties"]["evidence_status"]["enum"] == [
        "measured", "interpolated", "unsupported"
    ]


def test_typescript_freezes_c04_seam_and_generated_exports_without_node_apis() -> None:
    text = TYPES.read_text()
    for symbol in (
        "ResolveBenchShape", "BenchShapeResolution", "BenchShapeDegradedReason",
        "BENCH_SHAPE_SCHEMA_VERSION", "BENCH_SHAPE_CANONICAL_SOURCE_HASH",
        "BENCH_SHAPE_CANONICAL_SOURCE_RECEIPT", "BENCH_SHAPE_ROWS",
    ):
        assert symbol in text
    assert "readonly hardCaps: null" in text
    assert not any(token in text for token in ("node:", "readFile", "createHash", "process."))


def test_freeze_names_exact_artifact_hash_fallback_and_blocked_slice_rules() -> None:
    text = DOC.read_text()
    for phrase in (
        "fixtures/bench_shape.json",
        "frontend/lib/generated/benchShape.generated.ts",
        "exact raw bytes",
        "soft_marginal_costs",
        "t14-2qb-std-te0.5-b4-ir1",
        "No authoritative C03 experiment",
    ):
        assert phrase in text
