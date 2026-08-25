"""e2a — the availability truth layer: status coverage, depth chart, degradation.

Contract under test (`blitz_engine.survival.availability`):

    p_startable = P(rostered + active + dresses + ≥10% of team offensive snaps | team plays)

Every state in the brief resolves to a probability in [0,1]; the ordering properties hold
(IR ≤ active, depth rank 1 ≥ rank 3); every source can go missing INDEPENDENTLY and the
layer degrades to a documented default with a warning rather than crashing or zeroing; and
`is_effectively_unavailable` is the predicate e8 asserts on.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pytest

from blitz_engine.survival.availability import (
    DEPTH_RANK_P,
    ROSTER_STATE_P,
    SEASON_LONG_ZERO_STATES,
    ZERO_AVAILABILITY_EPS,
    AvailabilityModel,
    RosterState,
    depth_rank_p,
    fit_usage_priors,
    is_effectively_unavailable,
    is_season_long_zero,
    resolve_roster_state,
    roster_state_p,
    snap_share_p,
    unavailable_ids,
    usage_p,
)

# ── status coverage: every state in the brief ────────────────────────────────────
BRIEF_STATES = [
    RosterState.ROSTERED, RosterState.RETIRED, RosterState.FREE_AGENT,
    RosterState.PRACTICE_SQUAD, RosterState.SUSPENDED, RosterState.PUP,
    RosterState.NFI, RosterState.IR, RosterState.HOLDOUT, RosterState.CAMP_BODY,
]


def test_every_brief_state_is_covered_and_a_probability() -> None:
    for state in BRIEF_STATES:
        p = ROSTER_STATE_P[state]
        assert 0.0 <= p <= 1.0, state
    assert set(ROSTER_STATE_P) == set(RosterState)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ACT", RosterState.ROSTERED), ("Active", RosterState.ROSTERED),
        ("RES/RET", RosterState.RETIRED), ("retired", RosterState.RETIRED),
        ("UFA", RosterState.FREE_AGENT), ("Free Agent", RosterState.FREE_AGENT),
        ("PS", RosterState.PRACTICE_SQUAD), ("practice_squad", RosterState.PRACTICE_SQUAD),
        ("EXE/SUSP", RosterState.SUSPENDED), ("RES/PUP", RosterState.PUP),
        ("Non-Football Injury", RosterState.NFI), ("RES/INJ", RosterState.IR),
        ("holdout", RosterState.HOLDOUT), ("Camp Body", RosterState.CAMP_BODY),
    ],
)
def test_feed_spellings_resolve(raw: str, expected: RosterState) -> None:
    assert resolve_roster_state(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "  ", "nan", float("nan"), "WHO KNOWS"])
def test_unknown_state_is_no_signal_not_zero(raw: object) -> None:
    """An unparseable roster string must never sink a player (degrade-neutral)."""
    assert resolve_roster_state(raw) is None
    assert roster_state_p(raw) == 1.0


# ── depth chart + snap share: fitted, monotone ───────────────────────────────────
def test_depth_rank_prior_is_monotone_and_bounded() -> None:
    ranks = sorted(DEPTH_RANK_P)
    ps = [DEPTH_RANK_P[r] for r in ranks]
    assert ps == sorted(ps, reverse=True)
    assert all(0.0 <= p <= 1.0 for p in ps)
    assert depth_rank_p(1) > depth_rank_p(3)          # brief: rank 1 ≥ rank 3
    assert depth_rank_p(99) < depth_rank_p(6)         # deep tail
    assert depth_rank_p(0) is None and depth_rank_p(None) is None


def test_snap_share_prior_is_monotone_and_unit_agnostic() -> None:
    bands = [snap_share_p(x / 10 + 0.01) for x in range(10)]
    assert bands == sorted(bands)
    assert snap_share_p(0.62) == snap_share_p(62.0)   # fraction or percent
    assert snap_share_p("nope") is None and snap_share_p(-1) is None


def test_usage_combines_both_signals_and_stays_monotone() -> None:
    assert usage_p() == 1.0                                    # no signal → no-op
    assert usage_p(depth_rank=1) == DEPTH_RANK_P[1]
    assert usage_p(depth_rank=1, snap_share=0.9) > usage_p(depth_rank=3, snap_share=0.9)
    assert 0.0 <= usage_p(depth_rank=8, snap_share=0.0) <= 1.0


def test_buried_rb3_is_less_startable_than_the_starter() -> None:
    """"Ahead of others on the depth chart" IS availability — both healthy + rostered."""
    frame = pd.DataFrame({
        "player_id": ["rb1", "rb3"],
        "roster_status": ["ACT", "ACT"],
        "status": ["ACTIVE", "ACTIVE"],
        "depth_rank": [1, 3],
        "snap_share": [0.72, 0.08],
    })
    p = AvailabilityModel().p_startable(frame)
    assert p["rb1"] > p["rb3"] > 0.0
    assert not is_effectively_unavailable(p["rb3"])   # bad pick, not an impossible one


# ── ordering: an IR player is never more available than the same player active ───
@pytest.mark.parametrize("state", [s for s in RosterState if s is not RosterState.ROSTERED])
def test_no_state_beats_being_rostered(state: RosterState) -> None:
    frame = pd.DataFrame({
        "player_id": ["x", "x"],
        "roster_status": [RosterState.ROSTERED.value, state.value],
        "depth_rank": [1, 1],
    })
    p = AvailabilityModel().p_startable(frame).to_numpy()
    assert p[1] <= p[0]


def test_all_states_land_in_unit_interval() -> None:
    frame = pd.DataFrame({
        "player_id": [s.value for s in RosterState],
        "roster_status": [s.value for s in RosterState],
        "status": ["QUESTIONABLE"] * len(RosterState),
        "depth_rank": [2] * len(RosterState),
        "snap_share": [0.4] * len(RosterState),
    })
    p = AvailabilityModel().p_startable(frame)
    assert ((p >= 0.0) & (p <= 1.0)).all()


# ── the ~zero-availability predicate e8 asserts on ──────────────────────────────
def test_zero_availability_predicate_flags_the_undraftables() -> None:
    frame = pd.DataFrame({
        "player_id": ["retired", "unsigned", "camper", "ir", "susp", "rb1", "rb3"],
        "roster_status": ["RET", "UFA", "CAMP", "RES/INJ", "SUSP", "ACT", "ACT"],
        "depth_rank": [1, 1, 5, 1, 1, 1, 3],
    })
    p = AvailabilityModel().p_startable(frame)
    assert unavailable_ids(p) == ["retired", "unsigned", "camper", "ir", "susp"]
    assert not is_effectively_unavailable(p["rb1"])
    assert not is_effectively_unavailable(p["rb3"])
    assert is_effectively_unavailable(ZERO_AVAILABILITY_EPS / 2)
    assert not is_effectively_unavailable(ZERO_AVAILABILITY_EPS)


def test_season_long_zero_is_narrower_than_weekly_zero() -> None:
    for raw in ("RET", "UFA", "CAMP"):
        assert is_season_long_zero(raw)
    for raw in ("RES/INJ", "RES/PUP", "SUSP", "ACT", "garbage", None):
        assert not is_season_long_zero(raw)
    assert SEASON_LONG_ZERO_STATES < set(RosterState)


# ── degrade-safe: each source down INDEPENDENTLY ────────────────────────────────
ALL_COLS = {
    "player_id": ["a", "b"],
    "status": ["ACTIVE", "QUESTIONABLE"],
    "suspended": [False, False],
    "roster_status": ["ACT", "ACT"],
    "depth_rank": [1, 2],
    "snap_share": [0.8, 0.5],
}


@pytest.mark.parametrize("down", ["status", "suspended", "roster_status", "depth_rank",
                                  "snap_share"])
def test_each_source_can_go_missing_alone(down: str, caplog: pytest.LogCaptureFixture) -> None:
    frame = pd.DataFrame({k: v for k, v in ALL_COLS.items() if k != down})
    with caplog.at_level(logging.WARNING):
        p = AvailabilityModel().p_startable(frame)
    assert len(p) == 2
    assert ((p >= 0.0) & (p <= 1.0)).all()
    assert p["a"] > 0.0, "a missing source must never silently zero a healthy starter"
    assert any(down in rec.getMessage() for rec in caplog.records)


def test_stale_or_null_values_degrade_per_row() -> None:
    """Nulls inside a present column behave like the column being absent, per row."""
    frame = pd.DataFrame({
        "player_id": ["a", "b"],
        "status": [None, "ACTIVE"],
        "roster_status": [np.nan, "ACT"],
        "depth_rank": [None, 1],
        "snap_share": [np.nan, 0.9],
        "suspended": [None, False],
    })
    p = AvailabilityModel().p_startable(frame)
    assert p["a"] == 1.0                       # no usable signal → neutral passthrough
    assert 0.0 < p["b"] <= 1.0


def test_no_signals_at_all_is_a_pure_no_op() -> None:
    frame = pd.DataFrame({"player_id": ["a", "b"], "position": ["WR", "RB"]})
    assert np.allclose(AvailabilityModel().p_startable(frame).to_numpy(), 1.0)


def test_warning_is_emitted_once_per_model(caplog: pytest.LogCaptureFixture) -> None:
    model = AvailabilityModel()
    frame = pd.DataFrame({"player_id": ["a"]})
    with caplog.at_level(logging.WARNING):
        model.p_startable(frame)
        model.p_startable(frame)
    assert sum("depth_rank" in r.getMessage() for r in caplog.records) == 1


def test_p_available_alias_is_the_same_function() -> None:
    assert AvailabilityModel.p_startable is AvailabilityModel.p_available


# ── the priors are re-derivable from ingested snap counts ───────────────────────
def _snap_fixture() -> pd.DataFrame:
    """Two teams × 3 weeks: a bell-cow (rank 1, always plays) and a rank-3 who never does."""
    rows = []
    for team in ("KC", "MIA"):
        for week in (1, 2, 3):
            rows += [
                {"season": 2024, "week": week, "team": team, "position": "RB",
                 "player_id": f"{team}-rb1", "snap_share": 0.8},
                {"season": 2024, "week": week, "team": team, "position": "RB",
                 "player_id": f"{team}-rb3", "snap_share": 0.02},
            ]
    return pd.DataFrame(rows)


def test_fit_usage_priors_recovers_the_obvious_structure() -> None:
    out = fit_usage_priors(_snap_fixture())
    assert out["depth_rank_p"][1] == 1.0        # bell-cow always plays the next week
    assert out["depth_rank_p"][2] == 0.0        # the rank-2 (0.02 share) never does
    assert out["n"] == 8                        # week 3 has no following week → dropped
    assert out["snap_share_p"][8] == 1.0


def test_fit_usage_priors_degrades_on_a_useless_frame(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        out = fit_usage_priors(pd.DataFrame({"season": [2024]}))
    assert out["depth_rank_p"] == dict(DEPTH_RANK_P)   # baked priors kept
    assert out["n"] == 0
    assert caplog.records
