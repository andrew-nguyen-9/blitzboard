from __future__ import annotations

import json
from collections import Counter

import pandas as pd
import pytest

from blitz_engine.backtest import blind_market as bm
from blitz_engine.backtest.static_fit import run_bridge
from blitz_engine.simulation.season_eval import build_players
from blitz_engine.testing import matrix


def _job(*, reverse: bool = False) -> dict:
    row = matrix.by_id("t10-1qb-std-te0.0-b4-ir0")
    ids = [player.player_id for player in build_players(2024, row["id"])]
    if reverse:
        ids.reverse()
    return {
        "row": row,
        "seed": 884422,
        "market_adp": {pid: rank for rank, pid in enumerate(ids, start=1)},
        "arms": {"human": {"chooser": "human_adp", "top_k": 1}},
        "assign": ["human"] * row["teams"],
        "include_picks": True,
    }


def test_bridge_runs_source_isolated_market_opponents_and_records_picks() -> None:
    job = _job()
    result = run_bridge([job])[0]
    assert result["picks"][0]["player_id"] == min(job["market_adp"], key=job["market_adp"].get)
    assert result["picks"][0]["position"] in {"QB", "RB", "WR", "TE", "K", "DST"}
    assert {pick["chooser"] for pick in result["picks"]} == {"human_adp"}
    assert len(result["picks"]) == sum(len(roster) for roster in result["rosters"])


def test_bridge_opt_in_records_four_model_candidates_without_rollouts() -> None:
    job = _job()
    job["arms"] = {"candidate": {}}
    job["assign"] = ["candidate"] * job["row"]["teams"]
    job["recommendation_arms"] = ["candidate"]
    result = run_bridge([job])[0]

    first = result["recommendations"][0]
    assert first["pick_no"] == 1
    assert first["team"] == 1
    assert first["recommendation_randomness"] == 0
    assert first["selected_player_id"] == result["picks"][0]["player_id"]
    assert len(first["candidates"]) == 4
    assert (
        first["candidates"][0]["explanation"]["candidateId"]
        == first["candidates"][0]["player_id"]
    )
    assert first["candidates"][0]["explanation"]["runtime"] == {
        "resolverCalls": 1,
        "simulationTrials": 0,
        "seasonRollouts": 0,
        "monteCarloSamples": 0,
    }

    control = dict(job)
    control.pop("recommendation_arms")
    assert run_bridge([control])[0]["picks"] == result["picks"]


def test_bridge_rejects_model_recommendation_trace_for_market_only_arm() -> None:
    job = _job()
    job["recommendation_arms"] = ["human"]
    with pytest.raises(RuntimeError, match="recommendation trace requires a model arm"):
        run_bridge([job])


def test_bridge_market_rank_is_causal_and_seed_replays_exactly() -> None:
    forward = run_bridge([_job()])[0]
    assert forward == run_bridge([_job()])[0]
    reverse = run_bridge([_job(reverse=True)])[0]
    assert forward["rosters"] != reverse["rosters"]
    assert forward["picks"][0]["player_id"] != reverse["picks"][0]["player_id"]


def test_bridge_rejects_unknown_chooser_instead_of_falling_back_to_v5() -> None:
    job = _job()
    job["arms"]["human"]["chooser"] = "forged-model-assisted-human"
    with pytest.raises(RuntimeError, match="unknown chooser"):
        run_bridge([job])


def test_bridge_can_add_preseason_market_players_missing_from_outcome_fixture() -> None:
    job = _job()
    job["market_adp"] = {**job["market_adp"], "market-missing": 0.5}
    job["extra_players"] = [
        {
            "id": "market-missing",
            "full_name": "Missing Outcome Player",
            "position": "RB",
            "nfl_team": "TST",
            "bye_week": 9,
            "projection": 250.0,
            "boom": 320.0,
            "bust": 180.0,
        }
    ]
    result = run_bridge([job])[0]
    assert result["picks"][0]["player_id"] == "market-missing"


def test_bridge_can_shadow_alternate_preseason_distributions_without_changing_fixture() -> None:
    row = matrix.by_id("t10-1qb-std-te0.0-b4-ir0")
    pool = build_players(2024, row["id"])
    target = min((player for player in pool if player.position == "RB"), key=lambda p: p.projection)
    job = {
        "row": row,
        "seed": 884422,
        "arms": {"v5": {}},
        "assign": ["v5"] * row["teams"],
        "include_picks": True,
        "player_overrides": {
            target.player_id: {"projection": 10000.0, "boom": 11000.0, "bust": 9000.0}
        },
    }
    result = run_bridge([job])[0]
    assert result["picks"][0]["player_id"] == target.player_id

    job["player_overrides"][target.player_id] = {
        "projection": 100.0,
        "boom": 90.0,
        "bust": 110.0,
    }
    with pytest.raises(RuntimeError, match="ordered finite"):
        run_bridge([job])


