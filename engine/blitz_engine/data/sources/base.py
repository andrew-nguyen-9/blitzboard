"""Shared engine-source contract — the ONE seam every new v4 source reuses.

This mirrors `pipeline/adapters/base.py`'s degrade contract (present-or-neutral;
a missing key or empty source degrades to neutral, never raises) but targets the
engine's `ParquetStore` rather than Supabase. Adding a source is adding one small
module here that subclasses `EngineSource`, sets its class attrs, and implements
`fetch` + `normalize` — no per-source framework (`ponytail:` `_project` does the
present-or-neutral column mapping once, for all of them).

Contract
--------
* ``requires_key`` names an env var; when it is ABSENT the source is *unavailable*
  and ``run()`` returns a neutral result (0 rows, no fetch, no write, no raise).
  Keyless sources (``requires_key=None``) are always enabled but still degrade: a
  missing/empty payload normalizes to ``[]`` and writes nothing.
* ``normalize`` is PURE and fixture-testable: it maps raw records → table rows,
  filling absent columns with ``None`` (neutral) instead of failing.
* ``fetch`` is the ONLY networked step and is best-effort: any error degrades to an
  empty payload so a flaky/absent source can never crash the run.
* Every written row carries a provenance stamp (``prov_source`` / ``prov_dataset``
  / ``prov_ingested_at``) so downstream E1 factors know where a value came from.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd

from blitz_engine.store import ParquetStore

__all__ = ["EngineSource", "SourceResult"]


@dataclass(frozen=True)
class SourceResult:
    """Outcome of running one source — reports availability WITHOUT failing.

    `available` is False only when a required key is absent (degrade path); a source
    that is available but yields no rows (empty/absent payload) is still a success.
    """

    name: str
    table: str
    available: bool
    rows: int
    keys_present: dict[str, bool] = field(default_factory=dict)
    reason: str | None = None


class EngineSource(ABC):
    """Base for a single engine data source. Subclass, set attrs, implement
    `fetch` + `normalize`; the base handles enable/degrade, provenance and writing."""

    name: str = "unnamed"          # short id, used in logs + run_all() keys
    table: str = ""                # ParquetStore table name to write
    key_cols: Sequence[str] = ()   # columns that must be present for a row to count
    columns: Sequence[str] = ()    # the table's schema (present-or-neutral projection)
    requires_key: str | None = None  # env var the source needs, or None if keyless
    provenance: str = ""           # dataset / URL provenance (stamped on every row)
    free_tier: str = ""            # documented free-tier limit (inline provenance)

    # -- degrade gate ------------------------------------------------------
    @property
    def enabled(self) -> bool:
        """False only when a required key is absent — the degrade default."""
        return self.requires_key is None or bool(os.getenv(self.requires_key))

    def keys_present(self) -> dict[str, bool]:
        """Which required keys are set (empty for keyless sources)."""
        if self.requires_key is None:
            return {}
        return {self.requires_key: bool(os.getenv(self.requires_key))}

    # -- source-specific (implement these) --------------------------------
    @abstractmethod
    def fetch(self) -> object:
        """Return the raw payload. ONLY networked step; only called when enabled.
        Best-effort: degrade to an empty payload rather than raise."""

    @abstractmethod
    def normalize(self, raw: object) -> list[dict]:
        """Map raw payload → table rows. Pure + I/O-free (fixture-testable)."""

    # -- shared helpers ----------------------------------------------------
    def _project(self, raw: object) -> list[dict]:
        """Present-or-neutral projection: keep rows with all `key_cols`, and for each
        take exactly `columns`, filling any missing one with ``None`` (neutral)."""
        if not isinstance(raw, list):
            return []
        rows: list[dict] = []
        for rec in raw:
            if not isinstance(rec, dict):
                continue
            if any(rec.get(k) in (None, "") for k in self.key_cols):
                continue
            rows.append({c: rec.get(c) for c in self.columns})
        return rows

    def _stamp(self, rows: list[dict]) -> list[dict]:
        """Add provenance to every row (idempotent — never overwrites an existing)."""
        now = datetime.now(UTC).isoformat()
        for r in rows:
            r.setdefault("prov_source", self.name)
            r.setdefault("prov_dataset", self.provenance)
            r.setdefault("prov_ingested_at", now)
        return rows

    def write(self, store: ParquetStore, rows: list[dict]) -> int:
        """Provenance-stamp and write rows to the store. Empty → no-op (neutral)."""
        if not rows:
            return 0
        store.write_parquet(self.table, pd.DataFrame(self._stamp(rows)))
        return len(rows)

    def run(self, store: ParquetStore, raw: object | None = None) -> SourceResult:
        """fetch → normalize → write, degrade-safe.

        Pass `raw` to skip the networked fetch (used by tests with fixtures). A
        missing key returns a neutral (unavailable) result; a present-but-empty
        source returns available with 0 rows. Never raises for a missing key/source.
        """
        keys = self.keys_present()
        if not self.enabled:
            return SourceResult(
                self.name, self.table, available=False, rows=0, keys_present=keys,
                reason=f"{self.requires_key} unset — degrade to neutral",
            )
        if raw is None:
            raw = self.fetch()
        rows = self.normalize(raw)
        n = self.write(store, rows)
        return SourceResult(self.name, self.table, available=True, rows=n, keys_present=keys)
