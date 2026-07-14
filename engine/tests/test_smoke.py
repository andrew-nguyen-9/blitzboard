"""Foundation smoke tests — the E0-scaffold acceptance gate.

Proves the skeleton is green from zero: CLI verbs parse, the store round-trips Parquet
(full + chunked), the snapshot serializes/deserializes (full + compact), and the
registry records + reproduces a run. Downstream units extend, never weaken, these.
"""
from __future__ import annotations

import pandas as pd
import pytest

from blitz_engine import SCHEMA_VERSION, Snapshot
from blitz_engine.cli import build_parser, main
from blitz_engine.registry import ModelRegistry


# -- CLI ------------------------------------------------------------------
@pytest.mark.parametrize("verb", ["fit", "sim", "draft", "publish"])
def test_cli_help_all_verbs(verb: str) -> None:
    """`blitz-engine <verb> --help` exits 0 for every verb."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([verb, "--help"])
    assert exc.value.code == 0


@pytest.mark.parametrize("verb", ["fit", "sim", "draft", "publish"])
def test_cli_runs_end_to_end(verb: str, tmp_path) -> None:
    """Each verb wires config+store+registry and returns exit code 0."""
    assert main([verb, "--data-root", str(tmp_path / "run")]) == 0


# -- store ----------------------------------------------------------------
def test_store_roundtrips_parquet(store, sample_frame: pd.DataFrame) -> None:
    path = store.write_parquet("pbp", sample_frame)
    assert path.exists()
    back = store.table("pbp").df()
    pd.testing.assert_frame_equal(
        back.sort_values("player_id").reset_index(drop=True),
        sample_frame.sort_values("player_id").reset_index(drop=True),
    )


def test_store_query_by_name(store, sample_frame: pd.DataFrame) -> None:
    store.write_parquet("pbp", sample_frame)
    total = store.query("SELECT COUNT(*) AS n FROM pbp").fetchone()[0]
    assert total == len(sample_frame)


def test_store_chunked_read_never_whole(store, sample_frame: pd.DataFrame) -> None:
    store.write_parquet("pbp", sample_frame)
    rows = sum(batch.num_rows for batch in store.read_chunks("pbp", chunk_size=2))
    assert rows == len(sample_frame)
    assert "pbp" in store.tables()


# -- snapshot -------------------------------------------------------------
def test_snapshot_full_roundtrip(sample_snapshot: Snapshot, tmp_path) -> None:
    out = sample_snapshot.write(tmp_path / "snap")
    back = Snapshot.read(out)
    assert back.version == SCHEMA_VERSION
    assert back.strategy_tree == sample_snapshot.strategy_tree
    assert back.policy == sample_snapshot.policy
    pd.testing.assert_frame_equal(back.values, sample_snapshot.values)
    pd.testing.assert_frame_equal(back.corr_matrix, sample_snapshot.corr_matrix)


def test_snapshot_compact_export_excludes_raw(sample_snapshot: Snapshot, tmp_path) -> None:
    out = sample_snapshot.export_compact(tmp_path / "compact")
    written = {p.name for p in out.iterdir()}
    assert written == {"quantiles.parquet", "corr_matrix.parquet", "manifest.json"}
    assert not (out / "values.parquet").exists()
    assert not (out / "mc_probs.parquet").exists()


# -- registry -------------------------------------------------------------
def test_registry_record_and_reproduce(registry: ModelRegistry) -> None:
    rec = registry.record(
        params={"lr": 0.01, "layers": 3}, data_hash="deadbeef", seed=42, git_sha="abc123"
    )
    assert registry.reproduce(rec.version) == rec


def test_registry_version_is_deterministic(tmp_path) -> None:
    a = ModelRegistry(tmp_path / "a").record({"x": 1}, "h", seed=7, git_sha="sha")
    b = ModelRegistry(tmp_path / "b").record({"x": 1}, "h", seed=7, git_sha="sha")
    assert a.version == b.version


def test_registry_missing_version_raises(registry: ModelRegistry) -> None:
    with pytest.raises(KeyError):
        registry.reproduce("nonexistent")


# -- pipeline bridge ------------------------------------------------------
def test_pipeline_bridge_imports_existing_adapters() -> None:
    """Engine reuses pipeline/adapters by import (W1 no-move seam)."""
    from blitz_engine.pipeline_bridge import load_adapters

    discover, Adapter = load_adapters()
    assert callable(discover)
    assert hasattr(Adapter, "run")  # the degrade-safe contract
