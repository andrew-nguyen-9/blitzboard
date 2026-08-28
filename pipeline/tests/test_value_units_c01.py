"""C01 deterministic player-value correctness — unit contracts, replacement demand,
redraft age, search_rank, and cohort behaviors (rookie / veteran / missing-ADP /
negative-VOR / superflex-QB)."""

from models.league_rules import LeagueRules
from models.projector import Projection
from models.value_engine import VorpEngine


def mk_proj(pid: str, mean: float = 100.0, spread: float = 20.0) -> Projection:
    return Projection(
        player_id=pid, season=2026, source="test", mean=mean,
        floor=mean - spread, ceiling=mean + spread, stdev=10.0, predictability=1.0,
    )


def one_qb_rules() -> LeagueRules:
    return LeagueRules(
        league_id="redraft", league_size=12, scoring={},
        roster_slots={"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1},
    )


def superflex_rules() -> LeagueRules:
    return LeagueRules(
        league_id="sf", league_size=12, scoring={},
        roster_slots={"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1},
    )


def compute(projections, positions, rules, meta=None):
    return {v.player_id: v for v in VorpEngine().compute(projections, positions, rules, meta)}


# ── unit contract ──────────────────────────────────────────────────────────────

def test_boom_bust_are_ceiling_and_floor_vor() -> None:
    """The wire contract: boom = ceiling − replacement, bust = floor − replacement."""
    projs = {f"rb{i}": mk_proj(f"rb{i}", 200.0 - 10 * i) for i in range(30)}
    vals = compute(projs, {p: "RB" for p in projs}, one_qb_rules())
    for pid, v in vals.items():
        assert v.boom == round(projs[pid].ceiling - v.replacement, 2)
        assert v.bust == round(projs[pid].floor - v.replacement, 2)
        assert round(v.projection_mean, 2) == round(v.vor + v.replacement, 2)
        assert round(v.projection_ceiling, 2) == round(v.boom + v.replacement, 2)


# ── redraft age: no second future-value multiplier ─────────────────────────────

def test_equal_redraft_forecasts_have_equal_value_regardless_of_age() -> None:
    projs = {"young": mk_proj("young"), "veteran": mk_proj("veteran")}
    vals = compute(projs, {"young": "RB", "veteran": "RB"}, one_qb_rules(),
                   {"young": {"age": 22}, "veteran": {"age": 32}})
    assert vals["young"].value == vals["veteran"].value


def test_productive_veteran_ranks_by_projection_not_birthday() -> None:
    """A 31-year-old projected above a 23-year-old must out-rank him in redraft."""
    projs = {"vet": mk_proj("vet", 240.0), "youth": mk_proj("youth", 230.0)}
    projs.update({f"rb{i}": mk_proj(f"rb{i}", 150.0 - i) for i in range(28)})
    pos = {p: "RB" for p in projs}
    vals = compute(projs, pos, one_qb_rules(), {"vet": {"age": 31}, "youth": {"age": 23}})
    assert vals["vet"].value > vals["youth"].value


# ── search_rank is never a value input ─────────────────────────────────────────

def test_search_popularity_never_changes_player_value() -> None:
    projs = {
        "popular": mk_proj("popular", 80.0),
        "obscure": mk_proj("obscure", 80.0),
        "starter": mk_proj("starter", 100.0),
    }
    vals = compute(projs, {p: "QB" for p in projs}, LeagueRules("tiny", 1, {}, {"QB": 1}),
                   {"popular": {"search_rank": 1}, "obscure": {"search_rank": 800}})
    assert vals["popular"].value == vals["obscure"].value


def test_negative_vor_pool_orders_by_projection_and_upside_only() -> None:
    """Deep pool: better raw forecast wins; popularity cannot reorder it."""
    projs = {"better": mk_proj("better", 90.0), "worse": mk_proj("worse", 85.0),
             "starter": mk_proj("starter", 120.0)}
    vals = compute(projs, {p: "QB" for p in projs}, LeagueRules("tiny", 1, {}, {"QB": 1}),
                   {"better": {"search_rank": 800}, "worse": {"search_rank": 1}})
    assert vals["better"].vor < 0 and vals["worse"].vor < 0
    assert vals["better"].value > vals["worse"].value


# ── superflex/2QB replacement demand ───────────────────────────────────────────

def test_superflex_replacement_accounts_for_two_startable_qbs_per_team() -> None:
    assert superflex_rules().replacement_ranks()["QB"] >= 24


def test_superflex_op_demand_does_not_inflate_rb_wr_te_replacement() -> None:
    base = one_qb_rules().replacement_ranks()
    sf = superflex_rules().replacement_ranks()
    for pos in ("RB", "WR", "TE"):
        assert sf[pos] == base[pos], pos


def test_one_qb_replacement_unchanged() -> None:
    assert one_qb_rules().replacement_ranks()["QB"] == 12


def test_superflex_qb_vor_rises_with_correct_demand() -> None:
    """Deeper QB replacement ⇒ lower baseline ⇒ elite-QB VOR strictly higher in SF."""
    projs = {f"qb{i}": mk_proj(f"qb{i}", 400.0 - 8 * i) for i in range(32)}
    pos = {p: "QB" for p in projs}
    v1 = compute(projs, pos, one_qb_rules())
    v2 = compute(projs, pos, superflex_rules())
    assert v2["qb0"].vor > v1["qb0"].vor


# ── rookie / missing-ADP explicit degradation ──────────────────────────────────

def test_rookie_with_no_meta_gets_projection_driven_value_without_crash() -> None:
    projs = {"rookie": mk_proj("rookie", 180.0)}
    projs.update({f"rb{i}": mk_proj(f"rb{i}", 170.0 - i) for i in range(30)})
    vals = compute(projs, {p: "RB" for p in projs}, one_qb_rules(), {})  # no meta at all
    assert vals["rookie"].value > 0
    assert vals["rookie"].adp is None  # degrades explicitly, no substitution


def test_missing_adp_does_not_change_value() -> None:
    """Missing ADP degrades explicitly (adp=None) and never alters the shaped value."""
    projs = {"a": mk_proj("a", 150.0)}
    projs.update({f"rb{i}": mk_proj(f"rb{i}", 120.0 - i) for i in range(28)})
    pos = {p: "RB" for p in projs}
    with_adp = compute(projs, pos, one_qb_rules(), {"a": {"adp": 12.0}})
    without = compute(projs, pos, one_qb_rules(), {})
    assert with_adp["a"].value == without["a"].value
    assert with_adp["a"].adp == 12.0 and without["a"].adp is None
