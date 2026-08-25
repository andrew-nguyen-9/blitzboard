"""E7a league-config matrix loader — thin parsing + selection over `fixtures/league_matrix.json`.

No logic beyond parsing, the two selectors (`all`/`smoke`), `by_id`, and the one adapter to the
engine's `simulation.league.LeagueConfig`. Parsed once, cached at module level.
"""
from __future__ import annotations

import json
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from blitz_engine.simulation.league import LeagueConfig

_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "league_matrix.json"

Row = dict[str, Any]


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text())


def all() -> list[Row]:  # noqa: A001 - matches the brief's selector name
    """Every row (432) — the full grid, for cheap non-simulating assertions."""
    return list(_data()["rows"])


def smoke() -> list[Row]:
    """The checked-in 16-row pairwise-covering subset for simulation-driven tests."""
    ids = set(_data()["smoke"])
    return [r for r in all() if r["id"] in ids]


def by_id(row_id: str) -> Row:
    """One row by its stable id; raises `KeyError` if unknown."""
    for r in all():
        if r["id"] == row_id:
            return r
    raise KeyError(row_id)


def to_league_config(row: Row) -> LeagueConfig:
    """Adapt a matrix row to `simulation.league.LeagueConfig`.

    gotcha: that dataclass carries Monte-Carlo *simulation* knobs (n_seasons, playoff_teams,
    batch/memory budget, seed, ...), not league shape/scoring — it has no field for
    numTeams/qb_mode/scoring/te_premium/bench_slots/ir_slots/starting_slots. There is nothing to
    adapt there, so the only row-derived field is a stable per-row `seed` (CRC32 of the row id);
    everything else stays that dataclass's default. Callers needing the row's shape/scoring read
    the row dict directly.
    """
    return LeagueConfig(seed=zlib.crc32(row["id"].encode()))
