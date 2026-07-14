"""Career-arc dynamics: a closed-form GP trend + a scalar Kalman in-season update.

True talent is a **multi-year arc** the weekly box score only nudges. We split that into
two library-simple primitives (ponytail: no MCMC, no dependency — a Cholesky solve and a
2-line filter capture the whole dynamic):

  * **GP career arc** — a Gaussian-process regression (RBF kernel) over a player's whole
    history gives a *smooth* latent-talent trajectory + its posterior uncertainty. The
    kernel length-scale = "how many games back still matter" and is **learned per position**
    by marginal likelihood (this is the model-learned *adaptive recency* the brief asks for
    — not a fixed window).
  * **Kalman in-season update** — a local-level filter over the most recent season's GP
    residuals makes the newest weeks a *gentle* update on top of the arc; its innovation is
    the player's **momentum**. The gain is set from the player's own noise ratio, so a
    steady vet is smoothed hard and a volatile one tracks faster — again learned, not fixed.

`loc`/`scale` come out on the log-opportunity scale the core's talent-prior seam consumes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve

__all__ = ["CareerArc", "fit_career_arc", "learn_lengthscale"]

_LS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)  # candidate GP length-scales (in seasons)


@dataclass(frozen=True)
class CareerArc:
    """A player's fitted talent trajectory at the projection horizon.

    Attributes:
        level:      GP posterior latent-talent mean at the latest time (log scale).
        epistemic:  GP posterior std there — high for sparse/erratic careers, the seam's
                    scale widener (proven vet ⇒ small ⇒ tight prior).
        momentum:   Kalman innovation on the newest week (recent form vs the arc; the
                    leading-form signal E2/regime read).
        n_obs:      Number of career observations (0 ⇒ rookie/unknown, handled upstream).
        gain:       Learned Kalman gain (adaptive recency — how much the latest week moved
                    the state; 0 = fully smoothed vet, →1 = tracks every week).
    """

    level: float
    epistemic: float
    momentum: float
    n_obs: int
    gain: float


def _rbf(a: np.ndarray, b: np.ndarray, ls: float, sf: float) -> np.ndarray:
    d = a[:, None] - b[None, :]
    return sf * np.exp(-0.5 * (d / ls) ** 2)


def _log_marginal(t: np.ndarray, y: np.ndarray, ls: float, sf: float, sn: float) -> float:
    """GP log marginal likelihood — the score maximised to *learn* the length-scale."""
    n = len(t)
    k = _rbf(t, t, ls, sf) + (sn + 1e-6) * np.eye(n)
    try:
        c, low = cho_factor(k)
    except np.linalg.LinAlgError:
        return -np.inf
    alpha = cho_solve((c, low), y)
    return float(-0.5 * y @ alpha - np.log(np.diag(c)).sum() - 0.5 * n * np.log(2 * np.pi))


def learn_lengthscale(
    series: list[tuple[np.ndarray, np.ndarray]], sf: float = 1.0, sn: float = 0.3
) -> float:
    """Pick the RBF length-scale maximising the *pooled* marginal likelihood over a group.

    `series` is the (time, value) pairs of every player in a position. The grid keeps it
    cheap and robust; the winner is the adaptive-recency knob shared by that position.
    """
    usable = [(t, y) for t, y in series if len(t) >= 3]
    if not usable:
        return _LS_GRID[len(_LS_GRID) // 2]
    scores = [sum(_log_marginal(t, y, ls, sf, sn) for t, y in usable) for ls in _LS_GRID]
    return _LS_GRID[int(np.argmax(scores))]


def _kalman_update(y: np.ndarray) -> tuple[float, float, float]:
    """Local-level Kalman filter → (filtered state, innovation, gain).

    Process/observation variances are estimated from the series' own successive
    differences (learned recency), so smoothing strength adapts to each player.
    """
    if len(y) == 1:
        return float(y[0]), 0.0, 0.0
    diffs = np.diff(y)
    r = max(float(np.var(diffs)) * 0.5, 1e-4)  # observation noise
    q = max(float(np.var(y)) - r, 1e-4) * 0.25  # process (talent-drift) noise
    x, p = float(y[0]), r
    gain = 0.0
    innovation = 0.0
    for obs in y[1:]:
        p += q
        gain = p / (p + r)
        innovation = float(obs) - x
        x += gain * innovation
        p *= 1 - gain
    return x, innovation, gain


def fit_career_arc(
    t: np.ndarray, y: np.ndarray, *, lengthscale: float, sf: float = 1.0, sn: float = 0.3
) -> CareerArc:
    """Fit the GP trend + Kalman nudge for one player and read them at the latest time.

    Degrades gracefully: empty ⇒ neutral zero arc; a single game ⇒ a heavily-shrunk point.
    """
    t = np.asarray(t, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    n = len(t)
    if n == 0:
        return CareerArc(level=0.0, epistemic=1.0, momentum=0.0, n_obs=0, gain=0.0)

    t_star = float(t.max())
    k = _rbf(t, t, lengthscale, sf) + (sn + 1e-6) * np.eye(n)
    c, low = cho_factor(k)
    alpha = cho_solve((c, low), y)
    ks = _rbf(np.array([t_star]), t, lengthscale, sf)[0]  # (n,)
    gp_mean = float(ks @ alpha)
    v = cho_solve((c, low), ks)
    gp_var = max(sf - float(ks @ v), 1e-4)

    # Kalman on the most-recent season's residuals about the arc → gentle nudge + momentum
    resid = y - (_rbf(t, t, lengthscale, sf) @ alpha)
    recent = resid[-min(n, 20):]
    nudge, momentum, gain = _kalman_update(recent)

    return CareerArc(
        level=gp_mean + 0.5 * nudge,  # arc dominates; the in-season nudge is gentle
        epistemic=float(np.sqrt(gp_var)),
        momentum=momentum,
        n_obs=n,
        gain=gain,
    )
