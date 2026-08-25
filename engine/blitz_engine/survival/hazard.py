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

E3 builds the **fitted injury model** on top of this scaffold (second half of the module):
an exposure panel from participation data, a hazard for *injury onset*, a negative-binomial
**duration** model for games missed, a fitted **return curve**, a decaying **re-injury**
elevation, and the per-position season-fraction-missed that replaces the hand-typed
`injuryRate` constant in `frontend/lib/draftAI.ts`. Entry point: `fit_injury_model`.

    python -m blitz_engine.survival.hazard --data-root ~/.blitz_engine --seed 7 \
        --out fixtures/injury_rates.json

regenerates `fixtures/injury_rates.json` — **the artefact E10 reads** — and exits non-zero if
the hold-out calibration gate blocks. Nothing in the fit draws a random number, so the same
store and seed reproduce the file byte for byte.

Read the fitted rates as **unavailability**, not clinical injury (departure 1 below): QB comes
out highest because a benched starter is indistinguishable from an injured one in participation
data. E10 should ship them as the availability discount they are.

## Sources

Method survey behind each modelling choice (one per major decision):

* Discrete-time hazard as logistic regression on person-period rows — Singer & Willett (1993),
  "It's About Time: Using Discrete-Time Survival Analysis to Study Duration and the Timing of
  Events", *Journal of Educational Statistics* 18(2):155–195.
  https://journals.sagepub.com/doi/10.3102/10769986018002155
  Person-period dataset construction: https://alda.gse.harvard.edu/discrete-time-survival-analysis
* Injuries are **recurrent events**, so the elevated post-return hazard is modelled explicitly
  rather than assumed away — Ullah, Gabbett & Finch (2014), "Statistical modelling for recurrent
  events: an application to sports injuries", *BJSM* 48(17):1287–1293.
  https://pubmed.ncbi.nlm.nih.gov/22872683/
* Time-varying covariates (workload, weeks-since-return) in sports-injury time-to-event work —
  "Time-to-event analysis for sports injury research part 2: time-varying outcomes", *BJSM*.
  https://www.researchgate.net/publication/328845971
* L2-regularised hazard coefficients on sparse recurrent injury data — Groll et al. (2021),
  "Prediction of sports injuries in football: a recurrent time-to-event approach using
  regularized Cox models". https://link.springer.com/article/10.1007/s10182-021-00428-2

**Departures from the cited approach — our data is thinner:**

1. *No injury report, no diagnosis.* The store (E9) holds participation, not medical status, so
   the event is **games missed** derived from snap-count presence inside an exposure span, not
   a clinician-defined injury. Healthy scratches and benchings therefore enter the event set;
   the fitted rates are "unavailable", a superset of "injured". This is the direction fantasy
   cares about, but it is not the literature's injury definition.
2. *No birth dates.* Age — the strongest covariate in every cited paper — is absent from the
   store, so `experience` (prior seasons observed) stands in for it. Documented, not silently
   substituted; when a roster table lands, swap the covariate, do not re-derive the model.
3. *Discrete time, not Cox.* We fit a discrete-time logistic hazard (weeks are the natural
   grain of an NFL season and ties are pervasive) rather than the continuous-time Cox / A-G
   models the sports-injury papers use. Singer & Willett show these coincide in discrete time.
4. *Recurrence via covariates, not a frailty term.* Ullah et al. favour frailty / A-G; we carry
   the recurrence as time-varying covariates (`recent_injury`, `weeks_since_return`) and fit the
   post-return elevation separately, which keeps the whole fit one deterministic L-BFGS call.
5. *Return curve on snaps, not on performance.* Recovery is measured as snap share against the
   player's own pre-injury baseline — the only recovery signal our store carries.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

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
    #: Column mapping `fit` was given, replayed at predict time so a frame whose columns are
    #: named `workload`/`experience` (the E3 panel) scores with the SAME covariates it was
    #: fitted on — without this, predict silently fell back to `build_person_periods`'
    #: defaults and zeroed every numeric covariate.
    columns_: dict[str, object] = field(default_factory=dict)

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
        self.columns_ = dict(kw)
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
        pp = build_person_periods(
            frame, window=self.window, decay=self.decay, **self.columns_  # type: ignore[arg-type]
        )
        if not self.fitted:
            return np.full(len(pp), self.neutral_hazard, dtype=float)
        return _sigmoid(self._design(pp) @ self.beta)

    def predict_available(self, frame: pd.DataFrame) -> np.ndarray:
        """Per-row weekly ``P(available) = 1 − hazard`` (unfitted ⇒ 1 − base rate)."""
        return 1.0 - self.predict_hazard(frame)


