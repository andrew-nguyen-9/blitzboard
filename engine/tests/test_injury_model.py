"""E3 — the fitted injury model: hazard · duration · return curve · re-injury.

Everything here runs on a *synthetic* exposure history so the suite never needs the
`~/.blitz_engine` store: the panel builder consumes the same column shape `build_injury_panel`
assembles out of `weekly_rosters` + `injuries` + `snap_counts`, so a generated frame exercises
the real code path end to end (cohort filter → spells → fits → calibration gate → the JSON e10
reads).

The generator deliberately plants the two confounders the refit exists to separate: **bye weeks**
and **benched players** — both are zero-snap weeks with no injury designation, and both used to
read as injuries when the event came from snap presence.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from blitz_engine.survival.hazard import (
    FANTASY_POSITIONS,
    GAMES_PER_SEASON,
    MIN_SPELLS,
    REINJURY_WEEKS,
    RETURN_WEEKS,
    DurationModel,
    ReinjuryRisk,
    build_injury_panel_from_frame,
    extract_spells,
    fit_duration_model,
    fit_injury_model,
    fit_reinjury_risk,
    fit_return_curve,
    write_injury_rates,
)

#: Per-position weekly probability a healthy player picks up a new injury.
_ONSET = {"QB": 0.04, "RB": 0.11, "WR": 0.07, "TE": 0.07}
#: Players generated per position — TE is deliberately sparse (pooled-prior degrade path).
_ROSTER = {"QB": 26, "RB": 26, "WR": 26, "TE": 2}
_SEASONS = (2019, 2020, 2021, 2022, 2023, 2024)
_WEEKS = 17
#: Players who sit healthy (zero snaps, no designation) for `_BENCH_WEEKS` of `_BENCH_SEASON` —
#: a healthy scratch is the other confounder a snap-presence event cannot tell from an injury.
_BENCHED = ("WR25", "QB25")
_BENCH_SEASON = 2021
_BENCH_WEEKS = range(2, 8)


def make_exposure(seed: int = 11) -> pd.DataFrame:
    """A roster-shaped exposure history with programmed injury designations.

    One row per rostered player-week (the exposure denominator), carrying the clinical event
    (`report_out`) independently of the snap load — including a bye week and a benched player,
    which are zero-snap but healthy.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for position, n_players in _ROSTER.items():
        for p in range(n_players):
            player = f"{position}{p:02d}"
            born = pd.Timestamp("1996-06-01") - pd.Timedelta(days=365 * (p % 9))
            for season in _SEASONS:
                out_left, bye = 0, int(rng.integers(4, 12))
                for week in range(1, _WEEKS + 1):
                    if out_left == 0 and week > 1 and rng.random() < _ONSET[position]:
                        out_left = int(1 + rng.geometric(0.45))
                    injured = out_left > 0
                    out_left = max(out_left - 1, 0)
                    benched = (
                        player in _BENCHED
                        and season == _BENCH_SEASON
                        and week in _BENCH_WEEKS
                    )
                    playing = not injured and not benched and week != bye
                    rows.append(
                        {
                            "season": season,
                            "week": week,
                            "gsis_id": player,
                            "position": position,
                            "report_out": float(injured),
                            "reserve_injured": 0.0,
                            "off_snaps": float(rng.integers(45, 70)) if playing else 0.0,
                            "st_snaps": 0.0,
                            "birth_date": born,
                        }
                    )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return build_injury_panel_from_frame(make_exposure())


@pytest.fixture(scope="module")
def model(panel: pd.DataFrame) -> object:
    return fit_injury_model(panel=panel, seed=7, holdout=1)


# -- panel ---------------------------------------------------------------------------------
def test_panel_marks_the_clinical_event(panel: pd.DataFrame) -> None:
    assert not panel.empty
    assert set(panel["out"].unique()) <= {0.0, 1.0}
    assert 0.0 < panel["out"].mean() < 0.5  # a real, non-degenerate event rate
    # `onset` is a strict subset of `out` and never fires while already out
    assert (panel.loc[panel["onset"] == 1.0, "out"] == 1.0).all()
    assert (panel.loc[panel["onset"] == 1.0, "prev_out"] == 0.0).all()
    assert panel["weeks_since_return"].max() <= REINJURY_WEEKS


