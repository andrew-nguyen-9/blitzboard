"""Supplemental independent adversarial coverage for C02B."""

from __future__ import annotations

import numpy as np

from blitz_engine.simulation import season_eval as se


def test_op_slot_accepts_ordinary_superflex_positions_for_waiver_upgrade() -> None:
    """ESPN's OP label must retain the same eligibility as SUPERFLEX."""
    positions = ["QB", "WR", "RB"]
    swap = se._best_upgrade(
        squad=[0, 1],
        free=[2],
        positions=positions,
        proj=np.array([20.0, 1.0, 10.0]),
        known_out=np.zeros(3, dtype=bool),
        margin=0.15,
        slots={"OP": 1},
    )

    assert swap == (1, 2)