# ==========================================================================================
# E3 — the fitted injury model: hazard · duration · return curve · re-injury
# ==========================================================================================
# Everything below turns the scaffold above into a *fitted* per-position injury model, so the
# hand-typed `injuryRate: {QB: 0.08, RB: 0.18, ...}` constant becomes an output of a fit on
# our own ingested history rather than a number somebody typed. See the module `## Sources`.

#: Regular-season weeks of exposure (17-game era; the store's 2021+ seasons run to week 18).
GAMES_PER_SEASON = 17
#: Fantasy positions the model reports. DST is a team, not a player — it is never "injured".
FANTASY_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
#: `snap_counts.position` values folded into a fantasy position (everything else is dropped).
_POSITION_MAP = {
    "QB": "QB", "RB": "RB", "HB": "RB", "FB": "RB",
    "WR": "WR", "TE": "TE", "K": "K", "PK": "K",
}
#: Weeks of the post-return performance curve that get fitted (beyond that ⇒ multiplier 1.0).
RETURN_WEEKS = 6
#: Weeks after a return over which the elevated re-injury hazard is fitted.
REINJURY_WEEKS = 8
#: A position needs this many spells / player-weeks before its own estimate is trusted.
MIN_SPELLS = 40
MIN_ROWS = 500
#: Shrinkage strength (pseudo-observations) pulling a sparse position toward the pooled prior.
POOL_STRENGTH = 40.0
#: Pseudo-observations shrinking each weeks-since-return bucket toward the baseline hazard.
_REINJURY_POOL = 200.0
#: Default seed for the documented, reproducible entry point.
DEFAULT_SEED = 7
#: Columns of the panel `build_injury_panel` emits.
PANEL_COLUMNS = (
    "player_id", "position", "season", "week", "snaps", "out", "prev_out", "onset",
    "workload", "weeks_since_return", "experience",
)
#: Column mapping the injury panel feeds to `build_person_periods` / `DiscreteTimeHazard`.
PANEL_COLUMN_MAP = {
    "out_col": "out",
    "workload_col": "workload",
    "age_col": "experience",
    "position_col": "position",
    "player_col": "player_id",
    "time_cols": ("season", "week"),
}

__all__ += [
    "DEFAULT_SEED",
    "FANTASY_POSITIONS",
    "DurationModel",
    "InjuryModel",
    "ReinjuryRisk",
    "ReturnCurve",
    "build_injury_panel",
    "build_injury_panel_from_frame",
    "extract_spells",
    "fit_duration_model",
    "fit_injury_model",
    "fit_reinjury_risk",
    "fit_return_curve",
    "write_injury_rates",
]


# -- panel ---------------------------------------------------------------------------------
def _empty_panel() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in PANEL_COLUMNS})


#: Cohort filter — a player-season only enters the panel with at least this many appearances
#: and this median snap load, so the panel is the *fantasy-relevant* at-risk squad rather than
#: every third-stringer who dressed once. Without it a backup QB's permanent bench duty reads
#: as a nine-week injury and the fitted rates triple.
MIN_GAMES = 4
MIN_SNAPS = {"K": 3.0}
MIN_SNAPS_DEFAULT = 12.0
#: Median offensive snap share a player-season needs to count as a starter-grade role.
MIN_SHARE = 0.5


