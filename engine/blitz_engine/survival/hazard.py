"""Discrete-time logistic hazard — the survival core behind weekly P(available).

A discrete-time hazard is exactly logistic regression on **person-period** rows: one row
per player-week with a binary `out` event (player unavailable that week). We model

    logit h(player, week) = β·x(age, workload, injury-history, RECURRENCE, position)

and read weekly availability straight off it: ``P(available) = 1 − h``. `ponytail:` no
custom survival solver and no NUTS — a discrete-time hazard is standard logistic regression,
so the whole fit is one `scipy.optimize` call (lifelines/sklearn/statsmodels are absent from
the venv; scipy is present). Deterministic + fast, so the DoD tests never spin NUTS.

The **recurrence** signal is a genuine *time-varying* covariate (`recent_injury`): a decayed
indicator of whether the player was out in the preceding weeks, recomputed every person-
period. Recent injury raises this week's hazard — that is the recurrence mechanism.

Degrade-safe: no event column / a degenerate (all-in or all-out) history / too few rows ⇒
the model stays *unfitted* and every hazard prediction returns the neutral base rate, so the
availability layer can never worsen the base projection (mirrors E1's seam guarantee).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = [
    "DiscreteTimeHazard",
    "build_person_periods",
]

#: Covariates fed to the logistic hazard (position is added as drop-first one-hot columns).
_NUMERIC = ("age", "workload", "injury_history", "recent_injury")
#: The two columns standardised before the fit; the [0, 1]-ish rates are left interpretable.
_STANDARDIZE = ("age", "workload")


def build_person_periods(
    history: pd.DataFrame,
    *,
    out_col: str = "out",
    workload_col: str = "opportunities",
    age_col: str = "age",
    position_col: str = "position",
    player_col: str = "player_id",
    time_cols: tuple[str, ...] = ("season", "week"),
    window: int = 4,
    decay: float = 0.5,
) -> pd.DataFrame:
    """Assemble ordered person-period rows with the derived recurrence covariates.

    For each player (ordered by whatever of `time_cols` exist), computes two history-derived
    covariates from the leading `out` sequence, both using only the PAST (no leakage):

    * ``injury_history`` — the player's cumulative prior out-rate (chronic fragility).
    * ``recent_injury`` — a decayed count of outs in the previous `window` weeks (recurrence,
      time-varying): ``Σ decay**k · out(t−1−k)`` for k in 0..window−1.

    Returns a frame with `_NUMERIC` + the resolved `out`/`position` columns.
    """
    df = history.copy()
    df[player_col] = df[player_col].astype(str)
    order = [c for c in time_cols if c in df.columns]
    if order:
        df = df.sort_values([player_col, *order], kind="stable")
    df = df.reset_index(drop=True)

    out = (
        pd.to_numeric(df[out_col], errors="coerce").fillna(0.0).clip(0, 1)
        if out_col in df.columns
        else pd.Series(np.zeros(len(df)), index=df.index)
    )
    weights = decay ** np.arange(window)  # k = 0 (most recent) → 1.0

    hist = np.zeros(len(df))
    recent = np.zeros(len(df))
    for rows in df.groupby(player_col, sort=False).indices.values():
        seq = out.iloc[rows].to_numpy(dtype=float)
        prior_sum = np.concatenate([[0.0], np.cumsum(seq)[:-1]])
        prior_n = np.arange(len(seq), dtype=float)
        hist[rows] = np.divide(
            prior_sum, prior_n, out=np.zeros_like(prior_sum), where=prior_n > 0
        )
        rec = np.zeros(len(seq))
        for i in range(len(seq)):
            past = seq[max(0, i - window):i][::-1]  # most-recent-first
            rec[i] = float(np.dot(past, weights[: len(past)]))
        recent[rows] = rec

    df["out"] = out.to_numpy()
    df["injury_history"] = hist
    df["recent_injury"] = recent
    df["workload"] = pd.to_numeric(df.get(workload_col, 0.0), errors="coerce").fillna(0.0)
    age = pd.to_numeric(df.get(age_col, np.nan), errors="coerce")
    df["age"] = age.fillna(age.median() if age.notna().any() else 0.0)
    df["position"] = df[position_col].astype(str) if position_col in df.columns else "NA"
    return df


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def _fit_logistic(X: np.ndarray, y: np.ndarray, *, l2: float = 1.0) -> np.ndarray:
    """L2-regularised logistic MLE via scipy L-BFGS (intercept, col 0, unpenalised)."""
    from scipy.optimize import minimize

    n_feat = X.shape[1]

    def nll(beta: np.ndarray) -> float:
        z = X @ beta
        ll = float(np.sum(y * z - np.logaddexp(0.0, z)))
        return -ll + 0.5 * l2 * float(np.sum(beta[1:] ** 2))

    def grad(beta: np.ndarray) -> np.ndarray:
        g = X.T @ (_sigmoid(X @ beta) - y)
        reg = l2 * beta
        reg[0] = 0.0
        return g + reg

    res = minimize(nll, np.zeros(n_feat), jac=grad, method="L-BFGS-B")
    return np.asarray(res.x, dtype=float)


@dataclass
class DiscreteTimeHazard:
    """Fitted discrete-time logistic hazard → per-player-week P(available).

    `fit(history)` builds person-periods and fits the logistic; `predict_hazard(frame)` /
    `predict_available(frame)` score current player-weeks. Unfitted (degrade) ⇒ hazard
    everywhere equals `neutral_hazard`, so availability is neutral and the projection is
    untouched. All state is plain arrays/dicts (picklable, deterministic).
    """

    l2: float = 1.0
    window: int = 4
    decay: float = 0.5
    neutral_hazard: float = 0.0
    fitted: bool = False
    feature_names: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)
    beta: np.ndarray = field(default_factory=lambda: np.zeros(0))
    mean_: dict[str, float] = field(default_factory=dict)
    std_: dict[str, float] = field(default_factory=dict)

    # -- design matrix (shared by fit + predict so columns always align) --------
    def _design(self, pp: pd.DataFrame) -> np.ndarray:
        n = len(pp)
        cols = [np.ones(n)]  # intercept
        for c in _NUMERIC:
            v = pp[c].to_numpy(dtype=float) if c in pp.columns else np.zeros(n)
            if c in _STANDARDIZE:
                v = (v - self.mean_.get(c, 0.0)) / self.std_.get(c, 1.0)
            cols.append(v)
        pos = pp["position"].astype(str) if "position" in pp.columns else pd.Series(["NA"] * n)
        for p in self.positions[1:]:  # drop-first reference
            cols.append((pos == p).to_numpy(dtype=float))
        return np.column_stack(cols)

    def fit(self, history: pd.DataFrame, **kw: object) -> DiscreteTimeHazard:
        """Fit on `history`; degrade to *unfitted* when the event signal is unusable."""
        pp = build_person_periods(history, window=self.window, decay=self.decay, **kw)  # type: ignore[arg-type]
        y = pp["out"].to_numpy(dtype=float)
        # need both classes and enough rows, else the logistic is meaningless → stay neutral
        if len(pp) < 10 or y.sum() == 0 or y.sum() == len(y):
            self.fitted = False
            self.neutral_hazard = float(y.mean()) if len(y) else 0.0
            return self
        for c in _STANDARDIZE:
            v = pp[c].to_numpy(dtype=float)
            self.mean_[c] = float(v.mean())
            self.std_[c] = float(v.std()) or 1.0
        self.positions = sorted(pp["position"].astype(str).unique())
        self.feature_names = [
            "intercept", *_NUMERIC, *[f"pos_{p}" for p in self.positions[1:]]
        ]
        self.beta = _fit_logistic(self._design(pp), y, l2=self.l2)
        self.neutral_hazard = float(y.mean())
        self.fitted = True
        return self

    def predict_hazard(self, frame: pd.DataFrame) -> np.ndarray:
        """Per-row weekly hazard (P(unavailable)); neutral base rate when unfitted."""
        pp = build_person_periods(frame, window=self.window, decay=self.decay)
        if not self.fitted:
            return np.full(len(pp), self.neutral_hazard, dtype=float)
        return _sigmoid(self._design(pp) @ self.beta)

    def predict_available(self, frame: pd.DataFrame) -> np.ndarray:
        """Per-row weekly ``P(available) = 1 − hazard`` (unfitted ⇒ 1 − base rate)."""
        return 1.0 - self.predict_hazard(frame)
