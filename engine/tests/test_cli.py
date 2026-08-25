"""CLI smoke tests — every verb runs end to end against a tiny temporary store.

This is the proof the E0 print-stubs are gone: each verb reaches its real module, exits 0,
prints exactly one machine-readable JSON summary, and no output line says "stub". The store
is a `tmp_path` fixture — never `~/.blitz_engine`.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

import pandas as pd
import pytest

from blitz_engine.cli import main

_POSITIONS = ["QB"] * 3 + ["RB"] * 5 + ["WR"] * 6 + ["TE"] * 2
_WEEKS = (1, 2, 3)


def _player_weeks() -> pd.DataFrame:
    """A tiny but complete tidy player-week frame (16 players × 3 weeks, 4 positions)."""
    rows = []
    for i, pos in enumerate(_POSITIONS):
        for week in _WEEKS:
            rows.append({
                "player_id": f"p{i:02d}",
                "position": pos,
                "team": f"T{i % 4}",
                "season": 2024,
                "week": week,
                "team_plays": 60.0,
                "opportunities": 4.0 + (len(_POSITIONS) - i) + week,
                "yards": 30.0 + 4.0 * (len(_POSITIONS) - i) + week,
                "tds": float((i + week) % 3 == 0),
            })
    return pd.DataFrame(rows)


def _run(*argv: str) -> tuple[int, list[str]]:
    """Run the CLI, returning (exit code, output lines)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(list(argv))
    return code, [ln for ln in buf.getvalue().splitlines() if ln.strip()]


def _summary(lines: list[str]) -> dict:
    """The single JSON summary line — and the no-stub assertion every verb must pass."""
    assert lines, "a verb must print a summary line"
    assert not any("stub" in ln.lower() for ln in lines), lines
    return json.loads(lines[-1])


@pytest.fixture(scope="module")
def fitted(tmp_path_factory) -> tuple[str, dict]:
    """Run `fit` once into a module-scoped tmp store; later verbs read its tables."""
    root = tmp_path_factory.mktemp("engine_cli")
    (root).mkdir(exist_ok=True)
    _player_weeks().to_parquet(root / "player_weeks.parquet")
    code, lines = _run(
        "fit", "--data-root", str(root), "--seed", "7",
        "--warmup", "20", "--samples", "20", "--chains", "1", "--no-gate",
    )
    assert code == 0, lines
    return str(root), _summary(lines)


def test_fit_wires_the_projection_model(fitted) -> None:
    from pathlib import Path

    root, out = fitted
    assert out["verb"] == "fit" and out["ok"] is True
    assert out["players"] == len(_POSITIONS)
    assert out["obs"] == len(_POSITIONS) * len(_WEEKS)
    assert out["seed"] == 7
    assert Path(root, "projection_quantiles.parquet").exists()
    assert Path(root, "projection_draws.parquet").exists()
    assert Path(root, "registry.jsonl").exists()


def test_sim_wires_the_monte_carlo_core(fitted) -> None:
    root, _ = fitted
    code, lines = _run("sim", "--data-root", root, "--seed", "7", "--runs", "2000",
                       "--league", "4", "--weeks", "3", "--league-seasons", "200")
    out = _summary(lines)
    assert code == 0, lines
    assert out["players"] == len(_POSITIONS)
    assert out["n_runs"] == 2000 and out["within_budget"] is True
    assert out["league"]["rosters"] == 4 and out["league"]["champion"].startswith("t")


def test_draft_wires_the_value_engine(fitted) -> None:
    from pathlib import Path

    root, _ = fitted
    code, lines = _run("draft", "--data-root", root, "--seed", "7",
                       "--mcts-iter", "50", "--opponents", "3")
    out = _summary(lines)
    assert code == 0, lines
    assert out["candidates"] == len(_POSITIONS)
    assert out["best"] and out["mcts_best"] and out["starters"] > 0
    tree = json.loads(Path(root, "strategy_tree.json").read_text())
    assert tree["action_visits"] and abs(sum(tree["policy_target"].values()) - 1.0) < 1e-9


def test_publish_writes_full_and_compact_bundles(fitted, tmp_path) -> None:
    root, _ = fitted
    out_dir = tmp_path / "snap"
    code, lines = _run("publish", "--data-root", root, "--seed", "7", "--out", str(out_dir))
    out = _summary(lines)
    assert code == 0, lines
    assert out["schema_version"] >= 1
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "values.parquet").exists()
    # compact export carries ONLY the public tier (quantiles + corr), never raw draws
    compact = json.loads((out_dir / "compact" / "manifest.json").read_text())
    assert compact["compact"] is True
    assert not (out_dir / "compact" / "mc_probs.parquet").exists()


def test_publish_defaults_to_a_versioned_dir_under_data_root(fitted) -> None:
    """No --out → <data_root>/snapshots/<version> (the --data-root override must stay a Path)."""
    from pathlib import Path

    root, _ = fitted
    code, lines = _run("publish", "--data-root", root, "--seed", "7")
    out = _summary(lines)
    assert code == 0, lines
    assert Path(out["full"]) == Path(root, "snapshots", out["version"])
    assert Path(out["compact"], "manifest.json").exists()


def test_missing_inputs_exit_nonzero(tmp_path) -> None:
    code, lines = _run("sim", "--data-root", str(tmp_path / "empty"))
    assert code == 1
    assert json.loads(lines[-1])["ok"] is False


def test_player_weeks_falls_back_to_pbp(tmp_path) -> None:
    """No curated `player_weeks` table → the tidy frame is derived from raw pbp."""
    from blitz_engine.cli import _player_weeks as load
    from blitz_engine.store import ParquetStore

    pbp = pd.DataFrame({
        "game_id": ["2024_01"] * 4,
        "play_id": [1, 2, 3, 4],
        "season": [2024] * 4,
        "week": [1] * 4,
        "posteam": ["KC"] * 4,
        "passer_player_id": ["qb1", "qb1", None, None],
        "rusher_player_id": [None, None, "rb1", "rb1"],
        "receiver_player_id": ["wr1", "wr1", None, None],
        "passing_yards": [10.0, 20.0, 0.0, 0.0],
        "receiving_yards": [10.0, 20.0, 0.0, 0.0],
        "rushing_yards": [0.0, 0.0, 5.0, 7.0],
        "pass_touchdown": [0.0, 1.0, 0.0, 0.0],
        "rush_touchdown": [0.0, 0.0, 0.0, 1.0],
    })
    with ParquetStore.open(tmp_path / "store") as store:
        store.write_parquet("pbp", pbp)
        pw = load(store, "player_weeks", None, None)
    assert set(pw["player_id"]) == {"qb1", "rb1", "wr1"}
    assert set(pw["position"]) == {"QB", "RB", "WR"}
    assert pw.loc[pw["player_id"] == "rb1", "opportunities"].iloc[0] == 2
    assert pw.loc[pw["player_id"] == "qb1", "yards"].iloc[0] == 30
    assert (pw["team_plays"] == 4).all()