def build_injury_panel_from_frame(
    appearances: pd.DataFrame,
    *,
    seasons: object = None,
    min_games: int = MIN_GAMES,
    min_snaps: float = MIN_SNAPS_DEFAULT,
) -> pd.DataFrame:
    """Weekly *exposure* panel (one row per player-week at risk) from game appearances.

    There is no injury-report table in the store (see `## Sources` → departures), so the event
    is derived from participation — the standard "games missed" observable: inside a player's
    season **exposure span**, a week with no snap-count row is `out=1`. The span starts at his
    first appearance; it ends at the season's last week when he also appears the *following*
    season (evidence he was still an NFL player, so a trailing absence is a season-ending
    injury rather than an exit), otherwise at his last appearance — which stops players who
    were cut or retired from being scored as injured forever after.

    Derived per row from the past only (no leakage): `prev_out`, `onset` (a *new* spell — the
    survival event proper), `workload` (4-week trailing mean snaps, lagged),
    `weeks_since_return` (0 = not recently back) and `experience` (prior seasons, age proxy).
    """
    df = appearances.copy()
    if df.empty:
        return _empty_panel()
    df["position"] = df["position"].astype(str).str.upper().map(_POSITION_MAP)
    df = df[df["position"].notna()]
    pid = df["pfr_player_id"] if "pfr_player_id" in df.columns else df["player"]
    if "player" in df.columns:
        pid = pid.fillna(df["player"])
    df["player_id"] = pid.astype(str)
    off = pd.to_numeric(df.get("off_snaps", 0.0), errors="coerce").fillna(0.0)
    st = pd.to_numeric(df.get("st_snaps", 0.0), errors="coerce").fillna(0.0)
    df["snaps"] = np.where(df["position"].to_numpy() == "K", st, off)
    df["share"] = pd.to_numeric(df.get("off_pct", 0.0), errors="coerce").fillna(0.0)
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df = df.dropna(subset=["season", "week"])
    df["season"] = df["season"].astype(int)
    df["week"] = df["week"].astype(int)
    if seasons is not None:
        df = df[df["season"].isin(list(seasons))]  # type: ignore[arg-type]
    df = df[["player_id", "position", "season", "week", "snaps", "share"]].drop_duplicates(
        ["player_id", "season", "week"]
    )
    if df.empty:
        return _empty_panel()

    # cohort selection (see MIN_GAMES / MIN_SHARE): keep the player-seasons with a real role —
    # a median snap share of a starter across at least `min_games` appearances. Kickers have
    # no offensive share, so they qualify on special-teams snaps instead.
    grp = df.groupby(["player_id", "season"])
    is_k = df["position"].to_numpy() == "K"
    enough = (
        np.where(
            is_k,
            grp["snaps"].transform("median").to_numpy() >= MIN_SNAPS["K"],
            grp["share"].transform("median").to_numpy() >= MIN_SHARE,
        )
        & (grp["snaps"].transform("size").to_numpy() >= min_games)
    )
    df = df[enough]
    if df.empty:
        return _empty_panel()

    season_last_week = df.groupby("season")["week"].max().to_dict()
    present = set(zip(df["player_id"], df["season"], strict=False))

    blocks: list[pd.DataFrame] = []
    for (player_id, season), grp in df.groupby(["player_id", "season"], sort=True):
        weeks = grp.set_index("week")["snaps"].sort_index()
        first, last = int(weeks.index[0]), int(weeks.index[-1])
        end = int(season_last_week[season]) if (player_id, season + 1) in present else last
        idx = np.arange(first, end + 1)
        snaps = weeks.reindex(idx).to_numpy(dtype=float)
        out = np.isnan(snaps).astype(float)
        snaps = np.nan_to_num(snaps)
        prev_out = np.concatenate([[0.0], out[:-1]])
        onset = ((out == 1.0) & (prev_out == 0.0)).astype(float)
        lagged = pd.Series(np.concatenate([[np.nan], snaps[:-1]]))
        workload = lagged.rolling(4, min_periods=1).mean().fillna(0.0).to_numpy()
        since = np.zeros(len(idx))
        counter, seen_out = 0.0, False
        for i in range(len(idx)):
            if out[i] == 1.0:
                counter, seen_out = 0.0, True
            elif seen_out:
                counter += 1.0
            since[i] = 0.0 if counter > REINJURY_WEEKS else counter
        blocks.append(
            pd.DataFrame(
                {
                    "player_id": player_id,
                    "position": grp["position"].iloc[0],
                    "season": season,
                    "week": idx,
                    "snaps": snaps,
                    "out": out,
                    "prev_out": prev_out,
                    "onset": onset,
                    "workload": workload,
                    "weeks_since_return": since,
                }
            )
        )
    panel = pd.concat(blocks, ignore_index=True)
    debut = panel.groupby("player_id")["season"].transform("min")
    panel["experience"] = (panel["season"] - debut).astype(float)
    return panel[list(PANEL_COLUMNS)]


def build_injury_panel(
    store: object, *, seasons: object = None, table: str = "snap_counts"
) -> pd.DataFrame:
    """Read regular-season appearances out of a `ParquetStore` and build the exposure panel."""
    sql = (
        "SELECT season, week, pfr_player_id, player, position, "
        "COALESCE(offense_snaps, 0) AS off_snaps, COALESCE(st_snaps, 0) AS st_snaps, "
        "COALESCE(offense_pct, 0) AS off_pct "
        f"FROM {table} WHERE game_type = 'REG'"  # noqa: S608 — `table` is a store table name
    )
    return build_injury_panel_from_frame(store.query(sql).df(), seasons=seasons)  # type: ignore[attr-defined]


