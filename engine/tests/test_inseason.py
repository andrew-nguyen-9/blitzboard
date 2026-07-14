"""E5 in-season acceptance tests — waiver bandit + streaming + trade evaluator.

Proves the load-bearing E5-inseason claims:
  * the Thompson waiver bandit is seed-deterministic and ranks by posterior-draw win share;
  * a wide-posterior sleeper is surfaced as a *flyer* (explore) while the high-mean arm is the
    *exploit* — the exploit/explore split falls out of the mean-rank vs Thompson-rank gap;
  * streaming is win-prob-framed: the streamer that yields the best lineup win probability wins
    the board (matchup-driven), reusing the E5 lineup optimiser;
  * the trade evaluator finds a win-win (both teams' Δequity positive) surplus-for-need swap,
    scores fairness, and ranks win-win above lopsided — always ranked + explained.
"""
from __future__ import annotations

from blitz_engine.inseason import (
    StreamBoard,
    TradeSide,
    WaiverCandidate,
    evaluate_trade,
    propose_trades,
    stream_position,
    waiver_bandit,
)
from blitz_engine.lineup import LineupPlayer
from blitz_engine.value.roster_solver import Player, RosterRequirements

# ---------------------------------------------------------------- waiver bandit


def _cands() -> list[WaiverCandidate]:
    # A = tight stud (exploit), C = mid & certain, B = lower-mean but wide posterior (flyer).
    return [
        WaiverCandidate("A", "RB", mean=10.0, epistemic_sd=0.5),
        WaiverCandidate("C", "RB", mean=9.0, epistemic_sd=0.0),
        WaiverCandidate("B", "WR", mean=8.0, epistemic_sd=5.0),
    ]


def test_waiver_thompson_seed_deterministic() -> None:
    b1 = waiver_bandit(_cands(), n_draws=6000, seed=123)
    b2 = waiver_bandit(_cands(), n_draws=6000, seed=123)
    assert [(r.id, r.pick_prob) for r in b1.ranked] == [(r.id, r.pick_prob) for r in b2.ranked]
    # A different seed is still deterministic but need not match.
    b3 = waiver_bandit(_cands(), n_draws=6000, seed=999)
    assert [(r.id, r.pick_prob) for r in b3.ranked] == [
        (r.id, r.pick_prob) for r in waiver_bandit(_cands(), n_draws=6000, seed=999).ranked
    ]


def test_waiver_pick_probs_are_a_distribution_over_arms() -> None:
    board = waiver_bandit(_cands(), n_draws=8000, seed=7)
    total = sum(r.pick_prob for r in board.ranked)
    # Some draws are won by the incumbent (value 0 here loses to all), so mass ≈ 1 but ≤ 1.
    assert 0.99 < total <= 1.0
    assert board.best() is not None and board.best().id == "A"  # highest expected value wins


def test_waiver_exploit_vs_flyer_split() -> None:
    board = waiver_bandit(_cands(), n_draws=12000, seed=42)
    kind = {r.id: r.kind for r in board.ranked}
    assert kind["A"] == "exploit"          # top mean, tight posterior
    assert kind["B"] == "flyer"            # lower mean but wide posterior lifts its Thompson rank
    # Every rec carries an explanation.
    assert all(r.reason for r in board.ranked)


def test_waiver_beats_incumbent_gate() -> None:
    # Incumbent worth 9.5 ± 0: only the tight 10.0 stud reliably clears it.
    board = waiver_bandit(_cands(), incumbent_value=9.5, incumbent_sd=0.0, n_draws=12000, seed=3)
    beats = {r.id: r.beats_incumbent for r in board.ranked}
    assert beats["A"] is True
    assert beats["C"] is False              # 9.0 < 9.5, no spread to clear it
    assert "A" in {r.id for r in board.adds()}


def test_waiver_empty() -> None:
    board = waiver_bandit([], seed=1)
    assert board.ranked == () and board.best() is None and board.adds() == ()


# ---------------------------------------------------------------- streaming

_STREAM_REQS = RosterRequirements(starters=("QB", "RB", "DST"))


def _lp(pid: str, pos: str, mean: float, sd: float, team: str) -> LineupPlayer:
    return LineupPlayer(id=pid, position=pos, mean=mean, stdev=sd, team=team)


def test_streaming_ranks_by_projection_unsynced() -> None:
    base = [_lp("qb", "QB", 18.0, 4.0, "AAA"), _lp("rb", "RB", 12.0, 3.0, "BBB")]
    cands = [
        _lp("dst_hi", "DST", 9.0, 3.0, "CCC"),
        _lp("dst_lo", "DST", 5.0, 2.0, "DDD"),
    ]
    board = stream_position(base, cands, opponent=None, requirements=_STREAM_REQS,
                            n_draws=200, opt_draws=100, seed=5)
    assert isinstance(board, StreamBoard)
    assert board.opponent_synced is False
    assert board.best() is not None and board.best().id == "dst_hi"
    assert board.best().win_prob is None
    assert board.ranked[0].lift >= board.ranked[-1].lift
    assert all(o.reason for o in board.ranked)


