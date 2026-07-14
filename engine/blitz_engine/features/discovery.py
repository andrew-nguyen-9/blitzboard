"""Automated feature discovery — base columns + bounded nonlinear interactions.

The feature layer (E6) sits *over* the E1 projection core: it turns a tidy player-week
frame into a screened, importance-ranked `FeatureSet` that downstream models (E6-graph
embeddings, E6-ensemble) read, and that can be fed back into the core through the E1
`FactorHook` seam.

`ponytail:` discovery is deliberately NOT an AutoML search. It is (a) the numeric base
columns and (b) their degree-2 pairwise products — the "nonlinear interactions" the brief
asks for — computed on standardized inputs so products stay on a comparable scale. That is
the whole generator; screening (`screening.py`) does the selecting.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

__all__ = ["FeatureSet", "discover_features", "INTERACTION_SEP"]

#: How an interaction feature name joins its two parents (``"a x b"``).
INTERACTION_SEP = " x "

#: id/label columns carried through untouched (never treated as features).
_DEFAULT_ID_COLS = ("player_id", "position", "team", "week", "season")


@dataclass(frozen=True)
class FeatureSet:
    """A discovered feature matrix plus the id columns that index its rows.

    `matrix` is ``(N, F)`` float; `names` labels its columns; `index` carries the id
    columns (player/week/season…) so screening, per-season importance and the factor
    bridge can join back to players. Immutable — screening returns a new selected view.
    """

    names: list[str]
    matrix: np.ndarray  # (N, F) float
    index: pd.DataFrame  # (N, k) carried id columns

    @property
    def n_features(self) -> int:
        return len(self.names)

    @property
    def n_rows(self) -> int:
        return int(self.matrix.shape[0])

    def column(self, name: str) -> np.ndarray:
        """The (N,) values of one named feature."""
        return self.matrix[:, self.names.index(name)]

    def select(self, names: list[str]) -> FeatureSet:
        """A new `FeatureSet` keeping only `names` (order preserved)."""
        cols = [self.names.index(n) for n in names]
        return FeatureSet(names=list(names), matrix=self.matrix[:, cols], index=self.index)

    def frame(self) -> pd.DataFrame:
        """id columns + features as one tidy frame (for inspection / joins)."""
        feats = pd.DataFrame(self.matrix, columns=self.names)
        return pd.concat([self.index.reset_index(drop=True), feats], axis=1)


def _standardize(mat: np.ndarray) -> np.ndarray:
    """Column z-score; zero-variance columns collapse to 0 (never divide by 0)."""
    mu = mat.mean(axis=0)
    sd = mat.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    return (mat - mu) / sd


def discover_features(
    frame: pd.DataFrame,
    base_cols: list[str],
    *,
    id_cols: tuple[str, ...] = _DEFAULT_ID_COLS,
    interactions: bool = True,
    standardize: bool = True,
) -> FeatureSet:
    """Build a `FeatureSet` from `base_cols` plus their pairwise interaction products.

    Base columns are pulled numeric and (by default) z-scored; with `interactions`, every
    unordered pair ``a, b`` yields a product feature ``"a x b"`` on the standardized inputs
    — a compact, deterministic nonlinear expansion (no framework, no search). Non-numeric or
    all-NaN base columns are skipped. `id_cols` present in `frame` are carried through as the
    row index.
    """
    present_ids = [c for c in id_cols if c in frame.columns]
    index = frame[present_ids].reset_index(drop=True) if present_ids else pd.DataFrame(
        index=range(len(frame))
    )

    usable, arrays = [], []
    for c in base_cols:
        if c not in frame.columns:
            continue
        col = pd.to_numeric(frame[c], errors="coerce").to_numpy(dtype=float)
        if np.isnan(col).all():
            continue
        arrays.append(np.nan_to_num(col, nan=0.0))
        usable.append(c)
    if not usable:
        raise ValueError("no usable numeric base_cols found in frame")

    base = np.column_stack(arrays)
    feats = _standardize(base) if standardize else base
    names = list(usable)
    cols = [feats[:, i] for i in range(feats.shape[1])]

    if interactions:
        for i, j in combinations(range(len(usable)), 2):
            names.append(f"{usable[i]}{INTERACTION_SEP}{usable[j]}")
            cols.append(feats[:, i] * feats[:, j])

    return FeatureSet(names=names, matrix=np.column_stack(cols), index=index)