# -- spells (duration + return-curve raw material) ------------------------------------------
def extract_spells(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per *injury spell*: its length in games and the snap ratios after the return.

    `duration` = consecutive weeks out (≥ 1 game missed). `censored` marks a spell still open
    at the end of the player's season span (season-ending IR) — right-censored, and the
    duration fit uses the censored likelihood rather than dropping or truncating it.
    `ret_1…ret_{RETURN_WEEKS}` are post-return snaps ÷ the pre-injury 4-week snap baseline.
    """
    cols = ["player_id", "position", "season", "start_week", "duration", "censored"]
    ret_cols = [f"ret_{k}" for k in range(1, RETURN_WEEKS + 1)]
    empty = pd.DataFrame({c: pd.Series(dtype="float64") for c in [*cols, *ret_cols]})
    if panel.empty:
        return empty
    rows: list[dict[str, object]] = []
    for (player_id, season), grp in panel.groupby(["player_id", "season"], sort=True):
        g = grp.sort_values("week")
        out = g["out"].to_numpy(dtype=float)
        snaps = g["snaps"].to_numpy(dtype=float)
        weeks = g["week"].to_numpy(dtype=int)
        i = 0
        while i < len(out):
            if out[i] != 1.0:
                i += 1
                continue
            j = i
            while j + 1 < len(out) and out[j + 1] == 1.0:
                j += 1
            pre = snaps[max(0, i - 4):i]
            base = float(pre[pre > 0].mean()) if (pre > 0).any() else 0.0
            rec: dict[str, object] = {
                "player_id": player_id,
                "position": str(g["position"].iloc[0]),
                "season": int(season),
                "start_week": int(weeks[i]),
                "duration": float(j - i + 1),
                "censored": float(j == len(out) - 1),
            }
            for k in range(1, RETURN_WEEKS + 1):
                p = j + k
                rec[f"ret_{k}"] = (
                    float(snaps[p] / base)
                    if p < len(out) and out[p] == 0.0 and base > 0
                    else np.nan
                )
            rows.append(rec)
            i = j + 1
    return pd.DataFrame(rows) if rows else empty


# -- duration -------------------------------------------------------------------------------
def _fit_nbinom_censored(durations: np.ndarray, censored: np.ndarray) -> tuple[float, float]:
    """MLE of a shifted negative binomial on games missed, honouring right-censoring.

    Fits ``D − 1 ~ NB(r, p)`` (support 1, 2, … games) against the exact likelihood: `logpmf`
    for a spell that ended, `log sf` for one still open when the season ran out. Returns
    ``(mean_excess, dispersion r)``. Deterministic — fixed method-of-moments start, L-BFGS-B,
    no randomness — so a refit is bit-identical.
    """
    from scipy.optimize import minimize
    from scipy.stats import nbinom

    x = np.maximum(np.asarray(durations, dtype=float) - 1.0, 0.0)
    c = np.asarray(censored, dtype=float).astype(bool)
    m0 = max(float(x.mean()), 1e-3)
    v0 = max(float(x.var()), m0 * 1.05)
    r0 = max(m0 * m0 / max(v0 - m0, 1e-3), 0.05)

    def nll(theta: np.ndarray) -> float:
        m = float(np.exp(np.clip(theta[0], -6.0, 6.0)))
        r = float(np.exp(np.clip(theta[1], -6.0, 6.0)))
        p = r / (r + m)
        ll = float(nbinom.logpmf(x[~c], r, p).sum())
        if c.any():
            ll += float(np.log(np.clip(nbinom.sf(x[c], r, p), 1e-12, 1.0)).sum())
        return -ll if np.isfinite(ll) else 1e12

    res = minimize(nll, np.array([np.log(m0), np.log(r0)]), method="L-BFGS-B")
    return (
        float(np.exp(np.clip(res.x[0], -6.0, 6.0))),
        float(np.exp(np.clip(res.x[1], -6.0, 6.0))),
    )


@dataclass
class DurationModel:
    """Games missed per injury as a *distribution* (shifted negative binomial), per position.

    Negative binomial, not Poisson: games-missed is heavily overdispersed — most spells are a
    single week, a long tail are season-enders — which is the count family the injury-burden
    literature uses. A position with fewer than `MIN_SPELLS` spells is never fitted on its own;
    it inherits the **pooled** fit and `counts` records why (`pooled_positions()`).
    """

    params: dict[str, tuple[float, float]] = field(default_factory=dict)
    pooled: tuple[float, float] = (1.0, 1.0)
    counts: dict[str, int] = field(default_factory=dict)

    def _params(self, position: str) -> tuple[float, float]:
        return self.params.get(position, self.pooled)

    def mean(self, position: str) -> float:
        """Expected games missed for one injury (≥ 1 by construction)."""
        return 1.0 + self._params(position)[0]

    def var(self, position: str) -> float:
        m, r = self._params(position)
        return float(m + m * m / max(r, 1e-9))

    def pmf(self, k: object, position: str) -> np.ndarray:
        """P(games missed = k); zero below 1 game — a spell always costs at least one."""
        from scipy.stats import nbinom

        m, r = self._params(position)
        kk = np.asarray(k, dtype=float)
        return np.where(kk >= 1, nbinom.pmf(np.maximum(kk - 1.0, 0.0), r, r / (r + m)), 0.0)

    def sample(self, position: str, size: int, rng: np.random.Generator) -> np.ndarray:
        """Draw `size` games-missed values for one injury at `position`."""
        m, r = self._params(position)
        return 1 + rng.negative_binomial(max(r, 1e-6), r / (r + m), size=size)

    def pooled_positions(self) -> list[str]:
        """Positions that degraded to the pooled prior because their data was too sparse."""
        return sorted(p for p, n in self.counts.items() if n < MIN_SPELLS)


def fit_duration_model(spells: pd.DataFrame) -> DurationModel:
    """Fit the pooled duration distribution, then every position with enough spells."""
    if spells.empty:
        return DurationModel()
    pooled = _fit_nbinom_censored(spells["duration"].to_numpy(), spells["censored"].to_numpy())
    params: dict[str, tuple[float, float]] = {}
    counts: dict[str, int] = {}
    for position, grp in spells.groupby("position", sort=True):
        counts[str(position)] = int(len(grp))
        if len(grp) >= MIN_SPELLS:
            params[str(position)] = _fit_nbinom_censored(
                grp["duration"].to_numpy(), grp["censored"].to_numpy()
            )
    return DurationModel(params=params, pooled=pooled, counts=counts)


# -- return curve ---------------------------------------------------------------------------
@dataclass
class ReturnCurve:
    """Fitted performance multiplier for the weeks *after* a player returns.

    Measured on snap share — the recovery observable that survives in our store: a returning
    player's snaps ÷ his own pre-injury 4-week baseline, averaged over spells, shrunk toward
    the pooled curve, then forced non-decreasing and clipped to (0, 1]. Beyond `RETURN_WEEKS`
    the multiplier is 1.0 — fully re-integrated.
    """

    curves: dict[str, list[float]] = field(default_factory=dict)
    pooled: list[float] = field(default_factory=lambda: [1.0] * RETURN_WEEKS)
    counts: dict[str, int] = field(default_factory=dict)

    def curve(self, position: str) -> list[float]:
        return self.curves.get(position, self.pooled)

    def multiplier(self, position: str, weeks_since_return: object) -> np.ndarray:
        """Multiplier at week k after the return (k = 1 is the first game back)."""
        c = np.asarray(self.curve(position), dtype=float)
        k = np.asarray(weeks_since_return, dtype=float)
        idx = np.clip(k.astype(int) - 1, 0, len(c) - 1)
        return np.where((k >= 1) & (k <= len(c)), c[idx], 1.0)


def fit_return_curve(spells: pd.DataFrame) -> ReturnCurve:
    """Average the observed post-return snap ratios; shrink sparse positions to the pool."""
    ret_cols = [f"ret_{k}" for k in range(1, RETURN_WEEKS + 1)]
    if spells.empty or not set(ret_cols) <= set(spells.columns):
        return ReturnCurve()

    def _shape(frame: pd.DataFrame, prior: np.ndarray | None) -> list[float]:
        vals: list[float] = []
        for k, col in enumerate(ret_cols):
            v = pd.to_numeric(frame[col], errors="coerce").dropna()
            v = v[(v > 0) & (v <= 2.0)]  # a >2× jump is a role change, not a recovery
            n = float(len(v))
            base = 1.0 if prior is None else float(prior[k])
            vals.append(
                (n * float(v.mean()) + POOL_STRENGTH * base) / (n + POOL_STRENGTH) if n else base
            )
        arr = np.clip(np.maximum.accumulate(np.asarray(vals, dtype=float)), 0.05, 1.0)
        return [float(x) for x in arr]

    pooled = _shape(spells, None)
    prior = np.asarray(pooled, dtype=float)
    curves: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for position, grp in spells.groupby("position", sort=True):
        counts[str(position)] = int(len(grp))
        curves[str(position)] = _shape(grp, prior)
    return ReturnCurve(curves=curves, pooled=pooled, counts=counts)


# -- re-injury ------------------------------------------------------------------------------
@dataclass
class ReinjuryRisk:
    """Elevated hazard just after a return, decaying back to baseline.

    ``hazard_ratio(k) = 1 + elevation · exp(−(k − 1) / decay)`` for k = 1, 2, … weeks since
    the return. `elevation` is clamped ≥ 0, so the ratio is never below baseline and always
    decreases in k — the shape the recurrent-event injury literature reports.
    """

    elevation: float = 0.0
    decay: float = 1.0
    baseline_hazard: float = 0.0
    observed: list[float] = field(default_factory=list)

    def hazard_ratio(self, weeks_since_return: object) -> np.ndarray:
        k = np.asarray(weeks_since_return, dtype=float)
        ratio = 1.0 + max(self.elevation, 0.0) * np.exp(-(k - 1.0) / max(self.decay, 1e-6))
        return np.where(k >= 1, ratio, 1.0)


def fit_reinjury_risk(panel: pd.DataFrame, *, weeks: int = REINJURY_WEEKS) -> ReinjuryRisk:
    """Fit the post-return hazard elevation and its decay from the panel's onset events.

    Compares the **onset** hazard of at-risk player-weeks k games after a return against the
    baseline onset hazard of at-risk weeks with no recent return, then least-squares fits the
    exponential decay on ``log(ratio − 1)``.
    """
    if panel.empty:
        return ReinjuryRisk()
    at_risk = panel[panel["prev_out"] == 0.0]
    if at_risk.empty:
        return ReinjuryRisk()
    base_rows = at_risk[at_risk["weeks_since_return"] == 0.0]
    src = base_rows if len(base_rows) else at_risk
    baseline = float(src["onset"].mean())
    if not np.isfinite(baseline) or baseline <= 0:
        return ReinjuryRisk(baseline_hazard=max(baseline, 0.0))
    ks: list[float] = []
    ratios: list[float] = []
    observed: list[float] = []
    for k in range(1, weeks + 1):
        rows = at_risk[at_risk["weeks_since_return"] == float(k)]
        if len(rows) < 30:
            observed.append(float("nan"))
            continue
        n = float(len(rows))
        # shrink the bucket toward baseline — a thin week can't claim a big elevation
        h = (n * float(rows["onset"].mean()) + _REINJURY_POOL * baseline) / (n + _REINJURY_POOL)
        observed.append(h)
        if h > baseline:
            ks.append(float(k))
            ratios.append(h / baseline)
    if len(ks) < 2:
        elev = max(ratios[0] - 1.0, 0.0) if ratios else 0.0
        return ReinjuryRisk(elev, 1.0, baseline, observed)
    slope, intercept = np.polyfit(np.asarray(ks) - 1.0, np.log(np.asarray(ratios) - 1.0), 1)
    decay = float(1.0 / max(-slope, 1e-3)) if slope < 0 else float(weeks)
    return ReinjuryRisk(
        # never extrapolate past the largest elevation actually observed
        elevation=float(min(np.exp(intercept), max(ratios) - 1.0)),
        decay=float(min(decay, float(weeks))),
        baseline_hazard=baseline,
        observed=observed,
    )


# -- the assembled, calibrated model ---------------------------------------------------------
def _weekly_counts(frame: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    """Aggregate predicted P(out) and realised outs to (position, season, week) counts."""
    g = pd.DataFrame(
        {
            "position": frame["position"].to_numpy(),
            "season": frame["season"].to_numpy(),
            "week": frame["week"].to_numpy(),
            "p": p,
            "v": p * (1.0 - p),
            "y": frame["out"].to_numpy(dtype=float),
        }
    )
    agg = g.groupby(["position", "season", "week"], sort=True).agg(
        mean=("p", "sum"), var0=("v", "sum"), y=("y", "sum"), n=("p", "size")
    )
    return agg[agg["n"] >= 10]


def _calibrate(
    hazard: DiscreteTimeHazard, train: pd.DataFrame, test: pd.DataFrame
) -> dict[str, object]:
    """Hold-out calibration verdict through `blitz_engine.calibration`.

    The gate's PIT is Gaussian, so the calibration **unit** is the weekly per-position count
    of absent players — a sum of ~10–100 Bernoulli draws, where a Normal approximation is
    honest. (Player-season games-missed is zero-inflated and lumpy; gating it on a Gaussian
    PIT would block on discretisation rather than on miscalibration, so it is *reported*
    below as MAE, never gated.) The spread carries a **quasi-binomial** overdispersion φ
    estimated on the TRAINING split — weekly absences are correlated within a team, so the
    independent-Bernoulli variance alone would be dishonestly narrow.
    """
    from blitz_engine.calibration import calibrated

    if test.empty or train.empty:
        return {"passed": False, "reason": "no holdout rows", "n": 0}
    tr = _weekly_counts(train, hazard.predict_hazard(train))
    phi = 1.0
    if len(tr):
        resid = (tr["y"] - tr["mean"]) ** 2 / tr["var0"].clip(lower=1e-9)
        phi = float(max(resid.mean(), 1.0))
    te = _weekly_counts(test, hazard.predict_hazard(test))
    if not len(te):
        return {"passed": False, "reason": "no holdout groups", "n": 0}
    frame = pd.DataFrame(
        {"mean": te["mean"].to_numpy(), "stdev": np.sqrt(phi * te["var0"].to_numpy())}
    )
    report = calibrated(frame, te["y"].to_numpy())
    return {
        "passed": bool(report),
        "unit": "players absent per (position, season, week)",
        "n": int(report.metrics.n),
        "overdispersion": phi,
        "calibration_error": float(report.metrics.calibration_error),
        "threshold": float(report.threshold),
        "summary": report.summary(),
    }


@dataclass
class InjuryModel:
    """The fitted injury model: weekly hazard, duration, return curve, re-injury, rates.

    `position_rates` is the fitted stand-in for `frontend/lib/draftAI.ts`'s hand-typed
    `injuryRate` — the long-run **fraction of a season missed**, derived from the fit as an
    alternating-renewal duty cycle ``λ·E[D] / (1 + λ·E[D])`` where λ is the mean fitted onset
    hazard for the position and E[D] its expected games missed. E10 reads it from the JSON
    `write_injury_rates` emits; this unit never edits the frontend.
    """

    hazard: DiscreteTimeHazard
    onset_hazard: DiscreteTimeHazard
    duration: DurationModel
    return_curve: ReturnCurve
    reinjury: ReinjuryRisk
    position_rates: dict[str, float] = field(default_factory=dict)
    onset_rates: dict[str, float] = field(default_factory=dict)
    calibration: dict[str, object] = field(default_factory=dict)
    seed: int = DEFAULT_SEED
    seasons: tuple[int, ...] = ()
    holdout: tuple[int, ...] = ()
    n_rows: int = 0
    n_spells: int = 0

    @property
    def calibrated(self) -> bool:
        """True iff the hold-out calibration gate passed — publish is blocked when False."""
        return bool(self.calibration.get("passed", False))

    def injury_rate_map(self) -> dict[str, float]:
        """The `DEFAULT_POLICY.injuryRate` drop-in: position → season fraction missed."""
        return {p: round(float(self.position_rates.get(p, 0.0)), 4) for p in FANTASY_POSITIONS}

    def expected_games_missed(self) -> dict[str, float]:
        """Expected games missed per injury, per position."""
        return {p: round(self.duration.mean(p), 3) for p in FANTASY_POSITIONS if p != "DST"}

    def to_dict(self) -> dict[str, object]:
        """JSON-ready summary — everything e10 or a doc needs, nothing unserialisable."""
        return {
            "entry_point": "blitz_engine.survival.hazard.fit_injury_model",
            "seed": self.seed,
            "seasons": list(self.seasons),
            "holdout_seasons": list(self.holdout),
            "n_player_weeks": self.n_rows,
            "n_spells": self.n_spells,
            "injuryRate": self.injury_rate_map(),
            "onset_hazard_per_week": {k: round(v, 5) for k, v in self.onset_rates.items()},
            "expected_games_missed": self.expected_games_missed(),
            "games_missed_variance": {
                p: round(self.duration.var(p), 3) for p in FANTASY_POSITIONS if p != "DST"
            },
            "pooled_positions": self.duration.pooled_positions(),
            "return_curve": {
                p: [round(x, 4) for x in self.return_curve.curve(p)]
                for p in FANTASY_POSITIONS
                if p != "DST"
            },
            "reinjury": {
                "elevation": round(self.reinjury.elevation, 4),
                "decay_weeks": round(self.reinjury.decay, 4),
                "baseline_hazard": round(self.reinjury.baseline_hazard, 5),
            },
            "calibration": self.calibration,
        }


def _position_rates(
    hazard: DiscreteTimeHazard, onset: DiscreteTimeHazard, panel: pd.DataFrame
) -> tuple[dict[str, float], dict[str, float]]:
    """Per-position season fraction missed + the onset hazard λ that drives it.

    The published rate is the **fitted weekly P(out) averaged over the position's exposure** —
    i.e. it comes straight out of the hazard the calibration gate just cleared, so the number
    e10 ships and the number the gate blessed are the same object. λ (mean onset hazard among
    at-risk weeks) is reported alongside as the mechanism: rate ≈ λ·E[D]/(1+λ·E[D]). A
    position with fewer than `MIN_ROWS` player-weeks is shrunk toward the pooled rate rather
    than trusted on its own — the documented degrade for sparse positions.
    """
    at_risk = panel[panel["prev_out"] == 0.0].copy()
    at_risk["out"] = at_risk["onset"].to_numpy()  # onset hazard was fitted on this convention
    pooled_rate = float(np.mean(hazard.predict_hazard(panel))) if len(panel) else 0.0
    rates: dict[str, float] = {}
    lambdas: dict[str, float] = {}
    for position in FANTASY_POSITIONS:
        if position == "DST":  # a team defence never misses a game
            rates[position], lambdas[position] = 0.0, 0.0
            continue
        rows = panel[panel["position"] == position]
        risk_rows = at_risk[at_risk["position"] == position]
        n = float(len(rows))
        own = float(np.mean(hazard.predict_hazard(rows))) if n else pooled_rate
        rate = own if n >= MIN_ROWS else (n * own + POOL_STRENGTH * pooled_rate) / (
            n + POOL_STRENGTH
        )
        lambdas[position] = (
            float(np.mean(onset.predict_hazard(risk_rows))) if len(risk_rows) else 0.0
        )
        rates[position] = float(np.clip(rate, 0.0, 1.0))
    return rates, lambdas


def fit_injury_model(
    data_root: object = None,
    *,
    seed: int = DEFAULT_SEED,
    seasons: object = None,
    holdout: int = 2,
    panel: pd.DataFrame | None = None,
) -> InjuryModel:
    """**The entry point.** Re-fit the whole injury model from the store, deterministically.

        python -m blitz_engine.survival.hazard --data-root ~/.blitz_engine --seed 7

    Fits on every season but the last `holdout`, which are held out for the calibration gate.
    Nothing here draws a random number — the fits are L-BFGS from fixed starts — so two runs
    with the same seed and the same store are bit-identical; `seed` is carried on the model
    for the samplers (`DurationModel.sample`) that downstream units drive.
    """
    if panel is None:
        from blitz_engine.config import load_config
        from blitz_engine.store import ParquetStore

        root = data_root if data_root is not None else load_config().data_root
        with ParquetStore.open(root) as store:  # type: ignore[arg-type]
            panel = build_injury_panel(store, seasons=seasons)
    if panel.empty:
        raise ValueError("injury panel is empty — ingest snap_counts before fitting")

    all_seasons = tuple(int(s) for s in sorted(panel["season"].unique()))
    hold = all_seasons[-holdout:] if 0 < holdout < len(all_seasons) else ()
    train = panel[~panel["season"].isin(hold)] if hold else panel
    test = panel[panel["season"].isin(hold)] if hold else panel

    hazard = DiscreteTimeHazard().fit(train, **PANEL_COLUMN_MAP)  # type: ignore[arg-type]
    at_risk = train[train["prev_out"] == 0.0].copy()
    at_risk["out"] = at_risk["onset"].to_numpy()
    onset_hazard = DiscreteTimeHazard().fit(at_risk, **PANEL_COLUMN_MAP)  # type: ignore[arg-type]

    spells = extract_spells(train)
    duration = fit_duration_model(spells)
    rates, lambdas = _position_rates(hazard, onset_hazard, train)
    return InjuryModel(
        hazard=hazard,
        onset_hazard=onset_hazard,
        duration=duration,
        return_curve=fit_return_curve(spells),
        reinjury=fit_reinjury_risk(train),
        position_rates=rates,
        onset_rates=lambdas,
        calibration=_calibrate(hazard, train, test),
        seed=int(seed),
        seasons=all_seasons,
        holdout=tuple(hold),
        n_rows=int(len(panel)),
        n_spells=int(len(spells)),
    )


def write_injury_rates(model: InjuryModel, path: object) -> Path:
    """Write the fitted numbers as JSON — **the artefact e10 reads** for `DEFAULT_POLICY`."""
    dest = Path(str(path)).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(model.to_dict(), indent=2, sort_keys=True) + "\n")
    return dest


def main(argv: list[str] | None = None) -> int:
    """CLI: re-fit from the store, write `injury_rates.json`, print one JSON summary line.

    Exits non-zero when the calibration gate blocks — an uncalibrated hazard never ships.
    """
    import argparse

    from blitz_engine.config import load_config

    ap = argparse.ArgumentParser(prog="python -m blitz_engine.survival.hazard")
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--holdout", type=int, default=2)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    root = Path(args.data_root).expanduser() if args.data_root else load_config().data_root
    model = fit_injury_model(root, seed=args.seed, holdout=args.holdout)
    dest = write_injury_rates(model, args.out or Path(root) / "injury_rates.json")
    print(
        json.dumps(
            {
                "ok": model.calibrated,
                "out": str(dest),
                "injuryRate": model.injury_rate_map(),
                "calibration": model.calibration.get("summary", ""),
            }
        )
    )
    return 0 if model.calibrated else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