def test_event_is_clinical_not_participation(panel: pd.DataFrame) -> None:
    """The refit's whole point: a zero-snap week is only an injury if the club said so.

    Byes and benchings are zero-snap and healthy. When the event came from snap presence they
    were indistinguishable from injuries and inflated every rate; now they must score `out=0`.
    """
    healthy_zero_snap = panel[(panel["snaps"] == 0.0) & (panel["out"] == 0.0)]
    assert len(healthy_zero_snap) > 100  # the planted byes survive as healthy weeks
    benched = panel[
        panel["player_id"].isin(_BENCHED)
        & (panel["season"] == _BENCH_SEASON)
        & panel["week"].isin(list(_BENCH_WEEKS))
    ]
    assert len(benched) == len(_BENCHED) * len(_BENCH_WEEKS)
    assert (benched["snaps"] == 0.0).all()  # a healthy scratch takes no snaps …
    assert (benched["out"] == 0.0).all()    # … and is still not injured
    # and the event rate tracks what was programmed, not the zero-snap rate
    assert panel["out"].mean() < (panel["snaps"] == 0.0).mean()


def test_panel_carries_a_real_age_covariate(panel: pd.DataFrame) -> None:
    """`weekly_rosters.birth_date` makes age a real covariate, not the old seasons-played proxy."""
    assert panel["age"].notna().all()
    assert panel["age"].between(18.0, 50.0).all()
    assert panel["age"].nunique() > 5
    # and it ages with the calendar
    one = panel[panel["player_id"] == "RB00"]
    assert one.groupby("season")["age"].mean().is_monotonic_increasing


def test_person_period_key_is_the_player_season(panel: pd.DataFrame) -> None:
    """Recurrence must reset each September — grouping by career leaked IR across the offseason."""
    assert panel["player_season"].nunique() == len(
        panel[["player_id", "season"]].drop_duplicates()
    )
    assert (panel["player_season"].str.split(":").str[0] == panel["player_id"]).all()


def test_weeks_since_return_can_coincide_with_an_event(panel: pd.DataFrame) -> None:
    """Regression: `weeks_since_return` used to imply `out == 0`, zeroing the re-injury fit."""
    assert ((panel["weeks_since_return"] > 0.0) & (panel["out"] == 1.0)).any()


def test_panel_is_empty_and_typed_without_data() -> None:
    empty = build_injury_panel_from_frame(pd.DataFrame())
    assert empty.empty
    assert "out" in empty.columns


def test_cohort_filter_drops_bit_part_players() -> None:
    frame = make_exposure()
    scrub = frame[frame["gsis_id"] == "WR00"].copy()
    scrub["gsis_id"] = "WR99"
    scrub["off_snaps"] = 3.0  # never a real role, in any season of his career
    built = build_injury_panel_from_frame(pd.concat([frame, scrub], ignore_index=True))
    assert "WR99" not in set(built["player_id"])
    assert "WR00" in set(built["player_id"])

# -- hazard ---------------------------------------------------------------------------------
def test_hazards_are_probabilities(model: object, panel: pd.DataFrame) -> None:
    h = model.hazard.predict_hazard(panel)  # type: ignore[attr-defined]
    o = model.onset_hazard.predict_hazard(panel)  # type: ignore[attr-defined]
    assert np.isfinite(h).all() and np.isfinite(o).all()
    assert ((h >= 0.0) & (h <= 1.0)).all()
    assert ((o >= 0.0) & (o <= 1.0)).all()
    assert np.allclose(model.hazard.predict_available(panel), 1.0 - h)  # type: ignore[attr-defined]


