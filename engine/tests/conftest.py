"""Shared pytest fixtures for the engine test suite.

Every unit's tests inherit these: an isolated on-disk store rooted in a tmp dir, a
default config pinned to that dir, and small sample frames shaped like the snapshot
components. `ponytail:` fixtures build on the public foundation API only.
"""
from __future__ import annotations

import pandas as pd
import pytest

from blitz_engine.config import EngineConfig, load_config
from blitz_engine.registry import ModelRegistry
from blitz_engine.snapshot import Snapshot
from blitz_engine.store import ParquetStore


@pytest.fixture
def config(tmp_path) -> EngineConfig:
    """Default M1 config with `data_root` redirected into the test's tmp dir."""
    return load_config(data_root=tmp_path / "engine")


@pytest.fixture
def store(config: EngineConfig) -> ParquetStore:
    """An open ParquetStore rooted in the tmp config dir; closed on teardown."""
    with ParquetStore.open(config.data_root, config) as s:
        yield s


@pytest.fixture
def registry(config: EngineConfig) -> ModelRegistry:
    return ModelRegistry(config.data_root)


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    """A tiny player-values frame used for store round-trips."""
    return pd.DataFrame(
        {"player_id": ["p1", "p2", "p3"], "value": [12.5, 8.0, 3.25], "week": [1, 1, 1]}
    )


@pytest.fixture
def sample_snapshot() -> Snapshot:
    """A minimal but complete snapshot bundle covering all six components."""
    players = ["p1", "p2"]
    values = pd.DataFrame({"player_id": players, "value": [10.0, 5.0]})
    quantiles = pd.DataFrame({"player_id": players, "p10": [7.0, 3.0], "p90": [13.0, 7.0]})
    corr = pd.DataFrame([[1.0, 0.2], [0.2, 1.0]], index=players, columns=players)
    mc_probs = pd.DataFrame({"player_id": players, "p_top12": [0.8, 0.4]})
    return Snapshot(
        values=values,
        quantiles=quantiles,
        corr_matrix=corr,
        mc_probs=mc_probs,
        strategy_tree={"root": {"pick": "p1"}},
        policy={"round1": "best_available"},
    )
