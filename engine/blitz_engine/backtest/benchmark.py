"""Benchmark board — accuracy over time, keyed to the registry version tuple.

An append-only JSONL ledger (same shape as `registry`): each entry pins a model's
walk-forward MAE against actuals and, when supplied, a FantasyPros consensus predictor and a
prior version, all under one registry `version`. This is how a model unit tracks whether a
new version actually moved the needle versus the external field and its own past.

    board = BenchmarkBoard(store.root)
    entry = board.record_run(version=rec.version, model=engine, frame=hist,
                             fantasypros=fantasypros_predictor(fp), scoring=scoring)
    entry.beats_fantasypros   # did we clear the market?
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from blitz_engine.backtest.harness import walk_forward

if TYPE_CHECKING:
    from blitz_engine.backtest.harness import Predictor

__all__ = ["BenchmarkBoard", "BenchmarkEntry"]

_LEDGER = "benchmark_board.jsonl"


@dataclass(frozen=True)
class BenchmarkEntry:
    """One recorded benchmark: a version's MAE vs actuals, FantasyPros, and a prior version."""

    version: str
    model_mae: float
    n_obs: int
    fantasypros_mae: float | None = None
    prior_version: str | None = None
    prior_mae: float | None = None
    model_spearman: float | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def beats_fantasypros(self) -> bool | None:
        """True/False if a FantasyPros MAE was recorded (lower is better); None otherwise."""
        if self.fantasypros_mae is None:
            return None
        return self.model_mae <= self.fantasypros_mae

    @property
    def improved_on_prior(self) -> bool | None:
        if self.prior_mae is None:
            return None
        return self.model_mae <= self.prior_mae


class BenchmarkBoard:
    """Append-only benchmark ledger under a store root — `ponytail:` JSONL, no DB."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / _LEDGER

    def record(self, entry: BenchmarkEntry) -> BenchmarkEntry:
        with self.path.open("a") as fh:
            fh.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def entries(self) -> list[BenchmarkEntry]:
        """Every recorded benchmark, oldest first."""
        if not self.path.exists():
            return []
        return [
            BenchmarkEntry(**json.loads(line))
            for line in self.path.read_text().splitlines()
            if line.strip()
        ]

    def latest(self, version: str) -> BenchmarkEntry | None:
        """Most recent entry recorded under `version`, or None."""
        found = [e for e in self.entries() if e.version == version]
        return found[-1] if found else None

    def record_run(
        self,
        *,
        version: str,
        model: Predictor,
        frame: pd.DataFrame,
        fantasypros: Predictor | None = None,
        prior_model: Predictor | None = None,
        prior_version: str | None = None,
        scoring: dict | None = None,
        time_col: str = "season",
        min_train_periods: int = 1,
    ) -> BenchmarkEntry:
        """Walk-forward `model` (and optional FantasyPros / prior version) over `frame`,
        record the entry under `version`, and return it."""
        kw = dict(scoring=scoring, time_col=time_col, min_train_periods=min_train_periods)
        model_rep = walk_forward(frame, model, **kw)  # type: ignore[arg-type]
        fp_mae = (
            walk_forward(frame, fantasypros, **kw).mae  # type: ignore[arg-type]
            if fantasypros is not None
            else None
        )
        prior_mae = (
            walk_forward(frame, prior_model, **kw).mae  # type: ignore[arg-type]
            if prior_model is not None
            else None
        )
        return self.record(
            BenchmarkEntry(
                version=version,
                model_mae=model_rep.mae,
                n_obs=model_rep.n_obs,
                fantasypros_mae=fp_mae,
                prior_version=prior_version,
                prior_mae=prior_mae,
                model_spearman=model_rep.spearman,
            )
        )
