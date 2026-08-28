"""Schema-v2 bench-shape lookup with explicit, soft degradation."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from blitz_engine.value.bench_portfolio import POSITIONS

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/bench_shape.json"


@dataclass(frozen=True)
class BenchShapeResolution:
    league_config_key: str
    evidence_status: str
    composition: dict[str, int]
    soft_marginal_costs: dict[str, tuple[float, ...]]
    provenance: dict[str, Any]
    degraded: bool
    degraded_reason: str | None
    hard_caps: None = None


def fallback_shape(key: str, bench_slots: int, reason: str) -> BenchShapeResolution:
    bench = max(0, int(bench_slots))
    # Stable balanced fallback. Costs are finite opportunity prices, not rejection boundaries.
    counts = {p: 0 for p in POSITIONS}
    order = ("RB", "WR", "QB", "TE", "K", "DST")
    for i in range(bench):
        counts[order[i % len(order)]] += 1
    curves = {p: tuple(round(0.25 * depth, 6) for depth in range(bench + 1)) for p in POSITIONS}
    return BenchShapeResolution(
        league_config_key=key,
        evidence_status="unsupported",
        composition=counts,
        soft_marginal_costs=curves,
        provenance={"kind": "unsupported", "reason": reason},
        degraded=True,
        degraded_reason=reason,
    )


def resolve_bench_shape(
    key: str, bench_slots: int, *, artifact: Mapping[str, Any] | None = None
) -> BenchShapeResolution:
    try:
        data = dict(artifact) if artifact is not None else json.loads(FIXTURE.read_text())
    except (OSError, ValueError, TypeError):
        return fallback_shape(key, bench_slots, "malformed_artifact")
    if data.get("schema_version") != 2:
        return fallback_shape(key, bench_slots, "schema_version_mismatch")
    if artifact is None:
        try:
            receipt = ROOT / str(data["canonical_source_receipt"])
            if hashlib.sha256(receipt.read_bytes()).hexdigest() != data["canonical_source_hash"]:
                return fallback_shape(key, bench_slots, "source_hash_mismatch")
        except (KeyError, OSError, TypeError):
            return fallback_shape(key, bench_slots, "source_hash_mismatch")
    row = data.get("rows", {}).get(key)
    if not isinstance(row, dict):
        return fallback_shape(key, bench_slots, "missing_league_key")
    try:
        composition = {p: int(row["composition"][p]) for p in POSITIONS}
        curves = {p: tuple(float(x) for x in row["soft_marginal_costs"][p]) for p in POSITIONS}
        if sum(composition.values()) != int(bench_slots):
            return fallback_shape(key, bench_slots, "bench_budget_mismatch")
        if any(len(curves[p]) != int(bench_slots) + 1 for p in POSITIONS):
            return fallback_shape(key, bench_slots, "malformed_artifact")
        if not all(math.isfinite(x) for curve in curves.values() for x in curve):
            return fallback_shape(key, bench_slots, "malformed_artifact")
        status = str(row["evidence_status"])
        if status not in {"measured", "interpolated", "unsupported"}:
            return fallback_shape(key, bench_slots, "malformed_artifact")
    except (KeyError, TypeError, ValueError):
        return fallback_shape(key, bench_slots, "malformed_artifact")
    degraded = status == "unsupported"
    return BenchShapeResolution(
        league_config_key=key,
        evidence_status=status,
        composition=composition,
        soft_marginal_costs=curves,
        provenance=dict(row["provenance"]),
        degraded=degraded,
        degraded_reason="unsupported_evidence" if degraded else None,
    )


def marginal_cost(resolution: BenchShapeResolution, position: str, owned_bench_count: int) -> float:
    curve = resolution.soft_marginal_costs.get(position)
    if not curve:
        return 0.0
    depth = min(max(0, int(owned_bench_count)), len(curve) - 1)
    return float(curve[depth])


__all__ = ["BenchShapeResolution", "fallback_shape", "marginal_cost", "resolve_bench_shape"]
