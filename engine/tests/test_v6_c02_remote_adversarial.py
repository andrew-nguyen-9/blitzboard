"""Independent remote adversarial checks for v6 checkpoint C02."""

from __future__ import annotations

import numpy as np
import pytest

from blitz_engine.lineup.feasibility import InjuryDynamics
from blitz_engine.simulation import season_eval as se


def _player(
    player_id: str,
    position: str,
    projection: float,
    weekly: tuple[float, ...] = (10.0, 10.0, 10.0, 10.0),
) -> se.SeasonPlayer:
    return se.SeasonPlayer(player_id, position, "AAA", 0, weekly, projection, 1)


@pytest.fixture(autouse=True)
def certain_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(se, "_availability", lambda players: np.ones(len(players)))


def test_proactive_claim_can_drop_a_different_position_nonstarter() -> None:
    positions = ["RB", "WR", "RB"]
    projections = np.array([100.0, 1.0, 20.0])
    squads = [[0, 1]]
    free = [2]

    _emergency, upside = se._run_waivers(
        squads,
        free,
        np.zeros(1),
        {"RB": 1},
        positions,
        projections,
        known_out=np.zeros(3, dtype=bool),
        limit=0,
        cap=2,
        proactive_limit=1,
        upgrade_margin=0.15,
    )

    assert upside.tolist() == [1.0]
    assert squads == [[0, 2]]
    assert free == [1]


def test_transaction_cost_blocks_a_negative_net_claim() -> None:
    roster = [_player("starter", "RB", 40.0), _player("stale", "RB", 4.0)]
    free_agent = _player("upgrade", "RB", 20.0)
    row = {"id": "cost", "teams": 1, "bench_slots": 1, "starting_slots": {"RB": 1}}
    result = se.evaluate_rosters(
        [*roster, free_agent],
        [roster],
        row,
        config=se.EvalConfig(
            n_seasons=1,
            injury=InjuryDynamics.healthy(),
            waiver_cost=100.0,
        ),
    )

    assert result.waiver_adds.tolist() == [0.0]


def test_weekly_move_limit_caps_emergency_plus_upside() -> None:
    positions = ["RB", "K", "RB", "K"]
    projections = np.array([10.0, 1.0, 8.0, 10.0])
    squads = [[0, 1]]
    free = [2, 3]

    emergency, upside = se._run_waivers(
        squads,
        free,
        np.zeros(1),
        {"RB": 1, "K": 1},
        positions,
        projections,
        known_out=np.array([True, False, False, False]),
        limit=1,
        cap=2,
        proactive_limit=1,
        upgrade_margin=0.15,
        moves_left=np.array([10]),
    )

    assert (emergency + upside).tolist() == [1.0]


def test_exact_upgrade_boundary_does_not_transact() -> None:
    swap = se._best_upgrade(
        [0],
        [1],
        ["RB", "RB"],
        np.array([10.0, 11.5]),
        np.zeros(2, dtype=bool),
        0.15,
    )
    assert swap is None


def test_low_preseason_breakout_is_eventually_claimed() -> None:
    starter = _player("starter", "RB", 40.0)
    stale = _player("stale", "RB", 8.0, (2.0, 2.0, 2.0, 2.0))
    breakout = _player("breakout", "RB", 1.0, (30.0, 30.0, 30.0, 30.0))
    row = {"id": "breakout", "teams": 1, "bench_slots": 1, "starting_slots": {"RB": 1}}

    result = se.evaluate_rosters(
        [starter, stale, breakout],
        [[starter, stale]],
        row,
        config=se.EvalConfig(n_seasons=1, injury=InjuryDynamics.healthy()),
    )

    assert result.upside_adds.tolist() == [1.0]


def test_dropped_player_returns_to_shared_pool_for_later_priority_team() -> None:
    positions = ["RB", "RB", "RB"]
    squads = [[0], [2]]
    free = [1]

    _emergency, upside = se._run_waivers(
        squads,
        free,
        np.array([0.0, 1.0]),
        {"RB": 1},
        positions,
        np.array([1.0, 10.0, 0.1]),
        known_out=np.zeros(3, dtype=bool),
        limit=0,
        cap=1,
        proactive_limit=1,
        upgrade_margin=0.15,
    )

    assert upside.tolist() == [1.0, 1.0]
    assert squads == [[1], [0]]
    assert free == [2]


def test_exact_h2h_and_playoff_ties_use_deterministic_seat_order() -> None:
    a = _player("a", "RB", 40.0)
    b = _player("b", "RB", 40.0)
    row = {"id": "ties", "teams": 2, "bench_slots": 0, "starting_slots": {"RB": 1}}
    result = se.evaluate_rosters(
        [a, b],
        [[a], [b]],
        row,
        config=se.EvalConfig(
            n_seasons=2,
            injury=InjuryDynamics.healthy(),
            waivers=False,
            playoff_slots=1,
        ),
    )

    assert result.h2h_win_rate.tolist() == [0.5, 0.5]
    assert result.per_season_playoff.tolist() == [[1.0, 0.0], [1.0, 0.0]]
    assert result.per_season_champ.tolist() == [[1.0, 0.0], [1.0, 0.0]]
