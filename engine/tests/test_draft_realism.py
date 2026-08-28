from __future__ import annotations

from dataclasses import replace

import pytest

from blitz_engine.backtest import draft_realism as dr
from blitz_engine.simulation.season_eval import SeasonPlayer, build_players


def _player(pid: str, pos: str, value: float = 100.0, bye: int = 1) -> SeasonPlayer:
    return SeasonPlayer(pid, pos, "NFL", bye, (value / 10,) * 18, value, 1)


def _legal_roster() -> list[SeasonPlayer]:
    return [
        _player("q", "QB"),
        _player("r1", "RB"),
        _player("r2", "RB"),
        _player("w1", "WR"),
        _player("w2", "WR"),
        _player("t", "TE"),
        _player("f", "RB"),
        _player("k", "K"),
        _player("d", "DST"),
        _player("b1", "WR"),
        _player("b2", "RB"),
        _player("b3", "TE"),
        _player("b4", "QB"),
    ]


def test_specs_replay_exactly_and_cover_required_formats_and_seats() -> None:
    a = dr.draft_specs(20260828, 18)
    assert a == dr.draft_specs(20260828, 18)
    assert len({s.derived_seed for s in a}) == len(a)
    assert {s.row["teams"] for s in a} == {10, 12, 14}
    assert {s.row["qb_mode"] for s in a} >= {"1qb", "superflex", "2qb"}
    assert {s.row["bench_slots"] for s in a} == {4, 6, 8}
    assert {s.slot_band for s in a} == {"front", "middle", "back"}
    assert all(0 <= s.test_seat < s.row["teams"] for s in a)


def test_specs_change_meaningfully_but_stay_in_the_same_matrix() -> None:
    a, b = dr.draft_specs(1, 18), dr.draft_specs(2, 18)
    assert [s.row["id"] for s in a] == [s.row["id"] for s in b]
    assert 1 <= sum(x.test_seat != y.test_seat for x, y in zip(a, b, strict=True)) <= 18


def test_validate_rosters_accepts_complete_team_and_reports_degraded_metadata() -> None:
    roster = _legal_roster()
    row = dr.row("t10-1qb-std-te0.0-b4-ir0")
    report = dr.validate_rosters([roster], row)
    assert report[0]["legal"] and report[0]["starter_complete"]
    degraded = [replace(p, bye_week=0) for p in roster]
    assert dr.validate_rosters([degraded], row)[0]["missing_bye_count"] == len(roster)


def test_validate_rosters_rejects_duplicate_and_incomplete_teams() -> None:
    row = dr.row("t10-1qb-std-te0.0-b4-ir0")
    roster = _legal_roster()
    with pytest.raises(ValueError, match="duplicate"):
        dr.validate_rosters([roster, roster], row)
    broken = [p for p in roster if p.position != "QB"]
    with pytest.raises(ValueError, match="illegal"):
        dr.validate_rosters([broken], row)


def test_classification_is_honest_about_weak_and_invalid_teams() -> None:
    weak = dr.classify_team(
        legal=True,
        complete=True,
        started_points=800,
        league_median=1200,
        delta_ci=(-500, -250),
        h2h=0.30,
        playoff=0.05,
        playoff_baseline=0.50,
    )
    assert weak == {"classification": "UNACCEPTABLE", "winnable": False}
    invalid = dr.classify_team(
        legal=False,
        complete=False,
        started_points=2000,
        league_median=1200,
        delta_ci=(700, 900),
        h2h=0.90,
        playoff=0.90,
        playoff_baseline=0.50,
    )
    assert invalid == {"classification": "UNACCEPTABLE", "winnable": False}


def test_classification_uses_uncertainty_without_promising_a_win() -> None:
    result = dr.classify_team(
        legal=True,
        complete=True,
        started_points=1180,
        league_median=1200,
        delta_ci=(-80, 30),
        h2h=0.49,
        playoff=0.45,
        playoff_baseline=0.50,
    )
    assert result == {"classification": "ACCEPTABLE", "winnable": True}


def test_real_bridge_replays_seed_and_varies_without_duplicates() -> None:
    specs = dr.draft_specs(20260828, 2)
    first = dr.draft(specs)
    assert first == dr.draft(specs)
    drafted = [pid for result in first for team in result["rosters"] for pid in team]
    for result in first:
        flat = [pid for team in result["rosters"] for pid in team]
        assert len(flat) == len(set(flat))
    assert first[0]["rosters"] != first[1]["rosters"]
    assert drafted


def test_real_bridge_completes_every_required_roster() -> None:
    specs = dr.draft_specs(20260828, 18)
    for spec, result in zip(specs, dr.draft(specs), strict=True):
        by_id = {p.player_id: p for p in build_players(2024, spec.row["id"])}
        rosters = [[by_id[pid] for pid in ids] for ids in result["rosters"]]
        reports = dr.validate_rosters(rosters, spec.row)
        assert all(r["legal"] and r["starter_complete"] for r in reports)


def test_evaluate_draft_reports_required_reality_dimensions() -> None:
    spec = dr.draft_specs(20260828, 1)[0]
    result = dr.evaluate_draft(spec, dr.draft([spec])[0], n_seasons=2)
    assert result["synthetic_non_authoritative"] is True
    assert result["model_evaluator"] == dr.EVALUATOR
    assert len(result["player_selections"]) == spec.row["teams"]
    if not result["test_team"]["legal"]:
        assert result["test_team"]["classification"] == "UNACCEPTABLE"
        assert result["test_team"]["winnable"] is False
    assert {
        "starter_strength_vs_median",
        "bench_coverage",
        "replacement_quality",
        "bye_absence_coverage",
        "contingent_role_upside",
        "positional_scarcity_redundancy",
        "paired_h2h",
        "playoff_proxy",
        "championship_proxy",
        "uncertainty",
        "classification",
        "winnable",
    } <= result["test_team"].keys()


def test_invalid_roster_has_zero_replacement_quality_instead_of_crashing() -> None:
    spec = dr.draft_specs(20260828, 1)[0]
    result = dr.draft([spec])[0]
    pool = build_players(2024, spec.row["id"])
    by_id = {p.player_id: p for p in pool}
    drafted = {pid for roster in result["rosters"] for pid in roster}
    roster = result["rosters"][spec.test_seat]
    kicker = next(i for i, pid in enumerate(roster) if by_id[pid].position == "K")
    roster[kicker] = next(
        p.player_id for p in pool if p.position == "WR" and p.player_id not in drafted
    )

    report = dr.evaluate_draft(spec, result, n_seasons=1)
    assert report["test_team"]["legal"] is False
    assert report["test_team"]["replacement_quality"] == 0
