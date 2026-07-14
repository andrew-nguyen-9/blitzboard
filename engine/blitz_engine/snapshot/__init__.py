"""The versioned snapshot bundle — the engine ↔ world hand-off contract.

Every consumer (frontend, cron `pipeline/publish_snapshot.py`) reads THIS schema.
A snapshot is written as a *directory*: one Parquet per tabular component + a JSON
manifest holding `version`, `as_of` and the non-tabular trees.

    {values, quantiles, corr_matrix, mc_probs, strategy_tree, policy}

Split by trust boundary (see docs/design/v4-engine-architecture.md §"Snapshot"):
    * FULL (local Parquet): everything, including raw posterior draws elsewhere.
    * COMPACT export (Supabase / CDN): `quantiles` + `corr_matrix` only — enough for
      cheap live re-sim in the frontend. Raw draws NEVER leave the local box.

Version policy — FROZEN EARLY, ADDITIVE ONLY: bump `SCHEMA_VERSION` only to *add*
optional fields; never rename or repurpose an existing one. Readers tolerate a newer
minor by ignoring unknown keys; the frontend degrades to last-good + "as of <date>".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

__all__ = ["SCHEMA_VERSION", "Snapshot"]

# Additive bumps only. See module docstring / .done.md version policy.
SCHEMA_VERSION = 1

_TABLES = ("values", "quantiles", "corr_matrix", "mc_probs")
_COMPACT_TABLES = ("quantiles", "corr_matrix")
_MANIFEST = "manifest.json"


@dataclass
class Snapshot:
    """A versioned draft-intelligence bundle.

    Tabular components are pandas DataFrames; `strategy_tree` and `policy` are
    JSON-serializable structures (MCTS tree / RL draft policy).
    """

    values: pd.DataFrame
    quantiles: pd.DataFrame
    corr_matrix: pd.DataFrame
    mc_probs: pd.DataFrame
    strategy_tree: dict = field(default_factory=dict)
    policy: dict = field(default_factory=dict)
    version: int = SCHEMA_VERSION
    as_of: datetime = field(default_factory=lambda: datetime.now(UTC))

    # -- full local round-trip --------------------------------------------
    def write(self, out_dir: str | Path) -> Path:
        """Write the FULL bundle (all tables + trees) to `out_dir`. Returns the dir."""
        d = Path(out_dir).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        for name in _TABLES:
            getattr(self, name).to_parquet(d / f"{name}.parquet")
        (d / _MANIFEST).write_text(json.dumps(self._manifest(), indent=2))
        return d

    @classmethod
    def read(cls, in_dir: str | Path) -> Snapshot:
        """Read a FULL bundle previously written by `write`."""
        d = Path(in_dir).expanduser()
        manifest = json.loads((d / _MANIFEST).read_text())
        tables = {name: pd.read_parquet(d / f"{name}.parquet") for name in _TABLES}
        return cls(
            **tables,
            strategy_tree=manifest.get("strategy_tree", {}),
            policy=manifest.get("policy", {}),
            version=manifest["version"],
            as_of=datetime.fromisoformat(manifest["as_of"]),
        )

    # -- compact export (public tier) -------------------------------------
    def export_compact(self, out_dir: str | Path) -> Path:
        """Write the COMPACT export (quantiles + corr only) for Supabase/CDN.

        Raw draws and heavy trees are deliberately excluded — public consumers get
        only what a cheap live re-sim needs.
        """
        d = Path(out_dir).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        for name in _COMPACT_TABLES:
            getattr(self, name).to_parquet(d / f"{name}.parquet")
        manifest = {"version": self.version, "as_of": self.as_of.isoformat(),
                    "tables": list(_COMPACT_TABLES), "compact": True}
        (d / _MANIFEST).write_text(json.dumps(manifest, indent=2))
        return d

    # -- internals ---------------------------------------------------------
    def _manifest(self) -> dict:
        return {
            "version": self.version,
            "as_of": self.as_of.isoformat(),
            "tables": list(_TABLES),
            "strategy_tree": self.strategy_tree,
            "policy": self.policy,
            "compact": False,
        }
