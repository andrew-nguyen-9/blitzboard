"""C01 desired contracts for deterministic player-value correctness."""

import pytest

from models.league_rules import LeagueRules
from models.projector import Projection
from models.value_engine import VorpEngine


def projection(player_id: str, mean: float = 100.0) -> Projection:
    return Projection(
        player_id=player_id,
        season=2026,
        source="test",
        mean=mean,
        floor=mean - 20.0,
        ceiling=mean + 20.0,
        stdev=10.0,
        predictability=1.0,
    )


def one_qb_rules() -> LeagueRules:
    return LeagueRules(
        league_id="redraft",
        league_size=12,
        scoring={},
        roster_slots={"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1},
    )


@pytest.mark.xfail(strict=True, reason="C01: redraft value applies a second future-age multiplier")
def test_equal_redraft_forecasts_have_equal_value_regardless_of_age() -> None:
    projections = {"young": projection("young"), "veteran": projection("veteran")}
    values = VorpEngine().compute(
        projections,
        {"young": "RB", "veteran": "RB"},
        one_qb_rules(),
        {"young": {"age": 22}, "veteran": {"age": 32}},
    )
    by_id = {value.player_id: value.value for value in values}
    assert by_id["young"] == by_id["veteran"]


@pytest.mark.xfail(strict=True, reason="C01: Sleeper search_rank contaminates negative-VOR value")
def test_search_popularity_never_changes_player_value() -> None:
    projections = {
        "popular": projection("popular", 80.0),
        "obscure": projection("obscure", 80.0),
        "replacement": projection("replacement", 100.0),
    }
    values = VorpEngine().compute(
        projections,
        {player_id: "QB" for player_id in projections},
        LeagueRules("tiny", 1, {}, {"QB": 1}),
        {"popular": {"search_rank": 1}, "obscure": {"search_rank": 800}},
    )
    by_id = {value.player_id: value.value for value in values}
    assert by_id["popular"] == by_id["obscure"]


@pytest.mark.xfail(strict=True, reason="C01: OP demand is divided equally instead of measured")
def test_superflex_replacement_accounts_for_two_startable_qbs_per_team() -> None:
    rules = LeagueRules(
        league_id="sf",
        league_size=12,
        scoring={},
        roster_slots={"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1},
    )
    assert rules.replacement_ranks()["QB"] >= 24