def test_predict_replays_the_fit_column_mapping(model: object, panel: pd.DataFrame) -> None:
    """Predicting must use the covariates the fit used, not `build_person_periods` defaults."""
    hz = model.hazard  # type: ignore[attr-defined]
    assert hz.columns_["workload_col"] == "workload"
    zeroed = panel.copy()
    zeroed["workload"] = 0.0
    assert not np.allclose(hz.predict_hazard(panel), hz.predict_hazard(zeroed))


# -- duration ---------------------------------------------------------------------------------
def test_duration_distribution_has_positive_support_and_finite_mean(model: object) -> None:
    duration: DurationModel = model.duration  # type: ignore[attr-defined]
    for position in ("QB", "RB", "WR", "TE"):
        assert duration.mean(position) >= 1.0
        assert np.isfinite(duration.mean(position))
        # bounded by a season: an unbounded NB fitted through 38 % right-censoring reports a
        # latent mean of 10-26 games, which cannot be "games missed" in a 17-game year
        assert duration.mean(position) <= GAMES_PER_SEASON
        assert np.isfinite(duration.var(position)) and duration.var(position) > 0.0
        pmf = duration.pmf(np.arange(0, 30), position)
        assert pmf[0] == 0.0  # an injury always costs at least one game
        assert (pmf >= 0.0).all()
        assert pmf.sum() > 0.9  # essentially all mass inside 30 games
        draws = duration.sample(position, 500, np.random.default_rng(3))
        assert (draws >= 1).all()
        assert (draws <= duration.cap).all()


def test_spells_are_positive_and_flag_censoring(panel: pd.DataFrame) -> None:
    spells = extract_spells(panel)
    assert not spells.empty
    assert (spells["duration"] >= 1.0).all()
    assert set(spells["censored"].unique()) <= {0.0, 1.0}


def test_sparse_position_degrades_to_the_pooled_prior(model: object) -> None:
    """TE has only two players in the fixture ⇒ too few spells to fit on its own."""
    duration: DurationModel = model.duration  # type: ignore[attr-defined]
    assert duration.counts.get("TE", 0) < MIN_SPELLS
    assert "TE" in duration.pooled_positions()
    assert duration._params("TE") == duration.pooled
    assert duration.counts["RB"] >= MIN_SPELLS  # a dense position IS fitted on its own
    assert duration._params("RB") != duration.pooled


def test_duration_model_degrades_without_spells() -> None:
    empty = fit_duration_model(extract_spells(build_injury_panel_from_frame(pd.DataFrame())))
    # neutral prior, still a valid distribution (a hair under 2.0: the tail past `cap` is folded
    # back onto `cap` rather than extrapolated)
    assert empty.mean("RB") == pytest.approx(2.0, rel=1e-3)
    assert empty.mean("RB") <= 2.0


# -- return curve -------------------------------------------------------------------------------
def test_return_curve_is_bounded_and_recovers(panel: pd.DataFrame) -> None:
    curve = fit_return_curve(extract_spells(panel))
    for position in ("QB", "RB", "WR", "TE"):
        vals = np.asarray(curve.curve(position))
        assert len(vals) == RETURN_WEEKS
        assert ((vals > 0.0) & (vals <= 1.0)).all()
        assert (np.diff(vals) >= -1e-12).all()  # recovery never goes backwards
    assert curve.multiplier("RB", RETURN_WEEKS + 3) == pytest.approx(1.0)
    assert curve.multiplier("RB", 0) == pytest.approx(1.0)  # not recently back ⇒ no penalty


