"""Load, hash-verify and structurally validate a frozen promotion manifest.

A manifest is immutable once preregistered: this module only reads. Changing anything requires a
new version file; `validate_manifest` therefore also refuses a manifest whose `status` claims it
was already executed (results never replace preregistration).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

__all__ = [
    "ManifestError",
    "load_manifest",
    "sha256_file",
    "validate_manifest",
    "verify_board_corpus",
]

#: Keys the C05 protocol cannot run without. Absence is a freeze failure, not a default.
REQUIRED_KEYS = (
    "schema_version",
    "status",
    "baseline_sha",
    "hypotheses",
    "arms",
    "pairing",
    "seed_derivation",
    "board_corpus",
    "league_configurations",
    "seasons",
    "held_out_seasons",
    "evaluator",
    "primary_metric",
    "secondary_metrics",
    "ci_method",
    "thresholds",
    "mandatory_high_risk_slices",
    "limits",
    "failure_interpretation",
    "calibration_gates",
)

_ALLOWED_STATUS = ("preregistered", "preregistered_not_executed")


class ManifestError(ValueError):
    """The manifest is missing, malformed, or not in a runnable preregistered state."""


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Read + validate one manifest file; the returned dict also carries its own hash."""
    p = Path(path)
    if not p.is_file():
        raise ManifestError(f"manifest not found: {p}")
    m = json.loads(p.read_text())
    m["_manifest_sha256"] = sha256_file(p)
    m["_manifest_path"] = str(p)
    validate_manifest(m)
    return m


def validate_manifest(m: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in m]
    if missing:
        raise ManifestError(f"manifest missing frozen keys: {missing}")
    if m["status"] not in _ALLOWED_STATUS:
        raise ManifestError(
            f"manifest status {m['status']!r} is not preregistered; "
            "results never replace preregistration"
        )
    if set(m["seasons"]) & set(m["held_out_seasons"]):
        raise ManifestError("fit seasons and held-out seasons overlap")
    thr = m["thresholds"]
    for k in (
        "started_points_ci95_lower",
        "mandatory_slice_no_regression_tolerance",
        "h2h_ci95_lower",
        "playoff_or_championship_ci95_lower",
    ):
        if k not in thr:
            raise ManifestError(f"thresholds missing {k}")


def verify_board_corpus(m: dict[str, Any], repo_root: str | Path) -> list[str]:
    """sha256-check every frozen board-corpus file; returns readable mismatches (empty = ok)."""
    root = Path(repo_root)
    out = []
    for rel, want in m["board_corpus"]["files"].items():
        p = root / rel
        if not p.is_file():
            out.append(f"{rel}: MISSING")
        elif (got := sha256_file(p)) != want:
            out.append(f"{rel}: sha256 {got} != frozen {want}")
    return out
