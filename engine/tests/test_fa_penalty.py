"""Acceptance tests for E4fix-fa-penalty — truly-FA sinks but stays visible.

The DoD contract (brief): a truly-FA player's ranked value drops below all rostered
starters yet remains in the list; a rostered vet with a team is unaffected. Plus the
degrade-neutral guarantee and the interim-value reuse seam.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from blitz_engine.value import (
    FAStatus,
    InterimValue,
    apply_fa_penalty,
    interim_surface,
    is_truly_free_agent,
    load_pipeline_value_engine,
)


@dataclass
class _PValue:
    """Duck-typed stand-in for pipeline `PlayerValue` (has .player_id + .value)."""

    player_id: str
    value: float


# -- interim value hook ---------------------------------------------------
def test_interim_surface_ranks_pipeline_output() -> None:
    surface = interim_surface(
        [_PValue("a", 3.0), _PValue("b", 12.0), _PValue("c", 7.0)],
        positions={"a": "RB", "b": "WR"},
    )
    assert [iv.player_id for iv in surface] == ["b", "c", "a"]
    assert [iv.rank for iv in surface] == [1, 2, 3]
    assert surface[0].pos == "WR"
    assert surface[2].pos == "RB"        # from positions map
    assert surface[1].pos is None        # 'c' absent from positions → None


def test_load_pipeline_value_engine_reuses_shipped_module() -> None:
    """The hook imports the real pipeline engine — we adapt it, never reimplement it."""
    mod = load_pipeline_value_engine()
    assert hasattr(mod, "VorpEngine")
    assert hasattr(mod, "PlayerValue")


# -- truly-FA predicate ---------------------------------------------------
def test_truly_fa_requires_both_signals() -> None:
    assert is_truly_free_agent(FAStatus(team=None, has_news=False)) is True
    assert is_truly_free_agent(FAStatus(team="", has_news=False)) is True
    # has a team → not FA even with no news
    assert is_truly_free_agent(FAStatus(team="KC", has_news=False)) is False
    # no team but has news → not FA (news = still relevant)
    assert is_truly_free_agent(FAStatus(team=None, has_news=True)) is False


def test_predicate_degrade_neutral_on_missing_news() -> None:
    """Unknown news (None) or no status at all must NOT be treated as FA."""
    assert is_truly_free_agent(FAStatus(team=None, has_news=None)) is False
    assert is_truly_free_agent(None) is False


# -- penalty application --------------------------------------------------
def _starter_board() -> list[InterimValue]:
    # a realistic-ish board: rostered starters (positive) + a deep-pool negative value,
    # plus one truly-FA who the interim engine WRONGLY valued near the top (the bug).
    return interim_surface(
        [
            _PValue("vet_rb", 120.0),      # rostered starter, has a team
            _PValue("vet_wr", 80.0),       # rostered starter, has a team
            _PValue("fa_hyped", 95.0),     # truly-FA but over-valued (screenshot bug)
            _PValue("deep_guy", -5.0),     # rostered depth, low value
        ]
    )


def test_truly_fa_sinks_below_all_starters_but_stays_visible() -> None:
    board = _starter_board()
    status = {
        "vet_rb": FAStatus(team="KC", has_news=True),
        "vet_wr": FAStatus(team="MIA", has_news=False),
        "fa_hyped": FAStatus(team=None, has_news=False),   # truly FA
        "deep_guy": FAStatus(team="NYJ", has_news=False),
    }
    out = apply_fa_penalty(board, status)

    ids = [iv.player_id for iv in out]
    # still present (visible, not removed)
    assert "fa_hyped" in ids
    assert len(out) == len(board)

    fa = next(iv for iv in out if iv.player_id == "fa_hyped")
    non_fa = [iv for iv in out if iv.player_id != "fa_hyped"]
    # ranked value drops below EVERY non-FA (incl. the negative deep-pool guy)
    assert fa.value < min(iv.value for iv in non_fa)
    # and it lands dead last on the re-ranked board
    assert out[-1].player_id == "fa_hyped"
    assert fa.rank == len(out)


def test_rostered_vet_with_team_is_unaffected() -> None:
    board = _starter_board()
    before = {iv.player_id: iv.value for iv in board}
    status = {"fa_hyped": FAStatus(team=None, has_news=False)}
    out = apply_fa_penalty(board, status)
    for iv in out:
        if iv.player_id != "fa_hyped":
            assert iv.value == before[iv.player_id]     # untouched


def test_no_fa_returns_board_unchanged() -> None:
    board = _starter_board()
    status = {iv.player_id: FAStatus(team="KC", has_news=True) for iv in board}
    out = apply_fa_penalty(board, status)
    assert [(iv.player_id, iv.value) for iv in out] == [
        (iv.player_id, iv.value) for iv in board
    ]


def test_multiple_fas_keep_relative_order_below_floor() -> None:
    board = interim_surface(
        [_PValue("starter", 50.0), _PValue("fa_hi", 40.0), _PValue("fa_lo", 10.0)]
    )
    status = {
        "starter": FAStatus(team="KC", has_news=True),
        "fa_hi": FAStatus(team=None, has_news=False),
        "fa_lo": FAStatus(team=None, has_news=False),
    }
    out = apply_fa_penalty(board, status)
    vals = {iv.player_id: iv.value for iv in out}
    assert vals["starter"] == 50.0
    assert vals["fa_hi"] < vals["starter"]
    assert vals["fa_lo"] < vals["starter"]
    # the more-valued FA still outranks the less-valued FA among the sunk pool
    assert vals["fa_hi"] > vals["fa_lo"]


@pytest.mark.parametrize("factor,margin", [(0.02, 1.0), (0.0, 5.0), (0.5, 0.1)])
def test_sink_guarantee_holds_across_params(factor: float, margin: float) -> None:
    board = _starter_board()
    status = {"fa_hyped": FAStatus(team=None, has_news=False)}
    out = apply_fa_penalty(board, status, factor=factor, margin=margin)
    fa = next(iv for iv in out if iv.player_id == "fa_hyped")
    non_fa_min = min(iv.value for iv in out if iv.player_id != "fa_hyped")
    assert fa.value < non_fa_min
