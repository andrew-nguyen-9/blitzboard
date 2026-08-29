"""Blind market-opponent benchmark for the shipped TypeScript v5 draft policy.

Only the test seat runs BlitzBoard. Every opponent follows a historical market ADP
snapshot with seeded, bounded reaches and roster-completion guards implemented by
``frontend/lib/draftAI.ts::pickHumanAdp``. Market opponents never receive model fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import re
import time
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from blitz_engine.backtest import draft_realism as dr
from blitz_engine.backtest.static_fit import run_bridge
from blitz_engine.simulation import season_eval as se
from blitz_engine.simulation.season_eval import SeasonPlayer

SCENARIO_IDS = dr.SCENARIO_IDS
SEASONS = (2018, 2021, 2024)
PROVIDER = "Fantasy Football Calculator historical aggregate ADP"
SNAPSHOT_HASHES = {
    (2018, "half-ppr"): "5c88429b8f386b228edec3f8294018cfe9ddc2ee0634a65930186c598674584e",
    (2018, "2qb"): "842b371b1275dd53dcf3d818aefc17578044a29580b0eb2d61fcb9ec316fe918",
    (2021, "half-ppr"): "17e4d005383dbc78e7755fbd77d72268b6b34a650df35c215e8491dc42876ac8",
    (2021, "2qb"): "bbf6a046e82b4026ae75d6f254453370da704cb7cec27c7b97c3818a9eb672b1",
    (2024, "half-ppr"): "078df731fbe26812d59535b5c3339ae96b9cc062cc2239218a4da9d5ddbee7b1",
    (2024, "2qb"): "5c60396e524257e5e0c96a9f613791accc6b2043a35c4d4bdb601549a98b87e9",
}


@dataclass(frozen=True)
class MarketMatch:
    ranks: dict[str, float]
    matched: int
    ambiguous: tuple[str, ...]


@dataclass(frozen=True)
class MarketSnapshot:
    season: int
    market_format: str
    provider: str
    source: str
    sha256: str
    total_drafts: int
    raw_players: int
    matched_players: int
    ambiguous: tuple[str, ...]
    ranks: dict[str, float]


@dataclass(frozen=True)
class BlindCase:
    spec: dr.DraftSpec
    top_k: int
    market_format: str


@dataclass(frozen=True)
class AugmentedMarket:
    market_ranks: dict[str, float]
    node_players: tuple[dict[str, Any], ...]
    season_players: tuple[SeasonPlayer, ...]
    preseason_universe_coverage: float
    synthetic_player_ids: tuple[str, ...]


_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
_NAME_ALIASES = {"hollywoodbrown": "marquisebrown"}
_DEFENSE_ALIASES = {
    "arizona": "ARI",
    "cardinals": "ARI",
    "atlanta": "ATL",
    "falcons": "ATL",
    "baltimore": "BAL",
    "ravens": "BAL",
    "buffalo": "BUF",
    "bills": "BUF",
    "carolina": "CAR",
    "panthers": "CAR",
    "chicago": "CHI",
    "bears": "CHI",
    "cincinnati": "CIN",
    "bengals": "CIN",
    "cleveland": "CLE",
    "browns": "CLE",
    "dallas": "DAL",
    "cowboys": "DAL",
    "denver": "DEN",
    "broncos": "DEN",
    "detroit": "DET",
    "lions": "DET",
    "greenbay": "GB",
    "packers": "GB",
    "houston": "HOU",
    "texans": "HOU",
    "indianapolis": "IND",
    "colts": "IND",
    "jacksonville": "JAX",
    "jaguars": "JAX",
    "kansascity": "KC",
    "chiefs": "KC",
    "lasvegas": "LV",
    "oakland": "LV",
    "raiders": "LV",
    "chargers": "LAC",
    "losangeleschargers": "LAC",
    "rams": "LAR",
    "losangelesrams": "LAR",
    "miami": "MIA",
    "dolphins": "MIA",
    "minnesota": "MIN",
    "vikings": "MIN",
    "newengland": "NE",
    "patriots": "NE",
    "neworleans": "NO",
    "saints": "NO",
    "newyorkgiants": "NYG",
    "giants": "NYG",
    "newyorkjets": "NYJ",
    "jets": "NYJ",
    "philadelphia": "PHI",
    "eagles": "PHI",
    "pittsburgh": "PIT",
    "steelers": "PIT",
    "sanfrancisco": "SF",
    "49ers": "SF",
    "seattle": "SEA",
    "seahawks": "SEA",
    "tampabay": "TB",
    "buccaneers": "TB",
    "tennessee": "TEN",
    "titans": "TEN",
    "washington": "WAS",
    "commanders": "WAS",
    "footballteam": "WAS",
    "redskins": "WAS",
}


def _name_tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    return tokens


def normalize_name(name: str) -> str:
    normalized = "".join(_name_tokens(name))
    return _NAME_ALIASES.get(normalized, normalized)


def _short_name(name: str) -> str:
    tokens = _name_tokens(name)
    return f"{tokens[0][0]}{tokens[-1]}" if len(tokens) >= 2 else "".join(tokens)


def _position(position: str) -> str:
    position = position.upper()
    if position in {"DEF", "D/ST"}:
        return "DST"
    if position == "PK":
        return "K"
    return position


def _defense_key(name: str) -> str:
    normalized = normalize_name(name)
    normalized = normalized.replace("defense", "").replace("dst", "")
    for alias, code in sorted(_DEFENSE_ALIASES.items(), key=lambda item: -len(item[0])):
        if alias in normalized:
            return code
    return normalized.upper()


def _resolve_player(
    raw: dict[str, Any], candidates: Iterable[dict[str, Any]]
) -> tuple[str | None, bool]:
    pos = _position(str(raw.get("position", "")))
    raw_name = str(raw.get("name", ""))
    exact_name = _defense_key(raw_name) if pos == "DST" else normalize_name(raw_name)
    short_name = _short_name(raw_name)
    exact: list[tuple[str, str]] = []
    short: list[tuple[str, str]] = []
    for candidate in candidates:
        if _position(str(candidate.get("position", ""))) != pos:
            continue
        name = str(candidate.get("name", candidate.get("player_display_name", "")))
        pid = str(candidate["player_id"])
        team = str(candidate.get("nfl_team", candidate.get("recent_team", ""))).upper()
        candidate_name = _defense_key(name) if pos == "DST" else normalize_name(name)
        if candidate_name == exact_name:
            exact.append((pid, team))
        elif pos != "DST" and _short_name(name) == short_name:
            short.append((pid, team))
    matches = exact or short
    raw_team = str(raw.get("team", "")).upper()
    if len(matches) > 1 and raw_team:
        by_team = [match for match in matches if match[1] == raw_team]
        if by_team:
            matches = by_team
    ids = sorted({pid for pid, _ in matches})
    return (ids[0], False) if len(ids) == 1 else (None, len(ids) > 1)


def match_market_players(
    raw_players: Iterable[dict[str, Any]], fixture_players: Iterable[dict[str, Any]]
) -> MarketMatch:
    fixture = list(fixture_players)

    ranks: dict[str, float] = {}
    ambiguous: list[str] = []
    for player in raw_players:
        try:
            adp = float(player["adp"])
        except (KeyError, TypeError, ValueError):
            continue
        if not np.isfinite(adp):
            continue
        pid, is_ambiguous = _resolve_player(player, fixture)
        if pid is not None:
            ranks[pid] = adp
        elif is_ambiguous:
            pos = _position(str(player.get("position", "")))
            ambiguous.append(f"{player.get('name')}:{pos}")
    return MarketMatch(ranks, len(ranks), tuple(sorted(ambiguous)))


def _weekly_score(frame: Any, scoring: str, te_premium: float, position: str) -> np.ndarray:
    if frame.empty:
        return np.asarray([], dtype=float)
    standard = frame["fantasy_points"].fillna(0).to_numpy(dtype=float)
    ppr = frame["fantasy_points_ppr"].to_numpy(dtype=float)
    ppr = np.where(np.isfinite(ppr), ppr, standard)
    if scoring == "std":
        points = standard
    elif scoring == "ppr":
        points = ppr
    else:
        points = (standard + ppr) / 2
    if position == "TE" and te_premium:
        points = points + frame["receptions"].fillna(0).to_numpy(dtype=float) * te_premium
    return points


def augment_market_players(
    raw_players: Sequence[dict[str, Any]],
    fixture_players: Sequence[dict[str, Any]],
    current_weekly: Any,
    prior_weekly: Any,
    *,
    row: dict[str, Any],
    season: int,
    weeks: int,
) -> AugmentedMarket:
    """Restore ADP-ranked players removed by the fixture's realised-points truncation."""
    if "season_type" in current_weekly:
        current_weekly = current_weekly[current_weekly["season_type"] == "REG"]
    if "season_type" in prior_weekly:
        prior_weekly = prior_weekly[prior_weekly["season_type"] == "REG"]
    identity_columns = ["player_id", "player_display_name", "position", "recent_team"]
    identities = (
        pd.concat(
            [
                current_weekly.reindex(columns=identity_columns),
                prior_weekly.reindex(columns=identity_columns),
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .rename(columns={"player_display_name": "name", "recent_team": "nfl_team"})
        .to_dict("records")
    )
    fixture_ids = {str(player["player_id"]) for player in fixture_players}
    market_ranks = match_market_players(raw_players, fixture_players).ranks
    node_players: list[dict[str, Any]] = []
    season_players: list[SeasonPlayer] = []
    synthetic_ids: list[str] = []
    seen = set(fixture_ids)

    for raw in raw_players:
        try:
            adp = float(raw["adp"])
        except (KeyError, TypeError, ValueError):
            continue
        if not np.isfinite(adp):
            continue
        existing, _ = _resolve_player(raw, fixture_players)
        if existing is not None:
            continue
        position = _position(str(raw.get("position", "")))
        if position in {"K", "DST"}:
            continue
        pid, _ = _resolve_player(raw, identities)
        if pid is None:
            token = re.sub(r"[^a-zA-Z0-9]+", "-", str(raw.get("player_id", raw["name"]))).strip("-")
            pid = f"market-{season}-{token}"
            synthetic_ids.append(pid)
        if pid in seen:
            continue
        seen.add(pid)
        market_ranks[pid] = adp
        current = current_weekly[current_weekly["player_id"].astype(str) == pid].sort_values("week")
        prior = prior_weekly[prior_weekly["player_id"].astype(str) == pid].sort_values("week")
        scoring = str(row["scoring"])
        te_premium = float(row["te_premium"])
        previous_points = _weekly_score(prior, scoring, te_premium, position)
        projection = float(previous_points.mean() * weeks) if len(previous_points) else 0.0
        boom = float(np.percentile(previous_points, 85) * weeks) if len(previous_points) else 0.0
        bust = float(np.percentile(previous_points, 15) * weeks) if len(previous_points) else 0.0
        current_points = _weekly_score(current, scoring, te_premium, position)
        by_week = {
            int(week): float(points)
            for week, points in zip(current.get("week", []), current_points, strict=True)
        }
        typical = float(np.median(current_points)) if len(current_points) else 0.0
        weekly = tuple(by_week.get(week, typical) for week in range(1, weeks + 1))
        team = str(raw.get("team", "UNK"))
        bye = int(raw.get("bye") or 0)
        node_players.append(
            {
                "id": pid,
                "full_name": str(raw["name"]),
                "position": position,
                "nfl_team": team,
                "bye_week": bye,
                "projection": round(projection, 2),
                "boom": round(boom, 2),
                "bust": round(bust, 2),
            }
        )
        season_players.append(SeasonPlayer(pid, position, team, bye, weekly, projection, 1))

    valid_raw = sum(
        1
        for player in raw_players
        if isinstance(player.get("adp"), (int, float)) and np.isfinite(player["adp"])
    )
    coverage = len(market_ranks) / valid_raw if valid_raw else 0.0
    return AugmentedMarket(
        market_ranks,
        tuple(node_players),
        tuple(season_players),
        round(coverage, 6),
        tuple(sorted(synthetic_ids)),
    )


def load_market_snapshot(
    path: Path,
    *,
    season: int,
    market_format: str,
    fixture: Sequence[dict[str, Any]] | None = None,
) -> MarketSnapshot:
    raw_bytes = path.read_bytes()
    payload = json.loads(raw_bytes)
    meta = payload.get("meta", {})
    expected = "2 QB" if market_format == "2qb" else "Half-PPR"
    if meta.get("type") != expected:
        raise ValueError(f"market format mismatch: expected {expected!r}, got {meta.get('type')!r}")
    if int(meta.get("teams", 0)) != 12:
        raise ValueError("market snapshot must be a 12-team aggregate")
    if fixture is None:
        fixture = json.loads((dr.ROOT / "fixtures" / "seasons" / f"{season}.json").read_text())[
            "players"
        ]
    matched = match_market_players(payload.get("players", []), fixture)
    return MarketSnapshot(
        season=season,
        market_format=market_format,
        provider=PROVIDER,
        source=str(path),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        total_drafts=int(meta.get("total_drafts", 0)),
        raw_players=len(payload.get("players", [])),
        matched_players=matched.matched,
        ambiguous=matched.ambiguous,
        ranks=matched.ranks,
    )


def validate_snapshot_authority(snapshot: MarketSnapshot) -> None:
    key = (snapshot.season, snapshot.market_format)
    expected = SNAPSHOT_HASHES.get(key)
    if expected is None:
        raise ValueError(f"no frozen snapshot authority for {key}")
    if snapshot.sha256 != expected:
        raise ValueError(
            f"snapshot hash mismatch for {key}: expected {expected}, got {snapshot.sha256}"
        )


def _derived_seed(base_seed: int, index: int) -> int:
    raw = hashlib.blake2s(f"blind:{base_seed}:{index}".encode(), digest_size=4).digest()
    return int.from_bytes(raw) & 0x7FFF_FFFF


def blind_specs(
    base_seed: int,
    *,
    repetitions: int,
    top_ks: Sequence[int] = (8,),
    seasons: Sequence[int] = SEASONS,
    scenario_ids: Sequence[str] = SCENARIO_IDS,
) -> list[BlindCase]:
    if repetitions < 1 or any(k < 1 for k in top_ks):
        raise ValueError("repetitions and top_k values must be positive")
    cases: list[BlindCase] = []
    cell_index = 0
    for season in seasons:
        for scenario_id in scenario_ids:
            league = dr.row(scenario_id)
            teams = int(league["teams"])
            cuts = (0, max(1, teams // 3), max(2, 2 * teams // 3), teams)
            for band_index, band in enumerate(("front", "middle", "back")):
                for _ in range(repetitions):
                    seed = _derived_seed(base_seed, cell_index)
                    cell_index += 1
                    seat = random.Random(seed).randrange(cuts[band_index], cuts[band_index + 1])
                    for top_k in top_ks:
                        index = len(cases)
                        spec = dr.DraftSpec(index, base_seed, seed, league, seat, band, season)
                        market_format = "half-ppr" if league["qb_mode"] == "1qb" else "2qb"
                        cases.append(BlindCase(spec, int(top_k), market_format))
    return cases


def _draft_configuration(
    case: BlindCase,
    test_policy: dict[str, Any] | None,
    opponent_profile: Sequence[int] | None,
    *,
    forecast_shadow: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    test_arm = "candidate" if test_policy or forecast_shadow else "v5"
    arms = {test_arm: {"policy": dict(test_policy)} if test_policy else {}}
    if opponent_profile:
        if any(top_k < 1 for top_k in opponent_profile):
            raise ValueError("opponent profile top_k values must be positive")
        for top_k in sorted(set(opponent_profile)):
            arms[f"human_{top_k}"] = {"chooser": "human_adp", "top_k": int(top_k)}
        assign = [
            f"human_{opponent_profile[seat % len(opponent_profile)]}"
            for seat in range(int(case.spec.row["teams"]))
        ]
    else:
        arms["human"] = {"chooser": "human_adp", "top_k": case.top_k}
        assign = ["human"] * int(case.spec.row["teams"])
    assign[case.spec.test_seat] = test_arm
    return arms, assign


def job_for(
    case: BlindCase,
    snapshot: MarketSnapshot,
    augmentation: AugmentedMarket | None = None,
    *,
    test_policy: dict[str, Any] | None = None,
    opponent_profile: Sequence[int] | None = None,
    player_overrides: dict[str, dict[str, float]] | None = None,
    availability_by_player: dict[str, float] | None = None,
    include_recommendations: bool = False,
) -> dict[str, Any]:
    if (snapshot.season, snapshot.market_format) != (case.spec.season, case.market_format):
        raise ValueError("snapshot does not match blind case")
    arms, assign = _draft_configuration(
        case,
        test_policy,
        opponent_profile,
        forecast_shadow=bool(player_overrides or availability_by_player),
    )
    job = {
        "row": case.spec.row,
        "seed": case.spec.derived_seed,
        "market_adp": augmentation.market_ranks if augmentation else snapshot.ranks,
        "arms": arms,
        "assign": assign,
        "include_picks": True,
    }
    if augmentation and augmentation.node_players:
        job["extra_players"] = list(augmentation.node_players)
    if player_overrides:
        job["player_overrides"] = player_overrides
    if availability_by_player:
        job["availability_by_arm"] = {"candidate": availability_by_player}
    if include_recommendations:
        job["recommendation_arms"] = [assign[case.spec.test_seat]]
    return job


def _prepare_case(
    case: BlindCase,
    market_dir: Path,
    weekly_dir: Path,
    *,
    include_recommendations: bool = False,
) -> tuple[dict[str, Any], list[SeasonPlayer], dict[str, Any]]:
    market_path = market_dir / f"ffc-{case.market_format}-{case.spec.season}.json"
    payload = json.loads(market_path.read_text())
    fixture_doc = json.loads(
        (dr.ROOT / "fixtures" / "seasons" / f"{case.spec.season}.json").read_text()
    )
    fixture = fixture_doc["players"]
    snapshot = load_market_snapshot(
        market_path,
        season=case.spec.season,
        market_format=case.market_format,
        fixture=fixture,
    )
    validate_snapshot_authority(snapshot)
    current = pd.read_pickle(weekly_dir / f"weekly_{case.spec.season}.pkl")
    prior = pd.read_pickle(weekly_dir / f"weekly_{case.spec.season - 1}.pkl")
    augmentation = augment_market_players(
        payload["players"],
        fixture,
        current,
        prior,
        row=case.spec.row,
        season=case.spec.season,
        weeks=int(fixture_doc["weeks"]),
    )
    pool = [*se.build_players(case.spec.season, case.spec.row["id"]), *augmentation.season_players]
    provenance = {
        "provider": snapshot.provider,
        "format": snapshot.market_format,
        "sha256": snapshot.sha256,
        "raw_players": snapshot.raw_players,
        "fixture_matches": snapshot.matched_players,
        "augmented_players": len(augmentation.node_players),
        "synthetic_player_ids": list(augmentation.synthetic_player_ids),
        "preseason_universe_coverage": augmentation.preseason_universe_coverage,
        "provider_draft_sample": snapshot.total_drafts,
    }
    return job_for(
        case,
        snapshot,
        augmentation,
        include_recommendations=include_recommendations,
    ), pool, provenance


def _round(value: float) -> float:
    return round(float(value), 6)


def summarize(reports: Sequence[dict[str, Any]], *, seed: int) -> dict[str, Any]:
    if not reports:
        raise ValueError("cannot summarize an empty campaign")
    starter = [float(report["test_team"]["starter_strength_vs_median"]) for report in reports]
    h2h = [float(report["test_team"]["paired_h2h"]) for report in reports]
    playoff_delta = [float(report["playoff_delta_vs_baseline"]) for report in reports]
    clusters = [str(report["derived_seed"]) for report in reports]
    evidence = {
        "starter_strength_ci95": [
            _round(v) for v in cluster_bootstrap_ci(starter, clusters, seed=seed + 1)
        ],
        "h2h_ci95": [_round(v) for v in cluster_bootstrap_ci(h2h, clusters, seed=seed + 2)],
        "playoff_delta_ci95": [
            _round(v) for v in cluster_bootstrap_ci(playoff_delta, clusters, seed=seed + 3)
        ],
    }
    labels = {name: 0 for name in ("ACCEPTABLE", "BORDERLINE", "UNACCEPTABLE")}
    for report in reports:
        labels[report["test_team"]["classification"]] += 1
    human_picks = [
        pick
        for report in reports
        for pick in report["pick_trace"]
        if pick["chooser"] == "human_adp"
    ]
    ranked_adp = [
        float(pick["market_adp"]) for pick in human_picks if pick["market_adp"] is not None
    ]
    early_v5 = [
        pick
        for report in reports
        for pick in report["pick_trace"]
        if pick["chooser"] == "v5" and pick["pick_no"] <= report["number_of_teams"] * 3
    ]
    early_human = [
        pick
        for report in reports
        for pick in report["pick_trace"]
        if pick["chooser"] == "human_adp" and pick["pick_no"] <= report["number_of_teams"] * 3
    ]
    one_qb_reports = [report for report in reports if report["qb_mode"] == "1qb"]
    v5_one_qb_counts = [
        sum(pick["chooser"] == "v5" and pick["position"] == "QB" for pick in report["pick_trace"])
        for report in one_qb_reports
    ]
    extreme_early = [
        pick
        for report in reports
        for pick in report["pick_trace"]
        if pick["chooser"] == "human_adp"
        and pick["market_adp"] is not None
        and pick["pick_no"] <= len(report["pick_trace"]) / 2
        and float(pick["market_adp"]) > pick["pick_no"] + 24
    ]
    summary = {
        "drafts": len(reports),
        "season_evaluations": sum(int(r["test_team"]["uncertainty"]["n_seasons"]) for r in reports),
        "legal_drafts": sum(bool(report["all_rosters_legal"]) for report in reports),
        "duplicate_free_drafts": sum(bool(report["duplicate_free"]) for report in reports),
        "mean_finish_rank": _round(np.mean([r["test_team_finish_rank"] for r in reports])),
        "median_finish_rank": _round(np.median([r["test_team_finish_rank"] for r in reports])),
        "top_half_rate": _round(np.mean([r["test_team_top_half"] for r in reports])),
        "mean_starter_strength": _round(np.mean(starter)),
        "mean_h2h": _round(np.mean(h2h)),
        "mean_playoff_delta": _round(np.mean(playoff_delta)),
        "mean_championship": _round(
            np.mean([r["test_team"]["championship_proxy"] for r in reports])
        ),
        "classifications": labels,
        "winnable_drafts": sum(bool(r["test_team"]["winnable"]) for r in reports),
        "human_pick_ranked_rate": _round(len(ranked_adp) / len(human_picks))
        if human_picks
        else 0.0,
        "human_market_adp_median": _round(np.median(ranked_adp)) if ranked_adp else None,
        "early_extreme_reach_rate": _round(len(extreme_early) / len(human_picks))
        if human_picks
        else 0.0,
        "allocation_diagnostics": {
            "v5_early_qb_rate": _round(
                sum(pick["position"] == "QB" for pick in early_v5) / len(early_v5)
            )
            if early_v5
            else 0.0,
            "human_early_qb_rate": _round(
                sum(pick["position"] == "QB" for pick in early_human) / len(early_human)
            )
            if early_human
            else 0.0,
            "v5_one_qb_rosters_over_two_qbs": _round(
                sum(count > 2 for count in v5_one_qb_counts) / len(v5_one_qb_counts)
            )
            if v5_one_qb_counts
            else 0.0,
            "v5_one_qb_median_qbs": _round(np.median(v5_one_qb_counts))
            if v5_one_qb_counts
            else 0.0,
        },
        **evidence,
    }
    summary["competitive_assessment"] = competitive_assessment(evidence)
    return summary


def _group_summary(reports: Sequence[dict[str, Any]], key: str, seed: int) -> dict[str, Any]:
    values = sorted({str(report[key]) for report in reports})
    return {
        value: summarize(
            [report for report in reports if str(report[key]) == value], seed=seed + i * 17
        )
        for i, value in enumerate(values)
    }


def paired_top_k_effects(
    reports: Sequence[dict[str, Any]], *, baseline: int = 8, seed: int
) -> dict[str, Any]:
    cells: dict[int, dict[int, dict[str, Any]]] = {}
    for report in reports:
        cells.setdefault(int(report["derived_seed"]), {})[int(report["opponent_top_k"])] = report
    top_ks = sorted(
        {
            int(report["opponent_top_k"])
            for report in reports
            if int(report["opponent_top_k"]) != baseline
        }
    )
    output: dict[str, Any] = {}
    for offset, top_k in enumerate(top_ks):
        pairs = [
            (arms[baseline], arms[top_k])
            for arms in cells.values()
            if baseline in arms and top_k in arms
        ]
        if not pairs:
            continue
        extractors = {
            "starter_strength": lambda report: float(
                report["test_team"]["starter_strength_vs_median"]
            ),
            "h2h": lambda report: float(report["test_team"]["paired_h2h"]),
            "playoff_delta": lambda report: float(report["playoff_delta_vs_baseline"]),
            "finish_rank": lambda report: float(report["test_team_finish_rank"]),
        }
        entry: dict[str, Any] = {"pairs": len(pairs)}
        for metric_index, (name, get) in enumerate(extractors.items()):
            deltas = [get(other) - get(reference) for reference, other in pairs]
            entry[f"mean_{name}_delta"] = _round(np.mean(deltas))
            entry[f"{name}_delta_ci95"] = [
                _round(value)
                for value in bootstrap_ci(
                    deltas, seed=seed + offset * 101 + metric_index, resamples=2000
                )
            ]
        output[f"{top_k}_minus_{baseline}"] = entry
    return output


def paired_campaign_effects(
    reference: Sequence[dict[str, Any]],
    treatment: Sequence[dict[str, Any]],
    *,
    seed: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    reference_by_seed = {int(report["derived_seed"]): report for report in reference}
    treatment_by_seed = {int(report["derived_seed"]): report for report in treatment}
    seeds = sorted(reference_by_seed.keys() & treatment_by_seed.keys())
    if len(seeds) != len(reference) or len(seeds) != len(treatment):
        raise ValueError("campaigns must contain one matching report per derived seed")
    extractors = {
        "starter_strength": lambda report: float(report["test_team"]["starter_strength_vs_median"]),
        "h2h": lambda report: float(report["test_team"]["paired_h2h"]),
        "playoff_delta": lambda report: float(report["playoff_delta_vs_baseline"]),
        "finish_rank": lambda report: float(report["test_team_finish_rank"]),
    }
    output: dict[str, Any] = {
        "pairs": len(seeds),
        "confidence": confidence,
        "all_treatment_rosters_legal": all(
            bool(treatment_by_seed[cell]["all_rosters_legal"]) for cell in seeds
        ),
        "all_treatment_drafts_duplicate_free": all(
            bool(treatment_by_seed[cell]["duplicate_free"]) for cell in seeds
        ),
    }
    for offset, (name, get) in enumerate(extractors.items()):
        deltas = [get(treatment_by_seed[cell]) - get(reference_by_seed[cell]) for cell in seeds]
        output[f"mean_{name}_delta"] = _round(np.mean(deltas))
        output[f"{name}_delta_interval"] = [
            _round(value)
            for value in bootstrap_ci(
                deltas,
                seed=seed + offset,
                resamples=5000,
                confidence=confidence,
            )
        ]
    return output


def run_campaign(
    *,
    market_dir: Path,
    weekly_dir: Path,
    base_seed: int,
    repetitions: int,
    top_ks: Sequence[int],
    n_seasons: int,
    batch_size: int = 72,
    market_dropout: float = 0.0,
    seasons: Sequence[int] = SEASONS,
    scenario_ids: Sequence[str] = SCENARIO_IDS,
    test_policy: dict[str, Any] | None = None,
    opponent_profile: Sequence[int] | None = None,
    player_overrides: dict[str, dict[str, float]] | None = None,
    availability_by_player: dict[str, float] | None = None,
    forecast_identity: str | None = None,
    include_recommendations: bool = False,
) -> dict[str, Any]:
    if not 0 <= market_dropout < 1:
        raise ValueError("market metadata dropout must be in [0, 1)")
    if availability_by_player and len(seasons) != 1:
        raise ValueError("an availability forecast map requires exactly one target season")
    started = time.perf_counter()
    cases = blind_specs(
        base_seed,
        repetitions=repetitions,
        top_ks=top_ks,
        seasons=seasons,
        scenario_ids=scenario_ids,
    )
    cache: dict[
        tuple[int, str, str], tuple[dict[str, Any], list[SeasonPlayer], dict[str, Any]]
    ] = {}
    prepared: list[tuple[dict[str, Any], list[SeasonPlayer], dict[str, Any]]] = []
    for case in cases:
        key = (case.spec.season, case.spec.row["id"], case.market_format)
        if key not in cache:
            cache[key] = _prepare_case(
                case,
                market_dir,
                weekly_dir,
                include_recommendations=include_recommendations,
            )
        template_job, pool, provenance = cache[key]
        arms, assign = _draft_configuration(
            case,
            test_policy,
            opponent_profile,
            forecast_shadow=bool(player_overrides or availability_by_player),
        )
        job = {**template_job, "seed": case.spec.derived_seed, "assign": assign, "arms": arms}
        if player_overrides:
            job["player_overrides"] = player_overrides
        if availability_by_player:
            job["availability_by_arm"] = {"candidate": availability_by_player}
        job["market_adp"] = degrade_market_ranks(
            job["market_adp"], fraction=market_dropout, seed=case.spec.derived_seed + 991
        )
        prepared.append((job, pool, provenance))

    drafted: list[dict[str, Any] | None] = [None] * len(cases)
    for season in seasons:
        indices = [i for i, case in enumerate(cases) if case.spec.season == season]
        for offset in range(0, len(indices), batch_size):
            batch_indices = indices[offset : offset + batch_size]
            results = run_bridge([prepared[i][0] for i in batch_indices], season=season)
            for index, result in zip(batch_indices, results, strict=True):
                drafted[index] = result

    reports: list[dict[str, Any]] = []
    for case, result, (_, pool, provenance) in zip(cases, drafted, prepared, strict=True):
        if result is None:  # pragma: no cover - batch integrity guard
            raise RuntimeError(f"missing result for case {case.spec.index}")
        report = dr.evaluate_draft(
            case.spec,
            result,
            n_seasons=n_seasons,
            seat_policy=result["arm_of_seat"],
            evaluator=(
                "draftAI synthetic policy/forecast shadow vs source-isolated historical market ADP"
                if test_policy or player_overrides or availability_by_player
                else "draftAI.DEFAULT_POLICY(v5) vs source-isolated historical market ADP"
            ),
            pool_override=pool,
        )
        seat = case.spec.test_seat
        started_points = report["outcome_metrics"]["started_points"]
        rank = 1 + sum(value > started_points[seat] for value in started_points)
        playoff_baseline = min(se.EvalConfig().playoff_slots, int(case.spec.row["teams"])) / int(
            case.spec.row["teams"]
        )
        report.update(
            {
                "opponent_policy": "human_adp",
                "opponent_top_k": case.top_k,
                "opponent_profile": list(opponent_profile or (case.top_k,)),
                "test_policy_patch": dict(test_policy or {}),
                "forecast_identity": forecast_identity,
                "market_format": case.market_format,
                "market_metadata_dropout": market_dropout,
                "qb_mode": case.spec.row["qb_mode"],
                "test_team_finish_rank": rank,
                "test_team_top_half": rank <= int(case.spec.row["teams"]) / 2,
                "playoff_delta_vs_baseline": _round(
                    report["test_team"]["playoff_proxy"] - playoff_baseline
                ),
                "market_provenance": provenance,
                "pick_trace": result["picks"],
                "recommendation_trace": result.get("recommendations", []),
            }
        )
        reports.append(report)

    summary = summarize(reports, seed=base_seed)
    return {
        "schema_version": 1,
        "authority": (
            "synthetic policy/forecast shadow; no fit or promotion evidence"
            if test_policy or player_overrides or availability_by_player
            else "shipped v5 production behavior; no fit or promotion evidence"
        ),
        "opponent_authority": "source-isolated historical aggregate human ADP",
        "synthetic_non_authoritative": True,
        "base_seed": base_seed,
        "repetitions_per_cell": repetitions,
        "seasons": list(seasons),
        "scenario_ids": list(scenario_ids),
        "top_k_sensitivity": list(top_ks),
        "opponent_profile": list(opponent_profile or ()),
        "test_policy_patch": dict(test_policy or {}),
        "forecast_identity": forecast_identity,
        "forecast_override_players": len(player_overrides or {}),
        "availability_forecast_players": len(availability_by_player or {}),
        "market_metadata_dropout": market_dropout,
        "recommendation_trace_enabled": include_recommendations,
        "elapsed_seconds": _round(time.perf_counter() - started),
        "summary": summary,
        "by_season": _group_summary(reports, "season", base_seed + 100),
        "by_qb_mode": _group_summary(reports, "qb_mode", base_seed + 200),
        "by_slot_band": _group_summary(reports, "slot_band", base_seed + 300),
        "by_top_k": _group_summary(reports, "opponent_top_k", base_seed + 400),
        "paired_top_k": paired_top_k_effects(reports, baseline=8, seed=base_seed + 500),
        "limitations": [
            "Historical aggregate ADP is a human-market proxy, not ESPN, Sleeper, "
            "or FantasyPros proprietary recommendation logic.",
            "BlitzBoard preseason projections use the repository's prior-season-production "
            "proxy, not archived vendor projections.",
            "Season evaluation factorizes availability and samples proxy playoffs; "
            "no roster is guaranteed to win.",
            "Market-only rookies without a weekly identity receive zero proxy projection "
            "and zero performance.",
        ],
        "drafts": reports,
    }


def bootstrap_ci(
    values: Sequence[float],
    *,
    seed: int,
    resamples: int = 2000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    if not values:
        raise ValueError("cannot bootstrap an empty sample")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")
    array = np.asarray(values, dtype=float)
    if len(array) == 1:
        value = float(array[0])
        return value, value
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(resamples, len(array)))
    means = array[indices].mean(axis=1)
    tail = (1 - confidence) / 2
    low, high = np.quantile(means, (tail, 1 - tail))
    return float(low), float(high)


def cluster_bootstrap_ci(
    values: Sequence[float],
    clusters: Sequence[str],
    *,
    seed: int,
    resamples: int = 2000,
) -> tuple[float, float]:
    if len(values) != len(clusters):
        raise ValueError("values and clusters must have equal length")
    grouped: dict[str, list[float]] = {}
    for value, cluster in zip(values, clusters, strict=True):
        grouped.setdefault(cluster, []).append(float(value))
    cluster_means = [float(np.mean(grouped[key])) for key in sorted(grouped)]
    return bootstrap_ci(cluster_means, seed=seed, resamples=resamples)


def degrade_market_ranks(
    ranks: dict[str, float], *, fraction: float, seed: int
) -> dict[str, float]:
    if not 0 <= fraction < 1:
        raise ValueError("market metadata dropout must be in [0, 1)")
    if fraction == 0:
        return dict(ranks)
    keys = sorted(ranks)
    dropped = set(random.Random(seed).sample(keys, round(len(keys) * fraction)))
    return {key: ranks[key] for key in keys if key not in dropped}


def competitive_assessment(evidence: dict[str, Sequence[float]]) -> dict[str, str]:
    starter = evidence["starter_strength_ci95"]
    h2h = evidence["h2h_ci95"]
    playoff = evidence["playoff_delta_ci95"]
    if starter[0] >= 1.0 and h2h[0] >= 0.5 and playoff[0] >= 0:
        verdict = "COMPETITIVE"
        reason = "all predeclared intervals clear their league-average baselines"
    elif starter[1] < 1.0 and h2h[1] < 0.5 and playoff[1] < 0:
        verdict = "UNDERPERFORMS"
        reason = "all predeclared intervals remain below their league-average baselines"
    else:
        verdict = "INCONCLUSIVE"
        reason = "one or more intervals overlap their league-average baseline"
    return {"verdict": verdict, "reason": reason}


def _without_timing(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_timing(item)
            for key, item in value.items()
            if key not in {"elapsed_seconds", "evidence_sha256"}
        }
    if isinstance(value, list):
        return [_without_timing(item) for item in value]
    return value


def evidence_hash(report: dict[str, Any]) -> str:
    encoded = json.dumps(
        _without_timing(report), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:  # pragma: no cover - exercised by campaign command
    logging.getLogger("blitz_engine.survival.availability").setLevel(logging.ERROR)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-dir", type=Path, required=True)
    parser.add_argument("--weekly-dir", type=Path, required=True)
    parser.add_argument("--base-seed", type=int, default=20260828)
    parser.add_argument("--repetitions", type=int, default=4)
    parser.add_argument("--top-k", type=int, action="append", default=None)
    parser.add_argument("--seasons-per-draft", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=72)
    parser.add_argument("--market-dropout", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_campaign(
        market_dir=args.market_dir,
        weekly_dir=args.weekly_dir,
        base_seed=args.base_seed,
        repetitions=args.repetitions,
        top_ks=tuple(args.top_k or (1, 4, 8, 12)),
        n_seasons=args.seasons_per_draft,
        batch_size=args.batch_size,
        market_dropout=args.market_dropout,
    )
    report["evidence_sha256"] = evidence_hash(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    compact = {
        key: report[key]
        for key in (
            "schema_version",
            "authority",
            "opponent_authority",
            "synthetic_non_authoritative",
            "base_seed",
            "repetitions_per_cell",
            "top_k_sensitivity",
            "market_metadata_dropout",
            "elapsed_seconds",
            "evidence_sha256",
            "summary",
            "by_season",
            "by_qb_mode",
            "by_slot_band",
            "by_top_k",
            "paired_top_k",
            "limitations",
        )
    }
    summary_path = args.output.with_name(f"{args.output.stem}-summary.json")
    summary_path.write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                **report["summary"],
                "evidence_sha256": report["evidence_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
