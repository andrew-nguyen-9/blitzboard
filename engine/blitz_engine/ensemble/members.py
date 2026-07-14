"""Ensemble members — the diverse base learners the stack averages over.

Each member is a **named predictive-distribution model**: given a leakage-safe `(train, test)`
split (the same E7 walk-forward protocol), it emits a `MemberPrediction(mean, stdev)` — a
Gaussian summary per test row. Diversity is the whole point of an ensemble, so the roster
spans three model families plus the market:

  * **bayesian** — the E1 hierarchical core (`backtest.engine_predictor`), wrapped as a member.
  * **gbm**      — gradient-boosted trees (LightGBM if importable, else a compact numpy
    gradient-boosted-stumps fallback — `sklearn`/`lightgbm` are ABSENT from the engine venv).
  * **nn**       — a small torch MLP (lazy-imported; torch is the one heavy dep present).
  * **market**   — the Vegas+ADP+FantasyPros consensus (`backtest.fantasypros_predictor`),
    both an informative prior member and the benchmark the blend must beat (see `market.py`).

Every member is also a plain E7 `Predictor` via `.as_predictor()` (mean only), so members and
the ensemble drop straight into `walk_forward` / `ablation` / `no_regression`.

`ponytail:` GBM = boosted decision *stumps* (the classic weak learner), no CART zoo; NN = one
hidden layer; both borrow the E1 `points_of` scoring and per-player feature table — no new
feature pipeline.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import pandas as pd

from blitz_engine.backtest import engine_predictor, fantasypros_predictor, points_of
from blitz_engine.projection.families import ScoringWeights

if TYPE_CHECKING:
    from collections.abc import Callable

    from blitz_engine.backtest.harness import Predictor

__all__ = [
    "CallableMember",
    "EnsembleMember",
    "GBMMember",
    "MemberPrediction",
    "NNMember",
    "PredictorMember",
    "bayesian_member",
    "gbm_member",
    "market_member",
    "nn_member",
]

FloatArray = npt.NDArray[np.float64]
_NUM_FEATURES = ["opportunities", "yards", "tds", "team_plays"]


def _weights(scoring: dict | None) -> ScoringWeights:
    return ScoringWeights.from_scoring(scoring or {})


@dataclass(frozen=True)
class MemberPrediction:
    """A member's Gaussian forecast for a batch of test rows (mean + stdev per row)."""

    mean: FloatArray
    stdev: FloatArray


