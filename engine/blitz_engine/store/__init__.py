"""DuckDB + memory-mapped Parquet store — THE data-access seam.

E0-ingest fills this store with 2014+ play-by-play; every model *reads* through it.
The contract (see docs/design/v4-engine-architecture.md §"M1 / 16 GB budget"):

    * Never load full history into RAM. Reads are memory-mapped (DuckDB scans Parquet
      on disk; `read_chunks` streams RecordBatches via pyarrow `memory_map`).
    * Tables are named Parquet files under one root dir; DuckDB queries them by name.

`ponytail:` DuckDB + pyarrow do all the heavy lifting — no custom ORM, no query builder.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:  # avoid a hard pandas import at module load
    import pandas as pd

from blitz_engine.config import EngineConfig, load_config

__all__ = ["ParquetStore"]


class ParquetStore:
    """A directory of named Parquet tables, queried with DuckDB.

    Usage:
        with ParquetStore.open("data/") as store:
            store.write_parquet("pbp", df)
            rel = store.table("pbp")             # lazy, mmap Parquet scan
            store.query("SELECT week, COUNT(*) FROM pbp GROUP BY week")
            for batch in store.read_chunks("pbp"):   # streamed, never full-in-RAM
                ...
    """

    def __init__(self, root: str | Path, config: EngineConfig | None = None) -> None:
        self.config = config or load_config()
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(database=":memory:")

    # -- lifecycle ---------------------------------------------------------
    @classmethod
    def open(cls, root: str | Path, config: EngineConfig | None = None) -> ParquetStore:
        """Open (creating if needed) the store rooted at `root`."""
        return cls(root, config)

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> ParquetStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- paths -------------------------------------------------------------
    def path(self, name: str) -> Path:
        """Filesystem path of the named table's Parquet file."""
        return self.root / f"{name}.parquet"

    # -- write -------------------------------------------------------------
    def write_parquet(self, name: str, data: pd.DataFrame | pa.Table) -> Path:
        """Persist `data` as the named table, overwriting any prior version.

        Accepts a pandas DataFrame or an Arrow Table. Returns the file path.
        """
        table = data if isinstance(data, pa.Table) else pa.Table.from_pandas(data)
        dest = self.path(name)
        pq.write_table(table, dest)
        return dest

    # -- read --------------------------------------------------------------
    def table(self, name: str) -> duckdb.DuckDBPyRelation:
        """Lazy DuckDB relation over the named Parquet (memory-mapped scan)."""
        return self._con.read_parquet(str(self.path(name)))

    def query(self, sql: str) -> duckdb.DuckDBPyRelation:
        """Run SQL, referencing tables by bare name (auto-resolved to their Parquet).

        Every `<name>` that maps to an existing table file is registered as a view
        before the query runs, so `SELECT ... FROM pbp` just works.
        """
        for parquet in self.root.glob("*.parquet"):
            self._con.register(
                parquet.stem, self._con.read_parquet(str(parquet))
            )
        return self._con.sql(sql)

    def read_chunks(
        self, name: str, chunk_size: int | None = None
    ) -> Iterator[pa.RecordBatch]:
        """Stream the named table as Arrow RecordBatches — never materializes it whole.

        `chunk_size` defaults to `config.chunk_size`. Reads are memory-mapped when
        `config.mmap` is set.
        """
        pf = pq.ParquetFile(self.path(name), memory_map=self.config.mmap)
        yield from pf.iter_batches(batch_size=chunk_size or self.config.chunk_size)

    def tables(self) -> list[str]:
        """Names of every table currently in the store."""
        return sorted(p.stem for p in self.root.glob("*.parquet"))
