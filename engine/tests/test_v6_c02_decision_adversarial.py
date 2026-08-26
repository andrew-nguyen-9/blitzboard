"""Independent C02 adversarial tests for proactive-waiver decision semantics."""

from __future__ import annotations

import numpy as np

from blitz_engine.lineup.feasibility import InjuryDynamics
from blitz_engine.simulation import season_eval as se


def _player(pid: str, pos: str, ppw: float) -> se.SeasonPlayer:
    return se.SeasonPlayer(
        player_id=pid,
        position=pos,
        nfl_team="TST",
        bye_week=0,
        points_if_plays=(ppw, ppw, ppw),
        projection=ppw * 3,
        depth_rank=1,
    )


def test_feasible_cross_position_breakout_can_replace_lowest_nonstarter() -> None:
    """The upgrade comparison is roster-wide, not restricted to an incumbent position.

    Both RB and TE are legal in FLEX. The low RB is the roster's nonstarter and the free
    TE is the best feasible replacement, even though their nominal positions differ.
    """
    positions = ["QB", "WR", "RB", "TE"]
    proj = np.array([20.0, 12.0, 2.0, 10.0])
    swap = se._best_upgrade(
        squad=[0, 1, 2],
        free=[3],
        positions=positions,
        proj=proj,
        known_out=np.zeros(4, dtype=bool),
        margin=0.15,
    )
    assert swap == (2, 3)


def test_transaction_cost_can_veto_an_otherwise_positive_claim(
    monkeypatch,
) -> None:
    """A manager does not transact when the forward gain cannot repay its cost."""
    monkeypatch.setattr(se, "_availability", lambda players: np.ones(len(players)))
    a = [_player("a_qb", "QB", 20), _player("a_rb", "RB", 2)]
    b = [_player("b_qb", "QB", 18), _player("b_rb", "RB", 2)]
    free = _player("free_rb", "RB", 10)
    pool = [*a, *b, free]
    row = {
        "id": "transaction-boundary",
        "teams": 2,
        "bench_slots": 1,
        "starting_slots": {"QB": 1},
    }
    config = se.EvalConfig(
        n_seasons=1,
        injury=InjuryDynamics.healthy(),
        proactive_moves_per_week=1,
        upgrade_margin=0.0,
        waiver_cost=10_000.0,
    )
    result = se.evaluate_rosters(pool, [a, b], row, config=config)
    assert result.upside_adds.sum() == 0
