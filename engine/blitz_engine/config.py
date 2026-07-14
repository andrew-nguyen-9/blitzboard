"""Engine configuration — the single source of truth for the M1 / 16 GB budget.

Every unit reads its knobs from here (see docs/design/v4-engine-architecture.md
§"M1 / 16 GB budget"). Defaults are the safe *local* path; heavy jobs that will not
fit 16 GB set `cloud_burst=True` explicitly — it is never the default.

Env overrides: `BLITZ_ENGINE_<FIELD>` (e.g. `BLITZ_ENGINE_N_DRAWS=2000`). Only the
knobs below are recognized; unknown vars are ignored. `load_config()` is the entrypoint.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

_ENV_PREFIX = "BLITZ_ENGINE_"


@dataclass(frozen=True)
class EngineConfig:
    """Immutable M1/16GB knobs. Construct once, thread through every job.

    Attributes:
        dtype:       Floating precision for all arrays. float32 keeps 16 GB feasible.
        mmap:        Memory-map Parquet/DuckDB reads (never load full history into RAM).
        chunk_size:  Rows per streamed store chunk (`ParquetStore.read_chunks`).
        mc_batch:    Monte-Carlo draws simulated per batch (stream, accumulate stats).
        n_draws:     Posterior/MC draws requested (local default is modest; scale up on burst).
        seed:        Global RNG seed — recorded per run for reproducibility.
        device:      JAX device; "cpu" is the default (Metal is experimental, opt-in).
        cloud_burst: Opt-in to an external heavy-compute box. Never the default path.
        data_root:   Root dir for the local Parquet/DuckDB store, snapshots and registry.
    """

    dtype: str = "float32"
    mmap: bool = True
    chunk_size: int = 100_000
    mc_batch: int = 10_000
    n_draws: int = 1_000
    seed: int = 20240813
    device: str = "cpu"
    cloud_burst: bool = False
    data_root: Path = Path("~/.blitz_engine").expanduser()

    def with_overrides(self, **kwargs: object) -> EngineConfig:
        """Return a copy with the given fields replaced (config stays immutable)."""
        return replace(self, **kwargs)  # type: ignore[arg-type]

    def as_dict(self) -> dict[str, object]:
        """Plain-dict view (Path rendered as str) — for logging / registry params."""
        d = asdict(self)
        d["data_root"] = str(self.data_root)
        return d


def _coerce(name: str, raw: str) -> object:
    """Cast an env string to the dataclass field's type."""
    typ = {f.name: f.type for f in fields(EngineConfig)}[name]
    if typ is bool or typ == "bool":
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if typ is int or typ == "int":
        return int(raw)
    if typ is Path or typ == "Path":
        return Path(raw).expanduser()
    return raw


def load_config(**overrides: object) -> EngineConfig:
    """Build an `EngineConfig`: defaults <- `BLITZ_ENGINE_*` env <- explicit `overrides`.

    Explicit keyword overrides win over the environment; the environment wins over
    the field defaults. This is the ONLY constructor units should call.
    """
    env: dict[str, object] = {}
    known = {f.name for f in fields(EngineConfig)}
    for key, val in os.environ.items():
        if key.startswith(_ENV_PREFIX):
            field = key[len(_ENV_PREFIX) :].lower()
            if field in known:
                env[field] = _coerce(field, val)
    return EngineConfig(**{**env, **overrides})  # type: ignore[arg-type]
