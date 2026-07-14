"""Regime labelling: a tiny Gaussian HMM over week-to-week talent deltas.

Four latent states describe *where a career is right now* — the label E2-survival reads to
condition its hazard, and a leading indicator for the projection:

    breakout · steady · decline · hurt

There is no `hmmlearn` in the engine's dependency set, so this is a compact hand-rolled
Gaussian-emission HMM with a **Viterbi** decode (ponytail: the whole regime layer is one
DP loop). Emission means are fixed on the *standardised* delta scale — a strong positive
trend reads as breakout, a sharp collapse to a low level as hurt — and the transition
matrix is persistence-biased so a single noisy week cannot flip the regime. This keeps the
labels stable and deterministic on the short sequences fantasy careers actually give us.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["REGIMES", "RegimeFeatures", "label_regime"]

REGIMES = ("breakout", "steady", "decline", "hurt")

# emission means/stds over the per-week talent-z delta (hurt also keys off a low level)
_EMIT_MU = np.array([0.5, 0.0, -0.5, -1.2])
_EMIT_SD = np.array([0.4, 0.35, 0.4, 0.6])
# persistence-biased transition matrix (rows: from-state, cols: to-state)
_TRANS = np.array([
    [0.65, 0.22, 0.08, 0.05],  # breakout → mostly steady next
    [0.18, 0.62, 0.14, 0.06],  # steady is sticky
    [0.06, 0.20, 0.60, 0.14],  # decline
    [0.10, 0.15, 0.15, 0.60],  # hurt is sticky (injury lingers)
])
_START = np.array([0.22, 0.40, 0.22, 0.16])


@dataclass(frozen=True)
class RegimeFeatures:
    """Leading-indicator features behind a regime label (E2 hazard inputs).

    Attributes:
        label:      Current regime name (last decoded state).
        slope:      Recent linear trend of the talent signal (form direction).
        volatility: Std of recent deltas (instability — a hazard leading indicator).
        level:      Latest standardised talent level (low ⇒ workload/role at risk).
    """

    label: str
    slope: float
    volatility: float
    level: float


def _viterbi(obs: np.ndarray) -> int:
    """Return the final decoded state index for a standardised-delta sequence."""
    log_t = np.log(_TRANS)
    log_p = np.log(_START) + _emit_logprob(obs[0])
    for o in obs[1:]:
        log_p = (log_p[:, None] + log_t).max(axis=0) + _emit_logprob(o)
    return int(np.argmax(log_p))


def _emit_logprob(x: float) -> np.ndarray:
    return -0.5 * ((x - _EMIT_MU) / _EMIT_SD) ** 2 - np.log(_EMIT_SD)


def label_regime(values: np.ndarray) -> RegimeFeatures:
    """Decode the current regime + leading indicators from a talent-signal sequence.

    `values` is one player's standardised talent signal over time (oldest→newest). Short
    or flat histories degrade to `steady` with zeroed features — never raises.
    """
    v = np.asarray(values, dtype=np.float64).ravel()
    if len(v) < 2:
        return RegimeFeatures(label="steady", slope=0.0, volatility=0.0,
                              level=float(v[-1]) if len(v) else 0.0)

    deltas = np.diff(v)
    state = _viterbi(deltas)

    level = float(v[-1])
    # a genuine collapse to a low level overrides a borderline decline → hurt
    if state == 2 and level < -1.0 and deltas[-1] < -1.0:
        state = 3

    x = np.arange(len(v), dtype=np.float64)
    slope = float(np.polyfit(x, v, 1)[0])
    return RegimeFeatures(
        label=REGIMES[state], slope=slope, volatility=float(np.std(deltas)), level=level
    )
