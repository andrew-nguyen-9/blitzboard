# `engine/` — BlitzBoard heavy local quant tier (`blitz_engine`)

The **local, JAX/NumPyro/DuckDB-heavy** tier that does ALL the quant (MCMC fit, MC sim, IP
solver, MCTS/RL) and produces **versioned snapshots**. Physically separate from the free
GitHub-Actions cron `pipeline/`, which must never import JAX/torch. Full design:
[`docs/design/v4-engine-architecture.md`](../docs/design/v4-engine-architecture.md).

E0-scaffold ships the **foundation skeleton** every v4 unit builds on: config, store,
snapshot, registry, CLI. Model subpackages (projection, simulation, value, …) land later.

## Layout

```
engine/
  pyproject.toml                 # jax[cpu], numpyro, torch, duckdb, pyarrow, ortools, pandas
  blitz_engine/
    config.py                    # EngineConfig / load_config  — M1/16GB knobs (single source of truth)
    store/                       # ParquetStore — DuckDB + mmap Parquet data-access seam
    snapshot/                    # Snapshot + SCHEMA_VERSION — versioned hand-off bundle
    registry/                    # ModelRegistry / RunRecord — reproducible run records
    cli.py                       # blitz-engine fit | sim | draft | publish  (stubs in W1)
    pipeline_bridge.py           # reuse existing pipeline/adapters by import (W1 no-move seam)
  tests/                         # pytest smoke suite (green from zero)
```

## Environment

The engine shares the interpreter at **`pipeline/.venv`** (Python 3.12; jax/numpyro/duckdb/
torch/pyarrow/ortools installed). Install the package editable once:

```bash
pipeline/.venv/bin/python -m pip install -e engine --no-deps
```

## Definition of done (engine — authoritative)

```bash
cd engine && ../pipeline/.venv/bin/python -m pytest -q \
  && ../pipeline/.venv/bin/ruff check . \
  && ../pipeline/.venv/bin/mypy blitz_engine
```

The smoke suite proves: all four CLI verbs parse + run, the store round-trips Parquet
(full + chunked), the snapshot serializes/deserializes (full + compact), and the registry
records + reproduces a run. Extend these tests; never weaken them.

## Public foundation API (dependents build against this)

| Module | Surface |
|--------|---------|
| `config` | `EngineConfig(dtype, mmap, chunk_size, mc_batch, n_draws, seed, device, cloud_burst, data_root)`, `load_config(**overrides)` |
| `store` | `ParquetStore.open(root, cfg)` → `write_parquet(name, df\|table)`, `table(name)`, `query(sql)`, `read_chunks(name, chunk_size)`, `tables()` |
| `snapshot` | `Snapshot(values, quantiles, corr_matrix, mc_probs, strategy_tree, policy, version, as_of)` → `write(dir)`, `read(dir)`, `export_compact(dir)`; `SCHEMA_VERSION` |
| `registry` | `ModelRegistry(root)` → `record(params, data_hash, seed, git_sha=None)` → `RunRecord`, `reproduce(version)`, `records()` |
| `pipeline_bridge` | `load_adapters()` → `(discover, Adapter)` from `pipeline/adapters` |

## Snapshot version policy

Frozen early, **additive only**: bump `SCHEMA_VERSION` to *add* optional fields — never
rename or repurpose. Readers tolerate a newer minor by ignoring unknown keys; the frontend
degrades to last-good + "as of &lt;date&gt;". Raw posterior draws stay **local** (never in
the compact export).