class EnsembleMember:
    """A named base learner emitting a predictive distribution over test rows.

    Subclasses implement `predict`; `as_predictor` exposes the mean-only E7 `Predictor` view
    so any member slots into the walk-forward harness unchanged.
    """

    name: str = "member"

    def predict(self, train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        raise NotImplementedError

    def as_predictor(self) -> Callable[[pd.DataFrame, pd.DataFrame], FloatArray]:
        def predict(train: pd.DataFrame, test: pd.DataFrame) -> FloatArray:
            return self.predict(train, test).mean

        return predict


class CallableMember(EnsembleMember):
    """Wrap an arbitrary `(train, test) -> MemberPrediction` function as a member (tests, DI)."""

    def __init__(
        self, name: str, fn: Callable[[pd.DataFrame, pd.DataFrame], MemberPrediction]
    ) -> None:
        self.name = name
        self._fn = fn

    def predict(self, train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        return self._fn(train, test)


def _residual_sigma(train: pd.DataFrame, weights: ScoringWeights) -> float:
    """Aleatoric spread = stdev of train points around their positional mean (a floor > 0)."""
    pts = np.asarray(points_of(train, weights), dtype=np.float64)
    pos = train["position"].astype(str).to_numpy()
    resid = pts.copy()
    for p in np.unique(pos):
        m = pos == p
        resid[m] = pts[m] - pts[m].mean()
    return max(float(np.std(resid)), 1e-3)


class PredictorMember(EnsembleMember):
    """Adapt a mean-only E7 `Predictor` into a member by attaching a residual-based stdev.

    This is how the Bayesian core (`engine_predictor`) and the market line become members
    without changing the E7 predictor contract. Pass an explicit `sigma` to override the
    residual estimate (e.g. a market spread).
    """

    def __init__(
        self,
        name: str,
        predictor: Predictor,
        *,
        scoring: dict | None = None,
        sigma: float | None = None,
    ) -> None:
        self.name = name
        self._predict = predictor
        self._weights = _weights(scoring)
        self._sigma = sigma

    def predict(self, train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        mean = np.asarray(self._predict(train, test), dtype=np.float64)
        sd = self._sigma if self._sigma is not None else _residual_sigma(train, self._weights)
        return MemberPrediction(mean=mean, stdev=np.full(mean.shape, float(sd)))


# ── shared tabular design: per-player history → features/target ───────────────────
def _player_table(train: pd.DataFrame, weights: ScoringWeights) -> pd.DataFrame:
    """Collapse the train player-weeks into one feature row per player (career means)."""
    d = train.copy()
    d["_pts"] = points_of(d, weights)
    d["player_id"] = d["player_id"].astype(str)
    d["position"] = d["position"].astype(str)
    g = d.groupby("player_id")
    tbl = g[_NUM_FEATURES].mean()
    tbl["points"] = g["_pts"].mean()
    tbl["position"] = g["position"].agg(lambda s: s.iloc[0])
    return tbl


def _encode(num: FloatArray, positions: list[str], pos: npt.NDArray) -> FloatArray:
    onehot = (
        np.stack([(pos == p).astype(np.float64) for p in positions], axis=1)
        if positions
        else np.zeros((num.shape[0], 0))
    )
    return np.concatenate([num, onehot], axis=1)


def _design(
    train: pd.DataFrame, test: pd.DataFrame, weights: ScoringWeights
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """(X_train, y_train, X_test) for a tabular member; test rows use their train history.

    Unknown test players fall back to their position's mean feature row (or the overall mean),
    mirroring how the baseline/engine predictors align by player — leakage-safe (train only).
    """
    tbl = _player_table(train, weights)
    positions = sorted(tbl["position"].unique())
    x_tr = _encode(
        tbl[_NUM_FEATURES].to_numpy(dtype=np.float64), positions, tbl["position"].to_numpy()
    )
    y_tr = tbl["points"].to_numpy(dtype=np.float64)

    overall = tbl[_NUM_FEATURES].mean().to_numpy(dtype=np.float64)
    pos_mean = tbl.groupby("position")[_NUM_FEATURES].mean()
    known = {pid: i for i, pid in enumerate(tbl.index)}
    rows: list[FloatArray] = []
    for pid, pos in zip(
        test["player_id"].astype(str), test["position"].astype(str), strict=False
    ):
        if pid in known:
            rows.append(x_tr[known[pid]])
        else:
            base = pos_mean.loc[pos].to_numpy(np.float64) if pos in pos_mean.index else overall
            onehot = np.array([1.0 if pos == p else 0.0 for p in positions])
            rows.append(np.concatenate([base, onehot]))
    x_te = np.vstack(rows) if rows else np.zeros((0, x_tr.shape[1]))
    return x_tr, y_tr, x_te


def _sigma_of(resid: FloatArray) -> float:
    return max(float(np.std(resid)), 1e-3) if resid.size else 1.0


# ── GBM member: LightGBM if present, else numpy gradient-boosted stumps ────────────
class _Stump:
    """A single decision stump (depth-1 regression tree) — the boosting weak learner."""

    __slots__ = ("feature", "threshold", "lo", "hi")

    def fit(self, x: FloatArray, r: FloatArray, *, max_thresholds: int = 32) -> _Stump:
        base = float(r.mean())
        self.feature, self.threshold, self.lo, self.hi = 0, np.inf, base, base
        best_sse = float(((r - base) ** 2).sum())
        for j in range(x.shape[1]):
            xs = np.unique(x[:, j])
            if xs.size < 2:
                continue
            mids = (xs[:-1] + xs[1:]) / 2.0
            if mids.size > max_thresholds:
                mids = np.quantile(mids, np.linspace(0, 1, max_thresholds))
            for t in mids:
                m = x[:, j] <= t
                if m.all() or not m.any():
                    continue
                lo, hi = float(r[m].mean()), float(r[~m].mean())
                sse = float(((r[m] - lo) ** 2).sum() + ((r[~m] - hi) ** 2).sum())
                if sse < best_sse:
                    best_sse = sse
                    self.feature, self.threshold, self.lo, self.hi = j, float(t), lo, hi
        return self

    def predict(self, x: FloatArray) -> FloatArray:
        return np.where(x[:, self.feature] <= self.threshold, self.lo, self.hi)


class _NumpyGBRT:
    """Compact gradient-boosted stumps — the dependency-free fallback when LightGBM is absent."""

    def __init__(self, *, n_estimators: int, learning_rate: float) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.base = 0.0
        self.stumps: list[_Stump] = []

    def fit(self, x: FloatArray, y: FloatArray) -> _NumpyGBRT:
        self.base = float(np.mean(y)) if y.size else 0.0
        self.stumps = []
        pred = np.full(y.shape, self.base)
        for _ in range(self.n_estimators):
            if y.size < 2:
                break
            stump = _Stump().fit(x, y - pred)
            self.stumps.append(stump)
            pred = pred + self.learning_rate * stump.predict(x)
        return self

    def predict(self, x: FloatArray) -> FloatArray:
        out = np.full(x.shape[0], self.base)
        for stump in self.stumps:
            out = out + self.learning_rate * stump.predict(x)
        return out


def _fit_gbm(x: FloatArray, y: FloatArray, *, n_estimators: int, learning_rate: float,
             max_depth: int) -> Callable[[FloatArray], FloatArray]:
    try:
        import lightgbm as lgb  # noqa: PLC0415 — optional, absent from the engine venv
    except ImportError:
        model = _NumpyGBRT(n_estimators=n_estimators, learning_rate=learning_rate).fit(x, y)
        return model.predict
    reg = lgb.LGBMRegressor(
        n_estimators=n_estimators, learning_rate=learning_rate, max_depth=max_depth, verbose=-1
    )
    reg.fit(x, y)
    return lambda z: np.asarray(reg.predict(z), dtype=np.float64)


class GBMMember(EnsembleMember):
    """Gradient-boosted trees over the per-player feature table (tree-model diversity)."""

    def __init__(
        self,
        scoring: dict | None = None,
        *,
        name: str = "gbm",
        n_estimators: int = 60,
        learning_rate: float = 0.1,
        max_depth: int = 3,
    ) -> None:
        self.name = name
        self._weights = _weights(scoring)
        self._kw = dict(n_estimators=n_estimators, learning_rate=learning_rate, max_depth=max_depth)

    def predict(self, train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        x_tr, y_tr, x_te = _design(train, test, self._weights)
        if y_tr.size < 2 or x_te.shape[0] == 0:
            mean = np.full(x_te.shape[0], float(y_tr.mean()) if y_tr.size else 0.0)
            return MemberPrediction(mean=mean, stdev=np.full(mean.shape, _sigma_of(y_tr)))
        predict = _fit_gbm(x_tr, y_tr, **self._kw)  # type: ignore[arg-type]
        mean = np.asarray(predict(x_te), dtype=np.float64)
        sd = _sigma_of(y_tr - np.asarray(predict(x_tr), dtype=np.float64))
        return MemberPrediction(mean=mean, stdev=np.full(mean.shape, sd))


# ── NN member: a small torch MLP (lazy import) ────────────────────────────────────
def _standardize(x: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    mu = x.mean(axis=0)
    sd = x.std(axis=0)
    sd[sd < 1e-9] = 1.0
    return (x - mu) / sd, mu, sd


def _fit_nn(
    x: FloatArray, y: FloatArray, *, hidden: int, epochs: int, lr: float, seed: int
) -> Callable[[FloatArray], FloatArray]:
    import torch  # noqa: PLC0415 — heavy; keep the import lazy so module load stays cheap

    torch.manual_seed(seed)
    xs, mu, sd = _standardize(x)
    xt = torch.tensor(xs, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32).view(-1, 1)
    net = torch.nn.Sequential(
        torch.nn.Linear(x.shape[1], hidden), torch.nn.ReLU(), torch.nn.Linear(hidden, 1)
    )
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()
    for _ in range(epochs):
        opt.zero_grad()
        loss_fn(net(xt), yt).backward()
        opt.step()

    def predict(z: FloatArray) -> FloatArray:
        with torch.no_grad():
            zt = torch.tensor((z - mu) / sd, dtype=torch.float32)
            return net(zt).view(-1).numpy().astype(np.float64)

    return predict


class NNMember(EnsembleMember):
    """A small MLP over the per-player feature table (smooth-function diversity)."""

    def __init__(
        self,
        scoring: dict | None = None,
        *,
        name: str = "nn",
        hidden: int = 16,
        epochs: int = 200,
        lr: float = 0.03,
        seed: int = 0,
    ) -> None:
        self.name = name
        self._weights = _weights(scoring)
        self._kw = dict(hidden=hidden, epochs=epochs, lr=lr, seed=seed)

    def predict(self, train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        x_tr, y_tr, x_te = _design(train, test, self._weights)
        if y_tr.size < 2 or x_te.shape[0] == 0:
            mean = np.full(x_te.shape[0], float(y_tr.mean()) if y_tr.size else 0.0)
            return MemberPrediction(mean=mean, stdev=np.full(mean.shape, _sigma_of(y_tr)))
        predict = _fit_nn(x_tr, y_tr, **self._kw)  # type: ignore[arg-type]
        mean = np.asarray(predict(x_te), dtype=np.float64)
        sd = _sigma_of(y_tr - np.asarray(predict(x_tr), dtype=np.float64))
        return MemberPrediction(mean=mean, stdev=np.full(mean.shape, sd))


# ── factories: the four-family default roster ─────────────────────────────────────
def bayesian_member(
    scoring: dict | None = None,
    *,
    name: str = "bayesian",
    sigma: float | None = None,
    **fit_kw: object,
) -> PredictorMember:
    """The E1 hierarchical core as a member (mean from `engine_predictor`, residual stdev)."""
    predictor = engine_predictor(scoring, **fit_kw)  # type: ignore[arg-type]
    return PredictorMember(name, predictor, scoring=scoring, sigma=sigma)


def gbm_member(scoring: dict | None = None, **kw: object) -> GBMMember:
    return GBMMember(scoring, **kw)  # type: ignore[arg-type]


def nn_member(scoring: dict | None = None, **kw: object) -> NNMember:
    return NNMember(scoring, **kw)  # type: ignore[arg-type]


def market_member(
    projections: pd.DataFrame,
    *,
    name: str = "market",
    points_col: str = "proj_points",
    time_col: str = "season",
    sigma: float | None = None,
) -> PredictorMember:
    """The Vegas+ADP+FantasyPros consensus as an informative-prior member (see `market.py`)."""
    pred = fantasypros_predictor(projections, time_col=time_col, points_col=points_col)
    spread = float(np.std(projections[points_col])) if len(projections) else 1.0
    return PredictorMember(name, pred, sigma=sigma if sigma is not None else max(spread, 1e-3))


def _crc_u01(key: str) -> float:
    """Deterministic Uniform(0,1) hash — used by tests for reproducible pseudo-noise members."""
    return (zlib.crc32(key.encode()) % 100_000) / 100_000.0