# -- re-injury ----------------------------------------------------------------------------------
def _reinjury_panel(elevated: float, base: float = 0.05) -> pd.DataFrame:
    """A panel whose onset rate decays from `elevated` back to `base` after a return."""
    rng = np.random.default_rng(5)
    rows = []
    for k in range(0, REINJURY_WEEKS + 1):
        p = base if k == 0 else base + (elevated - base) * np.exp(-(k - 1) / 2.0)
        n = 4000 if k == 0 else 400
        rows.append(
            pd.DataFrame(
                {
                    "player_id": [f"p{k}"] * n,
                    "position": "RB",
                    "season": 2020,
                    "week": 1,
                    "snaps": 50.0,
                    "out": 0.0,
                    "prev_out": 0.0,
                    "onset": (rng.random(n) < p).astype(float),
                    "workload": 50.0,
                    "weeks_since_return": float(k),
                    "experience": 1.0,
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_reinjury_hazard_exceeds_baseline_and_decays() -> None:
    risk = fit_reinjury_risk(_reinjury_panel(elevated=0.25))
    assert risk.elevation > 0.0
    ratios = risk.hazard_ratio(np.arange(1, REINJURY_WEEKS + 1))
    assert (ratios >= 1.0).all()                      # never below baseline
    assert (np.diff(ratios) <= 1e-12).all()           # and it decays
    assert ratios[0] > ratios[-1]
    assert risk.hazard_ratio(0) == pytest.approx(1.0)  # no recent return ⇒ baseline


def test_reinjury_is_fitted_from_a_real_panel(panel: pd.DataFrame) -> None:
    """End-to-end: the panel's own post-return weeks must be able to produce an elevation."""
    risk = fit_reinjury_risk(panel)
    assert risk.baseline_hazard > 0.0
    assert risk.elevation >= 0.0
    assert (risk.hazard_ratio(np.arange(1, REINJURY_WEEKS + 1)) >= 1.0).all()


def test_reinjury_degrades_to_neutral_without_signal() -> None:
    flat = fit_reinjury_risk(_reinjury_panel(elevated=0.05))
    assert flat.hazard_ratio(np.arange(1, 5)).max() < 1.5
    assert (ReinjuryRisk().hazard_ratio(np.arange(0, 5)) == 1.0).all()


# -- the assembled model + reproducibility ------------------------------------------------------
def test_injury_rate_map_covers_every_fantasy_position(model: object) -> None:
    rates = model.injury_rate_map()  # type: ignore[attr-defined]
    assert set(rates) == set(FANTASY_POSITIONS)
    assert all(0.0 <= v <= 1.0 for v in rates.values())
    assert rates["DST"] == 0.0  # a team defence is never injured
    assert any(v > 0.0 for k, v in rates.items() if k != "DST")


def test_refit_with_the_same_seed_is_bit_identical(panel: pd.DataFrame) -> None:
    a = fit_injury_model(panel=panel, seed=7, holdout=1)
    b = fit_injury_model(panel=panel, seed=7, holdout=1)
    assert json.dumps(a.to_dict(), sort_keys=True) == json.dumps(b.to_dict(), sort_keys=True)
    assert np.array_equal(a.hazard.beta, b.hazard.beta)
    assert np.array_equal(a.onset_hazard.beta, b.onset_hazard.beta)


def test_calibration_gate_runs_and_is_recorded(model: object) -> None:
    cal = model.calibration  # type: ignore[attr-defined]
    assert "passed" in cal and "summary" in cal
    assert cal["overdispersion"] >= 1.0
    assert model.calibrated is bool(cal["passed"])  # type: ignore[attr-defined]


def test_write_injury_rates_emits_what_e10_reads(model: object, tmp_path: object) -> None:
    dest = write_injury_rates(model, tmp_path / "injury_rates.json")  # type: ignore[operator]
    payload = json.loads(dest.read_text())
    assert payload["seed"] == 7
    assert set(payload["injuryRate"]) == set(FANTASY_POSITIONS)
    assert payload["entry_point"].endswith("fit_injury_model")
    assert payload["calibration"]["unit"]
    # e10 bakes injuryRate into DEFAULT_POLICY — the payload must say what it measures
    assert "clinical injury" in payload["event"]
    assert "NOT snap-presence" in payload["event"]
    assert len(payload["return_curve"]["RB"]) == RETURN_WEEKS


def test_fit_refuses_an_empty_panel() -> None:
    with pytest.raises(ValueError, match="empty"):
        fit_injury_model(panel=build_injury_panel_from_frame(pd.DataFrame()))