def test_bridge_candidate_availability_is_causal_but_human_arm_is_source_isolated() -> None:
    row = matrix.by_id("t10-1qb-std-te0.0-b4-ir0")
    candidate = {
        "row": row,
        "seed": 884422,
        "arms": {"candidate": {}},
        "assign": ["candidate"] * row["teams"],
        "include_picks": True,
    }
    baseline = run_bridge([candidate])[0]
    first = baseline["picks"][0]["player_id"]
    candidate["availability_by_arm"] = {"candidate": {first: 0.0}}
    discounted = run_bridge([candidate])[0]
    assert discounted["picks"][0]["player_id"] != first
    assert run_bridge([candidate])[0] == discounted

    human = _job()
    human_baseline = run_bridge([human])[0]
    human["availability_by_arm"] = {
        "human": {player_id: 0.0 for player_id in human["market_adp"]}
    }
    assert run_bridge([human])[0] == human_baseline


def test_bridge_rejects_invalid_candidate_availability_probability() -> None:
    job = _job()
    job["arms"] = {"candidate": {}}
    job["assign"] = ["candidate"] * job["row"]["teams"]
    job["availability_by_arm"] = {"candidate": {"forged": 1.01}}
    with pytest.raises(RuntimeError, match="finite probabilities in \\[0, 1\\]"):
        run_bridge([job])


def test_campaign_rejects_one_availability_map_across_multiple_target_seasons(tmp_path) -> None:
    with pytest.raises(ValueError, match="exactly one target season"):
        bm.run_campaign(
            market_dir=tmp_path,
            weekly_dir=tmp_path,
            base_seed=7,
            repetitions=1,
            top_ks=(8,),
            n_seasons=1,
            seasons=(2021, 2024),
            availability_by_player={"p1": 0.5},
        )


def test_market_matching_normalizes_punctuation_suffixes_and_position_aliases() -> None:
    fixture = [
        {"player_id": "p1", "name": "D.J. Moore", "position": "WR"},
        {"player_id": "p2", "name": "Kenneth Walker III", "position": "RB"},
        {"player_id": "p3", "name": "Buffalo Bills", "position": "DST"},
        {"player_id": "p4", "name": "Jake Elliott", "position": "K"},
        {"player_id": "p5", "name": "B.Aubrey", "position": "K", "nfl_team": "DAL"},
        {"player_id": "p6", "name": "Marquise Brown", "position": "WR", "nfl_team": "KC"},
    ]
    raw = [
        {"name": "DJ Moore Jr.", "position": "WR", "adp": 12.5},
        {"name": "Kenneth Walker", "position": "RB", "adp": 18.0},
        {"name": "Buffalo Defense", "position": "DEF", "adp": 150.0},
        {"name": "Jake Elliott", "position": "PK", "adp": 160.0},
        {"name": "Brandon Aubrey", "position": "PK", "team": "DAL", "adp": 161.0},
        {"name": "Hollywood Brown", "position": "WR", "team": "KC", "adp": 78.2},
    ]
    matched = bm.match_market_players(raw, fixture)
    assert matched.ranks == {
        "p1": 12.5,
        "p2": 18.0,
        "p3": 150.0,
        "p4": 160.0,
        "p5": 161.0,
        "p6": 78.2,
    }
    assert matched.matched == 6
    assert not matched.ambiguous


def test_market_snapshot_records_raw_hash_and_rejects_wrong_format(tmp_path) -> None:
    fixture = [{"player_id": "p1", "name": "A Player", "position": "RB"}]
    path = tmp_path / "snapshot.json"
    path.write_text(
        json.dumps(
            {
                "meta": {"type": "Half-PPR", "teams": 12, "total_drafts": 50},
                "players": [{"name": "A Player", "position": "RB", "adp": 1.0}],
            }
        )
    )
    snapshot = bm.load_market_snapshot(path, season=2024, market_format="half-ppr", fixture=fixture)
    assert len(snapshot.sha256) == 64
    assert snapshot.ranks == {"p1": 1.0}
    assert snapshot.total_drafts == 50
    try:
        bm.load_market_snapshot(path, season=2024, market_format="2qb", fixture=fixture)
    except ValueError as exc:
        assert "format" in str(exc).lower()
    else:  # pragma: no cover - assertion guard
        raise AssertionError("wrong-format snapshot was accepted")


