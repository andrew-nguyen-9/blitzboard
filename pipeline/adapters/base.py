"""Shared external-data adapter contract (F2).

Every free external source is ONE module in this package exposing ONE `Adapter`
subclass. The pipeline finds them by globbing this directory — adding a source is
adding a file, never editing a registry (ponytail: `discover()` iterates the pkg).

Per-adapter shape:  fetch → normalize → persist, wrapped by `run()`, which enforces
the DEGRADE CONTRACT:

  * If the adapter declares `requires_key` and that env var is ABSENT, `run()`
    returns [] and NEVER fetches or writes. Missing key is not an error.
  * Keyless sources (`requires_key=None`) still degrade to a no-op: `persist()`
    delegates to `common.upsert`, which dry-runs when Supabase is unconfigured.
    So re-running any adapter with no backend writes NO partial rows and never
    raises — idempotent by construction.

HTTP + retry/backoff + secret access are REUSED, not reinvented: fetch bodies use
`requests` under `common.retry_api`; persistence uses `common.upsert`; user keys
come from the environment (staged as commented placeholders in the frontend
`.env*.example` files and, at runtime, `pipeline/.env`).
"""
from __future__ import annotations

import importlib
import os
import pkgutil
from abc import ABC, abstractmethod

from common import console, upsert


class Adapter(ABC):
    """Base for a single external source. Subclass, set the class attrs, implement
    `fetch` + `normalize`. Override `persist` only for non-upsert targets."""

    name: str = "unnamed"          # short id, used in logs + run_all() keys
    table: str = ""                # Supabase table to upsert into
    on_conflict: str = ""          # column(s) making the upsert idempotent
    requires_key: str | None = None  # env var name the source needs, or None if keyless
    free_tier: str = ""            # documented free-tier limit (inline provenance)

    @property
    def enabled(self) -> bool:
        """False when a required key is absent — the degrade default."""
        return self.requires_key is None or bool(os.getenv(self.requires_key))

    @abstractmethod
    def fetch(self) -> object:
        """Hit the source and return its raw payload. Only called when `enabled`.
        This is the ONLY networked step; wrap the request in `@common.retry_api`."""

    @abstractmethod
    def normalize(self, raw: object) -> list[dict]:
        """Map the raw payload → rows shaped for `table`. Pure + I/O-free so it is
        unit-testable on a fixture without touching the network."""

    def persist(self, rows: list[dict]) -> int:
        """Idempotent upsert. No-ops (dry-run) when Supabase is unconfigured."""
        return upsert(self.table, rows, on_conflict=self.on_conflict)

    def run(self) -> list[dict]:
        """fetch → normalize → persist with graceful degrade.

        Returns the normalized rows ([] when disabled). Never raises for a missing
        key; never writes partial rows when the backend is absent."""
        if not self.enabled:
            console.print(
                f"[yellow]⚠ {self.name}: {self.requires_key} unset — skipping (degrade path).[/yellow]"
            )
            return []
        rows = self.normalize(self.fetch())
        self.persist(rows)
        return rows


def discover() -> list[Adapter]:
    """Instantiate every concrete `Adapter` subclass in this package.

    Glob-by-directory: a new source is a new file here, no central registration."""
    import adapters  # this package

    found: list[Adapter] = []
    for mod in pkgutil.iter_modules(adapters.__path__):
        if mod.name == "base":
            continue
        m = importlib.import_module(f"adapters.{mod.name}")
        for obj in vars(m).values():
            if isinstance(obj, type) and issubclass(obj, Adapter) and obj is not Adapter:
                found.append(obj())
    return found


def run_all() -> dict[str, int]:
    """Run every discovered adapter (degrade-safe). Returns name → rows produced."""
    return {a.name: len(a.run()) for a in discover()}
