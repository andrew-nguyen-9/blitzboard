"""E5 lineup acceptance tests — win-probability-optimal weekly start/sit.

Proves the load-bearing E5 claims:
  * floor vs ceiling both fall out of ONE win-prob objective — a weak opponent ⇒ the
    low-variance FLEX pick (floor), a strong opponent ⇒ the high-variance one (ceiling), with
    no floor/ceiling heuristic in the code;
  * the synced lineup genuinely MAXIMISES P(beat the actual opponent) (it prefers a higher-
    variance, slightly-lower-mean player when that raises win-prob — i.e. it is NOT max-mean);
  * the fallback (no opponent synced) is the best-per-week (max expected points) lineup;
  * a per-slot "why" and a narrative are always present.
"""
from __future__ import annotations

import numpy as np

from blitz_engine.lineup import LineupPlayer, optimal_lineup
from blitz_engine.lineup.winprob import _draw_points, _opponent_start_cols
from blitz_engine.simulation.correlation import CorrelationSpec
from blitz_engine.value.roster_solver import RosterRequirements

_REQS = RosterRequirements()
_SPEC = CorrelationSpec()  # matches optimal_lineup's default, so re-drawn matrices are identical
_SPEC_SEED = 7
_N_DRAWS = 2_000
_OPT_DRAWS = 600


def _p(pid: str, pos: str, mean: float, sd: float, bye: int | None = None) -> LineupPlayer:
    # Unique team, no opponent ⇒ correlation degrades to independence: the FLEX floor/ceiling
    # contrast is isolated to each candidate's own variance, nothing else.
    return LineupPlayer(id=pid, position=pos, mean=mean, stdev=sd, team=f"T_{pid}", bye_week=bye)


def _my_roster(ceil_mean: float = 12.0) -> list[LineupPlayer]:
    """Nine dominant, locked starters + two equal-context FLEX candidates (one floor, one
    ceiling). Every locked player is the unique best for its own slot, so the ONLY real
    decision the solver faces is which candidate fills FLEX."""
    return [
        _p("QB1", "QB", 25.0, 3.0),
        _p("QB2", "QB", 22.0, 3.0),   # lands SUPERFLEX
        _p("RB1", "RB", 25.0, 3.0),
        _p("RB2", "RB", 24.0, 3.0),
        _p("WR1", "WR", 25.0, 3.0),
        _p("WR2", "WR", 24.0, 3.0),
        _p("TE1", "TE", 20.0, 3.0),
        _p("K1", "K", 10.0, 2.0),
        _p("DST1", "DST", 10.0, 3.0),
        _p("FLOOR", "WR", 12.0, 2.0),    # low variance
        _p("CEIL", "WR", ceil_mean, 12.0),  # high variance
    ]


def _opponent(total: float) -> list[LineupPlayer]:
    """A legal 10-slot opponent whose expected-best lineup sums to ~`total` points."""
    each = total / 10.0
    return [
        _p("oQB1", "QB", each, 3.0),
        _p("oQB2", "QB", each, 3.0),
        _p("oRB1", "RB", each, 3.0),
        _p("oRB2", "RB", each, 3.0),
        _p("oWR1", "WR", each, 3.0),
        _p("oWR2", "WR", each, 3.0),
        _p("oTE1", "TE", each, 3.0),
        _p("oFLEX", "WR", each, 3.0),
        _p("oK1", "K", each, 2.0),
        _p("oDST1", "DST", each, 3.0),
    ]


def _started_candidate(decision) -> str:
    # The slot LABELS among interchangeable players are arbitrary; what matters is which of the
    # two FLEX candidates made the starting set.
    ids = {p.id for _, p in decision.starters}
    return "CEIL" if "CEIL" in ids else "FLOOR"


def test_weak_opponent_picks_the_floor() -> None:
    # Favorite (my ~197 mean > opp 185): win-prob is maximised by the LOW-variance FLEX.
    dec = optimal_lineup(
        _my_roster(), opponent=_opponent(185.0),
        n_draws=_N_DRAWS, opt_draws=_OPT_DRAWS, seed=_SPEC_SEED,
    )
    assert _started_candidate(dec) == "FLOOR"
    assert dec.posture == "floor (favorite)"
    assert dec.win_prob is not None and 0.5 < dec.win_prob < 1.0