def test_frozen_market_authority_rejects_source_drift() -> None:
    snapshot = bm.MarketSnapshot(
        season=2024,
        market_format="half-ppr",
        provider="test",
        source="tampered.json",
        sha256="0" * 64,
        total_drafts=1,
        raw_players=1,
        matched_players=1,
        ambiguous=(),
        ranks={"p": 1.0},
    )
    with pytest.raises(ValueError, match="snapshot hash mismatch"):
        bm.validate_snapshot_authority(snapshot)


def test_outcome_truncated_market_player_is_restored_from_weekly_history() -> None:
    raw = [
        {
            "player_id": 42,
            "name": "Star Missing",
            "position": "RB",
            "team": "AAA",
            "bye": 9,
            "adp": 1.0,
        },
        {
            "player_id": 43,
            "name": "Rookie Missing",
            "position": "WR",
            "team": "BBB",
            "bye": 10,
            "adp": 80.0,
        },
    ]
    current = pd.DataFrame(
        [
            {
                "player_id": "gsis-star",
                "player_display_name": "Star Missing",
                "position": "RB",
                "recent_team": "AAA",
                "season_type": "REG",
                "week": 1,
                "fantasy_points": 9.0,
                "fantasy_points_ppr": 11.0,
                "receptions": 2,
            }
        ]
    )
    prior = pd.DataFrame(
        [
            {
                "player_id": "gsis-star",
                "player_display_name": "Star Missing",
                "position": "RB",
                "recent_team": "AAA",
                "season_type": "REG",
                "week": 1,
                "fantasy_points": 4.0,
                "fantasy_points_ppr": 6.0,
                "receptions": 2,
            },
            {
                "player_id": "gsis-star",
                "player_display_name": "Star Missing",
                "position": "RB",
                "recent_team": "AAA",
                "season_type": "REG",
                "week": 2,
                "fantasy_points": 14.0,
                "fantasy_points_ppr": 16.0,
                "receptions": 2,
            },
        ]
    )
    row = matrix.by_id("t12-1qb-half-te0.0-b6-ir0")
    augmented = bm.augment_market_players(raw, [], current, prior, row=row, season=2024, weeks=17)
    assert augmented.market_ranks["gsis-star"] == 1.0
    node = next(player for player in augmented.node_players if player["id"] == "gsis-star")
    assert node["projection"] == 170.0
    season_player = next(
        player for player in augmented.season_players if player.player_id == "gsis-star"
    )
    assert season_player.points_if_plays[0] == 10.0
    rookie = next(
        player for player in augmented.node_players if player["full_name"] == "Rookie Missing"
    )
    assert rookie["projection"] == 0.0
    assert augmented.preseason_universe_coverage == 1.0


def test_blind_specs_stratify_year_format_seat_and_random_seed() -> None:
    cases = bm.blind_specs(99117, repetitions=2, top_ks=(1, 8))
    assert cases == bm.blind_specs(99117, repetitions=2, top_ks=(1, 8))
    assert len(cases) == 3 * len(bm.SCENARIO_IDS) * 3 * 2 * 2
    assert {case.spec.season for case in cases} == {2018, 2021, 2024}
    assert {case.spec.slot_band for case in cases} == {"front", "middle", "back"}
    assert {case.market_format for case in cases} == {"half-ppr", "2qb"}
    assert {case.top_k for case in cases} == {1, 8}
    assert set(Counter(case.spec.derived_seed for case in cases).values()) == {2}
    assert all(0 <= case.spec.test_seat < case.spec.row["teams"] for case in cases)


def test_blind_specs_can_freeze_a_recent_season_and_scenario_subset() -> None:
    scenario = "t12-1qb-half-te0.0-b6-ir0"
    cases = bm.blind_specs(
        99117,
        repetitions=2,
        top_ks=(8,),
        seasons=(2024,),
        scenario_ids=(scenario,),
    )
    assert len(cases) == 3 * 2
    assert {case.spec.season for case in cases} == {2024}
    assert {case.spec.row["id"] for case in cases} == {scenario}


