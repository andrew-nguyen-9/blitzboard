"""Validation gate (E0-ingest): schema + row-counts + freshness + provenance.

    from blitz_engine.data.validation import gate, DEFAULT_SPECS
    gate(store, DEFAULT_SPECS)   # raises ValidationError → BLOCKS a poisoned model run
"""
from __future__ import annotations

from blitz_engine.data.validation.gate import (
    DEFAULT_SPECS,
    CheckResult,
    TableSpec,
    ValidationError,
    ValidationReport,
    gate,
    validate,
)

__all__ = [
    "DEFAULT_SPECS",
    "CheckResult",
    "TableSpec",
    "ValidationError",
    "ValidationReport",
    "gate",
    "validate",
]