def test_strong_opponent_picks_the_ceiling() -> None:
    # Underdog (opp 209 > my ~197 mean): the SAME win-prob objective now wants the HIGH-
    # variance FLEX — ceiling falls out with no special-casing.
    dec = optimal_lineup(
        _my_roster(), opponent=_opponent(209.0),
        n_draws=_N_DRAWS, opt_draws=_OPT_DRAWS, seed=_SPEC_SEED,
    )
    assert _started_candidate(dec) == "CEIL"
    assert dec.posture == "ceiling (underdog)"
    assert dec.win_prob is not None and 0.0 < dec.win_prob < 0.5


def test_synced_lineup_maximises_winprob_vs_actual_opponent() -> None:
    # CEIL has a SLIGHTLY LOWER mean but much higher variance. A max-mean lineup would bench
    # it; the win-prob objective starts it because — vs THIS strong opponent — it wins more
    # often. Verify the chosen lineup's win-prob is the true argmax over the FLEX choice on the
    # exact same draws the optimiser used.
    roster = _my_roster(ceil_mean=11.5)
    opp = _opponent(209.0)
    dec = optimal_lineup(
        roster, opponent=opp, n_draws=_N_DRAWS, opt_draws=_OPT_DRAWS, seed=_SPEC_SEED,
    )
    assert _started_candidate(dec) == "CEIL"  # NOT the higher-mean FLOOR ⇒ not max-mean

    # Re-measure both candidate lineups on the identical draw matrix.
    combined = roster + opp
    pts = _draw_points(combined, _N_DRAWS, _SPEC, _SPEC_SEED)
    opp_cols = _opponent_start_cols(opp, len(roster), _REQS, None)
    assert opp_cols is not None
    opp_score = pts[:, opp_cols].sum(axis=1)
    locked = {"QB1", "QB2", "RB1", "RB2", "WR1", "WR2", "TE1", "K1", "DST1"}
    idx = {p.id: j for j, p in enumerate(roster)}

    def winprob_with(flex_id: str) -> float:
        cols = [idx[i] for i in locked | {flex_id}]
        return float(np.mean(pts[:, cols].sum(axis=1) > opp_score))

    wp_ceil, wp_floor = winprob_with("CEIL"), winprob_with("FLOOR")
    assert wp_ceil > wp_floor  # ceiling really is the win-prob argmax here
    assert dec.win_prob is not None
    assert abs(dec.win_prob - wp_ceil) < 1e-9


def test_fallback_is_best_per_week_when_unsynced() -> None:
    dec = optimal_lineup(_my_roster(), n_draws=_N_DRAWS, seed=_SPEC_SEED)
    assert dec.opponent_synced is False
    assert dec.win_prob is None
    assert dec.opp_projected is None
    assert dec.posture.startswith("best-per-week")
    # Best-per-week = maximise expected points: total must equal the max-mean legal lineup
    # (locked 185 + best single FLEX candidate mean 12).
    assert dec.my_projected == 185.0 + 12.0
    assert len(dec.starters) == len(_REQS.starters)


def test_why_and_narrative_always_present() -> None:
    synced = optimal_lineup(
        _my_roster(), opponent=_opponent(185.0),
        n_draws=_N_DRAWS, opt_draws=_OPT_DRAWS, seed=_SPEC_SEED,
    )
    unsynced = optimal_lineup(_my_roster(), n_draws=_N_DRAWS, seed=_SPEC_SEED)
    for dec in (synced, unsynced):
        assert len(dec.why) == len(dec.starters)
        assert all(w.reason.strip() for w in dec.why)
        assert dec.narrative.strip()
        # every "why" points at the slot's actual starter
        starter_ids = {p.id for _, p in dec.starters}
        assert all(w.player_id in starter_ids for w in dec.why)


def test_bye_player_cannot_start() -> None:
    roster = _my_roster()
    # Bench WR1 by putting it on bye in week 5; a legal lineup must still be fielded.
    roster = [
        LineupPlayer(id=p.id, position=p.position, mean=p.mean, stdev=p.stdev,
                     team=p.team, bye_week=5 if p.id == "WR1" else None)
        for p in roster
    ]
    dec = optimal_lineup(
        roster, opponent=_opponent(185.0), week=5,
        n_draws=_N_DRAWS, opt_draws=_OPT_DRAWS, seed=_SPEC_SEED,
    )
    assert "WR1" not in {p.id for _, p in dec.starters}