def test_blind_job_assigns_one_v5_seat_and_no_model_fields_to_human_arm() -> None:
    case = bm.blind_specs(7, repetitions=1, top_ks=(8,))[0]
    snapshot = bm.MarketSnapshot(
        season=case.spec.season,
        market_format=case.market_format,
        provider="test",
        source="fixture",
        sha256="a" * 64,
        total_drafts=100,
        raw_players=2,
        matched_players=2,
        ambiguous=(),
        ranks={"p1": 1.0, "p2": 2.0},
    )
    job = bm.job_for(case, snapshot)
    assert job["assign"].count("v5") == 1
    assert job["assign"][case.spec.test_seat] == "v5"
    assert set(job["arms"]["human"]) == {"chooser", "top_k"}
    assert job["arms"]["human"]["chooser"] == "human_adp"
    assert "policy" not in job["arms"]["human"]
    assert job["market_adp"] == snapshot.ranks


def test_blind_job_can_opt_in_to_test_arm_recommendation_trace() -> None:
    case = bm.blind_specs(7, repetitions=1, top_ks=(8,), seasons=(2024,))[0]
    snapshot = bm.MarketSnapshot(
        season=case.spec.season,
        market_format=case.market_format,
        provider="test",
        source="fixture",
        sha256="a" * 64,
        total_drafts=100,
        raw_players=2,
        matched_players=2,
        ambiguous=(),
        ranks={"p1": 1.0, "p2": 2.0},
    )
    job = bm.job_for(case, snapshot, include_recommendations=True)
    assert job["recommendation_arms"] == ["v5"]
    assert job["arms"]["human"] == {"chooser": "human_adp", "top_k": 8}


def test_blind_job_supports_policy_ablation_and_heterogeneous_source_isolated_opponents() -> None:
    case = bm.blind_specs(7, repetitions=1, top_ks=(8,), seasons=(2024,))[0]
    snapshot = bm.MarketSnapshot(
        season=case.spec.season,
        market_format=case.market_format,
        provider="test",
        source="fixture",
        sha256="a" * 64,
        total_drafts=100,
        raw_players=2,
        matched_players=2,
        ambiguous=(),
        ranks={"p1": 1.0, "p2": 2.0},
    )
    job = bm.job_for(
        case,
        snapshot,
        test_policy={"runDepletion": 1.0},
        opponent_profile=(1, 4, 8, 12),
    )
    assert job["assign"].count("candidate") == 1
    assert job["arms"]["candidate"] == {"policy": {"runDepletion": 1.0}}
    human_arms = {name: arm for name, arm in job["arms"].items() if name != "candidate"}
    assert {arm["top_k"] for arm in human_arms.values()} == {1, 4, 8, 12}
    assert all(set(arm) == {"chooser", "top_k"} for arm in human_arms.values())
    assert all(arm["chooser"] == "human_adp" for arm in human_arms.values())


def test_blind_job_labels_forecast_overrides_as_a_candidate_shadow() -> None:
    case = bm.blind_specs(7, repetitions=1, top_ks=(8,), seasons=(2024,))[0]
    snapshot = bm.MarketSnapshot(
        season=case.spec.season,
        market_format=case.market_format,
        provider="test",
        source="fixture",
        sha256="a" * 64,
        total_drafts=100,
        raw_players=1,
        matched_players=1,
        ambiguous=(),
        ranks={"p1": 1.0},
    )
    overrides = {"p1": {"projection": 100.0, "boom": 120.0, "bust": 80.0}}
    job = bm.job_for(case, snapshot, player_overrides=overrides)
    assert job["assign"][case.spec.test_seat] == "candidate"
    assert job["arms"]["candidate"] == {}
    assert job["player_overrides"] == overrides


def test_blind_job_scopes_availability_forecast_to_candidate_arm() -> None:
    case = bm.blind_specs(7, repetitions=1, top_ks=(8,), seasons=(2024,))[0]
    snapshot = bm.MarketSnapshot(
        season=case.spec.season,
        market_format=case.market_format,
        provider="test",
        source="fixture",
        sha256="a" * 64,
        total_drafts=100,
        raw_players=1,
        matched_players=1,
        ambiguous=(),
        ranks={"p1": 1.0},
    )
    availability = {"p1": 0.25}
    job = bm.job_for(case, snapshot, availability_by_player=availability)
    assert job["assign"][case.spec.test_seat] == "candidate"
    assert job["availability_by_arm"] == {"candidate": availability}
    assert "availability" not in job["arms"]["human"]


def test_competitive_assessment_is_honest_about_clear_underperformance() -> None:
    evidence = {
        "starter_strength_ci95": [0.90, 0.96],
        "h2h_ci95": [0.35, 0.44],
        "playoff_delta_ci95": [-0.25, -0.10],
    }
    assert bm.competitive_assessment(evidence)["verdict"] == "UNDERPERFORMS"


