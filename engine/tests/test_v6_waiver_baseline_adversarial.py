"""C00 executable specification for the reactive-only v5 waiver limitation."""

import numpy as np
import pytest

from blitz_engine.simulation.season_eval import _run_waivers


@pytest.mark.xfail(
    strict=True,
    reason="C02: proactive non-emergency waiver upgrades are not implemented",
)
def test_healthy_lineup_replaces_stale_bench_player_when_improvement_clears_cost() -> None:
    squads = [[0, 1]]
    free = [2]
    adds = _run_waivers(
        squads,
        free,
        np.array([0.0]),
        {"QB": 1},
        ["QB", "RB", "RB"],
        np.array([20.0, 2.0, 12.0]),
        known_out=np.array([False, False, False]),
        limit=1,
        cap=2,
    )
    assert adds[0] == 1
    assert squads == [[0, 2]]
