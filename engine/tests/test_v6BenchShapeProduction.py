from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from blitz_engine.value.bench_shape import fallback_shape, marginal_cost, resolve_bench_shape

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "shape_generator", ROOT / "scripts/generateBenchShapeArtifact.py"
)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generator
SPEC.loader.exec_module(generator)


def _source(path: Path) -> Path:
    composition = {"QB": 1, "RB": 1, "WR": 1, "TE": 1, "K": 0, "DST": 0}
    costs = {p: [float(i) for i in range(5)] for p in composition}
    key = "t10-1qb-half-te0.0-b4-ir0"
    deep_composition = {"QB": 2, "RB": 2, "WR": 2, "TE": 2, "K": 0, "DST": 0}
    deep_costs = {p: [float(i) for i in range(9)] for p in composition}
    deep_key = "t10-1qb-half-te0.0-b8-ir0"
    payload = {
        "schema_version": 1,
        "source_kind": "test",
        "source_receipt": ".orchestrator-v6/experiments/test-source.json",
        "producer_sha": "a" * 40,
        "evaluator_sha": "b" * 40,
        "rows": {
            key: {
                "league_config_key": key,
                "evidence_status": "measured",
                "selection": {"composition": composition, "soft_marginal_costs": costs},
                "n_pairs": 10,
                "seeds": [1],
                "unsupported_reason": None,
            },
            deep_key: {
                "league_config_key": deep_key,
                "evidence_status": "measured",
                "selection": {
                    "composition": deep_composition,
                    "soft_marginal_costs": deep_costs,
                },
                "n_pairs": 10,
                "seeds": [1],
                "unsupported_reason": None,
            },
        },
    }
    path.write_text(json.dumps(payload))
    return path


def _do_not_promote_source(path: Path) -> Path:
    payload = {
        "schema_version": 2,
        "source_kind": "consumer_disposition",
        "source_receipt": ".orchestrator-v6/experiments/test-source-v2.json",
        "disposition": "do_not_promote",
        "interpolation_sources": [],
        "rows": {
            "t10-1qb-half-te0.0-b4-ir0": {
                "league_config_key": "t10-1qb-half-te0.0-b4-ir0",
                "evidence_status": "unsupported",
            }
        },
    }
    path.write_text(json.dumps(payload))
    return path


def test_generator_builds_all_supported_keys_and_exact_hash(tmp_path: Path) -> None:
    source = _source(tmp_path / "source.json")
    artifact = generator.build(source)
    assert artifact["schema_version"] == 2
    assert len(artifact["rows"]) == 216
    assert artifact["rows"]["t10-1qb-half-te0.0-b4-ir0"]["evidence_status"] == "measured"
    assert artifact["rows"]["t12-1qb-half-te0.0-b4-ir0"]["evidence_status"] == "interpolated"


def test_global_do_not_promote_cannot_publish_or_interpolate_guidance(
    tmp_path: Path,
) -> None:
    artifact = generator.build(_do_not_promote_source(tmp_path / "source-v2.json"))
    assert len(artifact["rows"]) == 216
    assert all(row["evidence_status"] == "unsupported" for row in artifact["rows"].values())
    assert all(
        row["provenance"]["nearest_measured_keys"] == []
        for row in artifact["rows"].values()
    )
    resolution = resolve_bench_shape(
        "t10-1qb-half-te0.0-b4-ir0", 4, artifact=artifact
    )
    assert resolution.degraded
    assert resolution.degraded_reason == "unsupported_evidence"


def test_lookup_is_soft_and_degrades_explicitly(tmp_path: Path) -> None:
    artifact = generator.build(_source(tmp_path / "source.json"))
    exact = resolve_bench_shape("t10-1qb-half-te0.0-b4-ir0", 4, artifact=artifact)
    assert not exact.degraded and exact.hard_caps is None
    assert marginal_cost(exact, "RB", 2) == 2.0
    missing = resolve_bench_shape("missing", 8, artifact=artifact)
    assert missing.degraded and missing.evidence_status == "unsupported"
    assert missing.degraded_reason == "missing_league_key" and missing.hard_caps is None


def test_malformed_and_budget_mismatch_fallbacks_are_finite() -> None:
    malformed = resolve_bench_shape("x", 4, artifact={"schema_version": 2, "rows": {}})
    assert malformed.degraded_reason == "missing_league_key"
    fallback = fallback_shape("x", 8, "malformed_artifact")
    assert sum(fallback.composition.values()) == 8
    assert all(all(x >= 0 for x in curve) for curve in fallback.soft_marginal_costs.values())


def test_generator_check_mode_detects_one_byte_drift(tmp_path: Path) -> None:
    source = _source(tmp_path / "source.json")
    fixture = tmp_path / "bench_shape.json"
    typescript = tmp_path / "benchShape.generated.ts"
    command = [
        sys.executable,
        str(ROOT / "scripts/generateBenchShapeArtifact.py"),
        "--source", str(source),
        "--fixture", str(fixture),
        "--typescript", str(typescript),
    ]
    subprocess.run(command, check=True, cwd=ROOT)
    subprocess.run([*command, "--check"], check=True, cwd=ROOT)
    typescript.write_text(typescript.read_text() + " ")
    drift = subprocess.run([*command, "--check"], cwd=ROOT, capture_output=True, text=True)
    assert drift.returncode != 0
    assert "bench-shape drift" in drift.stderr + drift.stdout
