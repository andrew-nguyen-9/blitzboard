"""The validation gate — runs BEFORE any model, BLOCKS a poisoned store.

A model must not train on a store that is missing a table, missing a column, empty,
stale, duplicated, or unprovenanced. The gate checks all of that and, on any anomaly,
`gate()` RAISES `ValidationError` (non-zero / hard stop) — never a silent pass. This
is the store-level extension of the pipeline's degrade-safe adapter contract: degrade
is fine at the *source* (older seasons flagged), but a poisoned *store* blocks.

Model usage (the one line every training entrypoint runs first):

    from blitz_engine.data.validation import gate, DEFAULT_SPECS
    gate(store, DEFAULT_SPECS)      # raises ValidationError → run aborts
    ...                            # only reached on a clean store

Checks per table: exists · schema (required + provenance columns) · row-count ·
key-uniqueness (catches dup/poison) · provenance non-null · freshness (optional).

`ponytail:` DuckDB answers every check with one aggregate query; no row iteration.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import pyarrow.parquet as pq

from blitz_engine.data.ingest.provenance import (
    INGESTED_AT_COL,
    PROVENANCE_COLS,
    SOURCE_COL,
)

if TYPE_CHECKING:
    from blitz_engine.store import ParquetStore

__all__ = [
    "TableSpec",
    "CheckResult",
    "ValidationReport",
    "ValidationError",
    "validate",
    "gate",
    "DEFAULT_SPECS",
]


class ValidationError(RuntimeError):
    """Raised by `gate()` when the store fails any check. Carries the report."""

    def __init__(self, report: ValidationReport) -> None:
        super().__init__(report.summary())
        self.report = report


@dataclass(frozen=True)
class TableSpec:
    """The contract a store table must satisfy to feed a model."""

    name: str
    required_columns: tuple[str, ...] = ()
    key_columns: tuple[str, ...] = ()
    min_rows: int = 1
    freshness_days: float | None = None  # None → skip the freshness check


@dataclass(frozen=True)
class CheckResult:
    table: str
    check: str
    ok: bool
    detail: str = ""


@dataclass
class ValidationReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.ok]

    def summary(self) -> str:
        if self.ok:
            return f"validation OK ({len(self.results)} checks passed)"
        lines = [f"validation BLOCKED — {len(self.failures)} failure(s):"]
        lines += [f"  ✗ {r.table}.{r.check}: {r.detail}" for r in self.failures]
        return "\n".join(lines)


def _sql_str(path: Path) -> str:
    return str(path).replace("'", "''")


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    """First column of the first row of an aggregate query (never None-indexed)."""
    row = con.execute(sql).fetchone()
    return row[0] if row else None


def _check_table(
    con: duckdb.DuckDBPyConnection, path: Path, spec: TableSpec, now: datetime
) -> list[CheckResult]:
    out: list[CheckResult] = []

    def add(check: str, ok: bool, detail: str = "") -> None:
        out.append(CheckResult(spec.name, check, ok, detail))

    # 1. exists
    if not path.exists():
        add("exists", False, f"missing table file {path.name}")
        return out
    add("exists", True)

    # 2. schema — required + provenance columns present
    columns = set(pq.read_schema(path).names)
    needed = set(spec.required_columns) | set(PROVENANCE_COLS) | set(spec.key_columns)
    missing = sorted(needed - columns)
    add("schema", not missing, f"missing columns {missing}" if missing else "")
    if missing:
        # further checks reference columns that may not exist; stop for this table.
        return out

    src = f"read_parquet('{_sql_str(path)}')"

    # 3. row-count
    n = _scalar(con, f"SELECT COUNT(*) FROM {src}")
    add("row_count", n >= spec.min_rows, f"{n} rows < min {spec.min_rows}" if n < spec.min_rows else "")  # noqa: E501

    # 4. key-uniqueness (catches duplicate / poisoned rows a bad re-ingest would leave)
    if spec.key_columns:
        cols = ", ".join(f'"{k}"' for k in spec.key_columns)
        dups = _scalar(
            con,
            f"SELECT COUNT(*) FROM (SELECT {cols} FROM {src} GROUP BY {cols} HAVING COUNT(*) > 1)",
        )
        detail = f"{dups} duplicated key(s) on {spec.key_columns}" if dups else ""
        add("key_unique", dups == 0, detail)

    # 5. provenance non-null
    nulls = _scalar(
        con,
        f'SELECT COUNT(*) FROM {src} WHERE "{SOURCE_COL}" IS NULL OR "{INGESTED_AT_COL}" IS NULL',
    )
    add("provenance", nulls == 0, f"{nulls} rows missing provenance" if nulls else "")

    # 6. freshness (optional)
    if spec.freshness_days is not None:
        newest = _scalar(con, f'SELECT MAX("{INGESTED_AT_COL}") FROM {src}')
        stale = True
        detail = f"no {INGESTED_AT_COL} values"
        if newest:
            try:
                ts = datetime.fromisoformat(str(newest))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                age = (now - ts).total_seconds() / 86400.0
                stale = age > spec.freshness_days
                detail = f"newest ingest {age:.1f}d old > {spec.freshness_days}d" if stale else ""
            except ValueError:
                detail = f"unparseable timestamp {newest!r}"
        add("freshness", not stale, detail)

    return out


def validate(store: ParquetStore, specs: Sequence[TableSpec]) -> ValidationReport:
    """Run every check for every spec and return a report (does NOT raise).

    Use this when you want to inspect results; use `gate()` to enforce them."""
    now = datetime.now(UTC)
    report = ValidationReport()
    con = duckdb.connect()
    try:
        for spec in specs:
            report.results.extend(_check_table(con, store.path(spec.name), spec, now))
    finally:
        con.close()
    return report


def gate(store: ParquetStore, specs: Sequence[TableSpec]) -> ValidationReport:
    """Validate and BLOCK on any failure. Returns the (passing) report or raises
    `ValidationError`. Every model entrypoint calls this before reading the store."""
    report = validate(store, specs)
    if not report.ok:
        raise ValidationError(report)
    return report


# Default expectations for the nflverse ingest. Advanced feeds carry no `min_rows`
# floor above 1 (older ranges are legitimately thin — degraded, not failed); PBP is
# the spine and must be substantial. Freshness is opt-in per deployment.
DEFAULT_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        "pbp",
        required_columns=("game_id", "play_id", "season", "week"),
        key_columns=("game_id", "play_id"),
        min_rows=1000,
    ),
    TableSpec("ngs_passing", key_columns=("season", "week", "player_gsis_id")),
    TableSpec("ngs_rushing", key_columns=("season", "week", "player_gsis_id")),
    TableSpec("ngs_receiving", key_columns=("season", "week", "player_gsis_id")),
    TableSpec("snap_counts", key_columns=("game_id", "pfr_player_id")),
)