def test_streaming_winprob_framed_when_synced() -> None:
    base = [_lp("qb", "QB", 18.0, 4.0, "AAA"), _lp("rb", "RB", 12.0, 3.0, "BBB")]
    cands = [
        _lp("dst_hi", "DST", 9.0, 3.0, "CCC"),
        _lp("dst_lo", "DST", 5.0, 2.0, "DDD"),
    ]
    opp = [
        _lp("oqb", "QB", 17.0, 4.0, "EEE"),
        _lp("orb", "RB", 11.0, 3.0, "FFF"),
        _lp("odst", "DST", 7.0, 3.0, "GGG"),
    ]
    board = stream_position(base, cands, opponent=opp, requirements=_STREAM_REQS,
                            n_draws=400, opt_draws=200, seed=11)
    assert board.opponent_synced is True
    for o in board.ranked:
        assert o.win_prob is not None and 0.0 <= o.win_prob <= 1.0
    # win-prob is the ranking key when synced
    probs = [o.win_prob for o in board.ranked]
    assert probs == sorted(probs, reverse=True)
    assert board.best().id == "dst_hi"


# ---------------------------------------------------------------- trade evaluator

_TRADE_REQS = RosterRequirements(starters=("RB", "WR"))


def _team_a() -> TradeSide:
    # A starts 1 RB / 1 WR; short at RB (best RB only 5), surplus WR (10 and a spare 9).
    return TradeSide(
        roster_id="A",
        roster=(
            Player("a_rb", "RB", 5.0),
            Player("a_wr1", "WR", 10.0),
            Player("a_wr2", "WR", 9.0),
        ),
    )


def _team_b() -> TradeSide:
    # B is deep at RB (8 and a spare 7), thin at WR (only 4).
    return TradeSide(
        roster_id="B",
        roster=(
            Player("b_rb1", "RB", 8.0),
            Player("b_rb2", "RB", 7.0),
            Player("b_wr", "WR", 4.0),
        ),
    )


def test_trade_surplus_for_need_is_win_win() -> None:
    ev = evaluate_trade(
        _team_a(), _team_b(), a_sends=["a_wr2"], b_sends=["b_rb2"], requirements=_TRADE_REQS
    )
    # A: RB 5→7 (+2). B: WR 4→9 (+5). Both starting-lineup values rise → win-win.
    assert ev.delta_value_a == 2.0
    assert ev.delta_value_b == 5.0
    assert ev.win_win is True
    assert ev.legal is True
    assert 0.0 < ev.fairness < 1.0
    assert ev.reason


def test_trade_lopsided_is_not_win_win() -> None:
    # A ships its spare WR (9) for B's weak WR (4): A's starters don't improve (still 5+10),
    # only B gains a startable WR — one-sided, not win-win.
    ev = evaluate_trade(
        _team_a(), _team_b(), a_sends=["a_wr2"], b_sends=["b_wr"], requirements=_TRADE_REQS
    )
    assert ev.delta_value_a == 0.0
    assert ev.delta_value_b > 0.0
    assert ev.win_win is False


def test_trade_sensitivity_scales_equity() -> None:
    a = TradeSide("A", _team_a().roster, sensitivity=0.01)
    b = TradeSide("B", _team_b().roster, sensitivity=0.02)
    ev = evaluate_trade(a, b, a_sends=["a_wr2"], b_sends=["b_rb2"], requirements=_TRADE_REQS)
    assert abs(ev.delta_equity_a - 0.01 * ev.delta_value_a) < 1e-9
    assert abs(ev.delta_equity_b - 0.02 * ev.delta_value_b) < 1e-9


def test_propose_trades_ranks_win_win_first_and_explains() -> None:
    ranked = propose_trades(_team_a(), _team_b(), requirements=_TRADE_REQS)
    assert ranked  # all 3x3 one-for-one swaps evaluated
    assert ranked[0].win_win is True
    assert ranked[0].delta_value_a > 0 and ranked[0].delta_value_b > 0
    # win-win trades sort ahead of the rest
    kinds = [e.win_win for e in ranked]
    assert kinds == sorted(kinds, reverse=True)
    assert all(e.reason for e in ranked)
    ww = propose_trades(_team_a(), _team_b(), requirements=_TRADE_REQS, win_win_only=True)
    assert ww and all(e.win_win for e in ww)


def test_trade_unknown_id_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        evaluate_trade(_team_a(), _team_b(), a_sends=["nope"], b_sends=["b_rb2"],
                       requirements=_TRADE_REQS)
