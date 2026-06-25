"""
Unit tests for predictability scoring (v2.2.1 / SCORING.md §1).

No pytest in the pipeline venv — these are plain asserts, runnable two ways:
    python tests/test_predictability.py          # from pipeline/
    python -m pytest tests/test_predictability.py # if pytest is ever added

Every test_* function is self-contained and prints a ✓ line on success.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import LeagueRules, HistoryStore  # noqa: E402
from models.predictability import Predictability, td_turnover_share  # noqa: E402

SCORING = {
    "passing": {"pt_per_yd": 0.04, "td": 4, "int": -2, "two_pt": 2},
    "rushing": {"pt_per_yd": 0.1, "td": 6, "two_pt": 2},
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6, "two_pt": 2},
    "misc": {"fumble_lost": -2},
}
ROSTER = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1, "DST": 1, "K": 1, "_superflex": True}
RULES = LeagueRules(league_id="t", league_size=12, scoring=SCORING, roster_slots=ROSTER)


def _store(players: dict[str, list[tuple[int, dict, str]]]) -> HistoryStore:
    """players: pid -> [(season, stats, position), ...]."""
    s = HistoryStore(RULES)
    for pid, lines in players.items():
        for season, stats, pos in lines:
            s.add(pid, season, stats, games=stats.get("games", 16), age=25, position=pos)
    return s.finalize()


def test_score_in_unit_interval():
    """ρ is always a probability — even for empty / zero / degenerate input."""
    s = _store({
        "rb": [(2024, {"rushing_yards": 1200, "rushing_tds": 8}, "RB")],
        "empty": [],  # no usable lines
        "zero": [(2024, {}, "WR")],  # zero points
    })
    p = Predictability(s, RULES)
    for pid, pos in [("rb", "RB"), ("empty", "RB"), ("zero", "WR"), ("missing", "QB"), ("k", None)]:
        rho = p.score(pid, pos)
        assert 0.0 <= rho <= 1.0, f"{pid}: {rho} out of [0,1]"
    print("✓ score is always within [0,1] (incl. empty/zero/missing)")


def test_td_share_bounds_and_direction():
    """TD/turnover share ∈ [0,1]; a yardage line is low, a TD-only line is high."""
    yardage = td_turnover_share({"receiving_yards": 1500, "receptions": 100}, SCORING)
    td_only = td_turnover_share({"receiving_tds": 25}, SCORING)
    empty = td_turnover_share({}, SCORING)
    assert 0.0 <= yardage <= 1.0 and 0.0 <= td_only <= 1.0
    assert empty == 0.0, empty
    assert yardage < 0.25, yardage
    assert td_only > 0.9, td_only
    print(f"✓ td/turnover share: yardage={yardage:.2f} < td-only={td_only:.2f}")


def test_high_td_share_lowers_score():
    """Same position, sample, and variance — more TD-dependence ⇒ lower ρ."""
    yards_line = {"receiving_yards": 1500}            # 150 pts, all yardage
    td_line = {"receiving_tds": 25}                   # 150 pts, all TDs
    s = _store({
        "wr_yards": [(y, yards_line, "WR") for y in (2022, 2023, 2024)],
        "wr_td": [(y, td_line, "WR") for y in (2022, 2023, 2024)],
    })
    p = Predictability(s, RULES)
    assert p.score("wr_yards", "WR") > p.score("wr_td", "WR")
    print(f"✓ td-heavy WR scores lower: yards={p.score('wr_yards','WR'):.2f} "
          f"> td={p.score('wr_td','WR'):.2f}")


def test_volatile_player_scores_lower():
    """Same position/sample/TD-mix — higher season-to-season variance ⇒ lower ρ."""
    s = _store({
        "stable": [(y, {"rushing_yards": 1500}, "RB") for y in (2022, 2023, 2024)],
        "volatile": [(2022, {"rushing_yards": 500}, "RB"),
                     (2023, {"rushing_yards": 2500}, "RB"),
                     (2024, {"rushing_yards": 1500}, "RB")],
    })
    p = Predictability(s, RULES)
    assert p.score("stable", "RB") > p.score("volatile", "RB")
    print(f"✓ volatile RB scores lower: stable={p.score('stable','RB'):.2f} "
          f"> volatile={p.score('volatile','RB'):.2f}")


def test_low_sample_shrinks_to_prior():
    """A one-season player sits closer to the positional prior than a long-tenured
    one with the same per-season profile (Bayesian shrinkage)."""
    line = {"rushing_yards": 1500}
    s = _store({
        "rookie": [(2024, line, "RB")],
        "vet": [(y, line, "RB") for y in (2020, 2021, 2022, 2023, 2024)],
    })
    p = Predictability(s, RULES)
    prior = p.prior["RB"]
    assert abs(p.score("rookie", "RB") - prior) < abs(p.score("vet", "RB") - prior)
    print(f"✓ low-sample shrinks to prior {prior:.2f}: "
          f"rookie={p.score('rookie','RB'):.2f}, vet={p.score('vet','RB'):.2f}")


def test_positional_prior_orders_kdef_below_skill():
    """With thin data the prior dominates: K/DST land below skill positions even
    given an identical (position-blind) stat line."""
    line = {"rushing_yards": 1500}  # identical own-signal for both
    s = _store({"k": [(2024, line, "K")], "rb": [(2024, line, "RB")]})
    p = Predictability(s, RULES)
    assert p.prior["K"] < p.prior["RB"], (p.prior["K"], p.prior["RB"])
    assert p.score("k", "K") < p.score("rb", "RB")
    print(f"✓ structural prior orders K<RB: K={p.score('k','K'):.2f} < RB={p.score('rb','RB'):.2f}")


def main():
    test_score_in_unit_interval()
    test_td_share_bounds_and_direction()
    test_high_td_share_lowers_score()
    test_volatile_player_scores_lower()
    test_low_sample_shrinks_to_prior()
    test_positional_prior_orders_kdef_below_skill()
    print("\nALL PREDICTABILITY TESTS PASSED ✅")


if __name__ == "__main__":
    main()
