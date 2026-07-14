"""Correlation structure for the correlated Monte-Carlo core (E3).

The MC sim draws player-week fantasy points from a **joint** distribution, not P
independent marginals — because the outcomes that decide a lineup are correlated:

    QB ↔ his WR/TE     positive   (a passing game lifts both)
    QB ↔ his RB        slight −   (a pass-heavy script is a run-light one)
    RB ↔ team pass-catchers   −   (proxy for RB ↔ team pass volume)
    same-game opponents       +   (a shootout inflates both offenses)
    DST ↔ opposing offense    −   (a defense scores when the opponent's script fails)

`build_correlation` turns a tidy per-player frame (position / team / opponent) plus a
tunable `CorrelationSpec` into a valid P×P correlation matrix — **the matrix that ships
in the snapshot** (`corr_matrix` table), enabling a cheap live re-sim in the frontend.

Degrade-neutral: any player whose position/opponent is unknown simply gets zero
off-diagonal (independent), so a missing signal can never distort the joint — it only
loses the correlation lift, mirroring the E1/E2 seam guarantee.

`ponytail:` numpy broadcasting builds every pairwise rule as a boolean mask — no O(P²)
Python loop, no graph library.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

__all__ = [
    "CorrelationSpec",
    "build_correlation",
    "cholesky_factor",
    "nearest_psd_correlation",
]

# Offensive skill positions that share a team's play-script.
_OFFENSE = frozenset({"QB", "RB", "WR", "TE", "K", "FB"})
_DST = frozenset({"DST", "DEF", "D/ST"})
_RECEIVERS = frozenset({"WR", "TE"})


@dataclass(frozen=True)
class CorrelationSpec:
    """Tunable correlation coefficients for the factor/rule structure.

    Every field is a target Pearson correlation in (-1, 1); the assembled matrix is
    projected to the nearest valid (PSD, unit-diagonal) correlation before use, so these
    are *desired* strengths, not guaranteed exact entries.
    """

    qb_wr: float = 0.35          # QB ↔ same-team WR (the classic stack)
    qb_te: float = 0.25          # QB ↔ same-team TE
    qb_rb: float = -0.10         # QB ↔ same-team RB (pass vs run script)
    rb_receivers: float = -0.10  # RB ↔ same-team WR/TE (RB ↔ team pass volume, −)
    same_pos: float = -0.05      # same team, same skill position (usage competition)
    game_stack: float = 0.12     # opposing offenses in the same game (shootout, +)
    dst_opp_offense: float = -0.25  # a DST ↔ the opposing offense (script, −)


def _col(players: pd.DataFrame, *names: str) -> npt.NDArray[np.object_] | None:
    """First present column among `names` as an object array, else None (degrade)."""
    for n in names:
        if n in players.columns:
            return players[n].astype("string").to_numpy(dtype=object)
    return None


_DEFAULT_SPEC = CorrelationSpec()


def build_correlation(
    players: pd.DataFrame, spec: CorrelationSpec = _DEFAULT_SPEC
) -> pd.DataFrame:
    """Assemble the per-player correlation matrix from the factor/rule structure.

    `players` needs `player_id`, `position`, `team`; `opponent` (opposing team abbr) is
    optional — without it the same-game rules (game-stack, DST ↔ opp) simply don't fire.
    Returns a P×P `DataFrame` indexed and columned by `player_id`, guaranteed a valid
    (symmetric, PSD, unit-diagonal) correlation matrix ready for Cholesky.
    """
    pid = players["player_id"].astype("string").to_numpy(dtype=object)
    pos = players["position"].astype("string").str.upper().to_numpy(dtype=object)
    team = _col(players, "team")
    opp = _col(players, "opponent", "opp", "def_team")
    n = len(pid)

    c = np.zeros((n, n), dtype=np.float64)

    is_qb = pos == "QB"
    is_rb = pos == "RB"
    is_wr = pos == "WR"
    is_te = pos == "TE"
    is_recv = np.isin(pos, list(_RECEIVERS))
    is_off = np.isin(pos, list(_OFFENSE))
    is_dst = np.isin(pos, list(_DST))

    def _apply(mask_a: npt.NDArray[np.bool_], mask_b: npt.NDArray[np.bool_],
               relation: npt.NDArray[np.bool_], coef: float) -> None:
        # symmetric pairwise assignment where (a_i & b_j & relation) or its transpose
        pair = (mask_a[:, None] & mask_b[None, :] & relation)
        pair |= pair.T
        c[pair] = coef

    if team is not None:
        same_team = team[:, None] == team[None, :]
        _apply(is_qb, is_wr, same_team, spec.qb_wr)
        _apply(is_qb, is_te, same_team, spec.qb_te)
        _apply(is_qb, is_rb, same_team, spec.qb_rb)
        _apply(is_rb, is_recv, same_team, spec.rb_receivers)
        # same team, same skill position (WR1 vs WR2 etc.) — usage competition
        same_pos = pos[:, None] == pos[None, :]
        _apply(is_off, is_off, same_team & same_pos, spec.same_pos)

    if team is not None and opp is not None:
        # i and j are opponents in the same game
        opponents = (team[:, None] == opp[None, :]) & (opp[:, None] == team[None, :])
        _apply(is_off, is_off, opponents, spec.game_stack)
        _apply(is_dst, is_off, opponents, spec.dst_opp_offense)

    np.fill_diagonal(c, 1.0)
    psd = nearest_psd_correlation(c)
    return pd.DataFrame(psd, index=pid, columns=pid)


def nearest_psd_correlation(
    matrix: npt.NDArray[np.float64], *, eps: float = 1e-8
) -> npt.NDArray[np.float64]:
    """Project a symmetric matrix to the nearest valid correlation matrix.

    Clips negative eigenvalues to `eps` (guaranteeing PSD) then rescales to a unit
    diagonal. A one-shot Higham-style projection — enough for the mildly-inconsistent
    rule matrix we build (the raw entries are already close to feasible).
    """
    a = np.asarray(matrix, dtype=np.float64)
    a = 0.5 * (a + a.T)
    vals, vecs = np.linalg.eigh(a)
    vals = np.clip(vals, eps, None)
    a = (vecs * vals) @ vecs.T
    d = np.sqrt(np.clip(np.diag(a), eps, None))
    a = a / d[:, None] / d[None, :]
    a = 0.5 * (a + a.T)
    np.fill_diagonal(a, 1.0)
    return a


def cholesky_factor(
    corr: npt.NDArray[np.float64] | pd.DataFrame, *, jitter: float = 1e-10
) -> npt.NDArray[np.float64]:
    """Lower-Cholesky factor `L` (`L @ Lᵀ = corr`) for correlated sampling.

    Adds escalating diagonal jitter on failure — a last-resort guard for a matrix that
    is PSD only up to floating-point noise. `nearest_psd_correlation` normally makes this
    a no-op.
    """
    a = corr.to_numpy(dtype=np.float64) if isinstance(corr, pd.DataFrame) else np.asarray(
        corr, dtype=np.float64
    )
    for k in range(6):
        try:
            return np.linalg.cholesky(a + np.eye(a.shape[0]) * jitter * (10.0**k))
        except np.linalg.LinAlgError:
            continue
    # final fallback: independent (identity) — degrade-neutral, never crash a publish
    return np.eye(a.shape[0])