def test_bootstrap_interval_replays_and_contains_the_sample_mean() -> None:
    values = [0.2, 0.4, 0.5, 0.7, 0.9]
    first = bm.bootstrap_ci(values, seed=1234, resamples=500)
    assert first == bm.bootstrap_ci(values, seed=1234, resamples=500)
    assert first[0] <= sum(values) / len(values) <= first[1]


def test_bootstrap_interval_supports_preregistered_multiplicity_level() -> None:
    values = [0.1, 0.2, 0.4, 0.7, 0.9, 1.1]
    standard = bm.bootstrap_ci(values, seed=1234, resamples=2000, confidence=0.95)
    adjusted = bm.bootstrap_ci(values, seed=1234, resamples=2000, confidence=0.9833333333)
    assert adjusted[0] <= standard[0] <= standard[1] <= adjusted[1]


def test_cluster_bootstrap_counts_paired_sensitivity_arms_once() -> None:
    clustered = bm.cluster_bootstrap_ci(
        [0.0, 0.0, 1.0, 1.0], ["low", "low", "high", "high"], seed=44, resamples=500
    )
    independent_cells = bm.bootstrap_ci([0.0, 1.0], seed=44, resamples=500)
    assert clustered == independent_cells


def test_top_k_sensitivity_is_paired_by_design_cell() -> None:
    reports = []
    for seed, base in ((1, 0.40), (2, 0.50)):
        for top_k, lift in ((8, 0.0), (12, 0.10)):
            reports.append(
                {
                    "derived_seed": seed,
                    "opponent_top_k": top_k,
                    "test_team": {
                        "starter_strength_vs_median": 1 + lift,
                        "paired_h2h": base + lift,
                    },
                    "playoff_delta_vs_baseline": lift,
                    "test_team_finish_rank": 6 - lift * 10,
                }
            )
    result = bm.paired_top_k_effects(reports, baseline=8, seed=22)
    assert result["12_minus_8"]["pairs"] == 2
    assert result["12_minus_8"]["mean_h2h_delta"] == 0.1
    assert result["12_minus_8"]["mean_finish_rank_delta"] == -1.0


def test_campaign_effects_pair_treatment_minus_reference_by_seed() -> None:
    reference = []
    treatment = []
    for seed, base in ((1, 0.40), (2, 0.50), (3, 0.60)):
        common = {
            "derived_seed": seed,
            "test_team": {
                "starter_strength_vs_median": 1.0,
                "paired_h2h": base,
            },
            "playoff_delta_vs_baseline": 0.0,
            "test_team_finish_rank": 6.0,
            "all_rosters_legal": True,
            "duplicate_free": True,
        }
        reference.append(common)
        treatment.append(
            {
                **common,
                "test_team": {
                    "starter_strength_vs_median": 1.1,
                    "paired_h2h": base + 0.05,
                },
                "playoff_delta_vs_baseline": 0.02,
                "test_team_finish_rank": 5.0,
            }
        )
    result = bm.paired_campaign_effects(
        reference,
        treatment,
        seed=22,
        confidence=0.9833333333,
    )
    assert result["pairs"] == 3
    assert result["all_treatment_rosters_legal"]
    assert result["all_treatment_drafts_duplicate_free"]
    assert result["mean_h2h_delta"] == 0.05
    assert result["mean_finish_rank_delta"] == -1.0


def test_market_metadata_dropout_is_exact_reproducible_and_bounded() -> None:
    ranks = {f"p{i}": float(i) for i in range(100)}
    first = bm.degrade_market_ranks(ranks, fraction=0.30, seed=88)
    assert first == bm.degrade_market_ranks(ranks, fraction=0.30, seed=88)
    assert len(first) == 70
    assert first != bm.degrade_market_ranks(ranks, fraction=0.30, seed=89)
    assert bm.degrade_market_ranks(ranks, fraction=0.0, seed=88) == ranks


def test_evidence_hash_ignores_timing_but_detects_result_mutation() -> None:
    first = {"elapsed_seconds": 1.2, "result": {"score": 10, "elapsed_seconds": 0.1}}
    replay = {"elapsed_seconds": 9.9, "result": {"score": 10, "elapsed_seconds": 5.0}}
    mutated = {"elapsed_seconds": 1.2, "result": {"score": 11, "elapsed_seconds": 0.1}}
    assert bm.evidence_hash(first) == bm.evidence_hash(replay)
    assert bm.evidence_hash(first) != bm.evidence_hash(mutated)
    stored = {**first, "evidence_sha256": bm.evidence_hash(first)}
    assert bm.evidence_hash(stored) == stored["evidence_sha256"]
