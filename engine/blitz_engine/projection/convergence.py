"""The HARD convergence gate — an unconverged fit must never publish.

A Bayesian projection is only trustworthy if the sampler actually explored the posterior.
The brief makes this a *blocking* gate (brief §"Convergence gate (HARD, gates publish)"):

    R-hat < 1.01   AND   ESS ≥ threshold   AND   0 divergences   →  else BLOCK.

* **R-hat** (split Gelman–Rubin) near 1 ⇒ chains agree — the classic non-convergence flag.
* **ESS** (effective sample size) ⇒ enough *independent* information behind each quantile;
  a tiny ESS means the floor/ceiling we publish are noise.
* **Divergences** ⇒ NUTS hit a region its step size can't integrate — the posterior
  geometry is being misrepresented; even one is a red flag for a hierarchical model.

`check` returns a `ConvergenceReport` (non-raising, for diagnostics / the Model Lab);
`gate` raises `ConvergenceError` on failure — that is what `HierarchicalProjector.fit`
calls so a bad fit can never reach a snapshot. Mirrors the `data.validation.gate` /
`ValidationError` pattern E0-ingest established (raise-to-block vs report-to-inspect).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpyro.diagnostics import effective_sample_size, split_gelman_rubin

__all__ = [
    "ConvergenceError",
    "ConvergenceReport",
    "check",
    "gate",
]

# Defaults from the brief. Tightenable per-run via `check`/`gate` kwargs.
RHAT_MAX = 1.01
ESS_MIN = 100.0
MAX_DIVERGENCES = 0


class ConvergenceError(RuntimeError):
    """Raised by `gate` when a fit fails the hard convergence criteria (blocks publish)."""


@dataclass(frozen=True)
class ConvergenceReport:
    """Per-fit convergence verdict + the offending parameters (for the Lab / logs)."""

    passed: bool
    rhat_max: float
    ess_min: float
    n_divergences: int
    rhat_max_param: str = ""
    ess_min_param: str = ""
    offenders: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "BLOCK"
        return (
            f"[{verdict}] r_hat_max={self.rhat_max:.4f} ({self.rhat_max_param}) "
            f"ess_min={self.ess_min:.0f} ({self.ess_min_param}) "
            f"divergences={self.n_divergences}"
        )


def _grouped(samples: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Keep only chain-grouped array sites (shape (chains, draws, ...))."""
    return {k: np.asarray(v) for k, v in samples.items() if np.asarray(v).ndim >= 2}


def check(
    samples: dict[str, np.ndarray],
    *,
    n_divergences: int = 0,
    rhat_max: float = RHAT_MAX,
    ess_min: float = ESS_MIN,
    max_divergences: int = MAX_DIVERGENCES,
) -> ConvergenceReport:
    """Diagnose convergence from chain-grouped posterior `samples` (never raises).

    `samples` is the dict from `MCMC.get_samples(group_by_chain=True)` — each value shaped
    (num_chains, num_draws, *event). Divergence count comes from the sampler's
    `diverging` extra field (pass it in via `n_divergences`).
    """
    grouped = _grouped(samples)
    worst_rhat, worst_rhat_p = 1.0, ""
    least_ess, least_ess_p = float("inf"), ""
    offenders: dict[str, str] = {}

    for name, arr in grouped.items():
        # split-R-hat is valid with a single chain (splits it into halves)
        with np.errstate(invalid="ignore"):
            r_arr = np.asarray(split_gelman_rubin(arr))
            e_arr = np.asarray(effective_sample_size(arr))
        r = float(np.nanmax(r_arr)) if np.isfinite(r_arr).any() else float("inf")
        e = float(np.nanmin(e_arr)) if np.isfinite(e_arr).any() else 0.0  # all-NaN ESS = fail
        if r > worst_rhat:
            worst_rhat, worst_rhat_p = r, name
        if e < least_ess:
            least_ess, least_ess_p = e, name
        if r > rhat_max:
            offenders[name] = f"r_hat={r:.4f}"
        if e < ess_min:
            offenders[name] = (offenders.get(name, "") + f" ess={e:.0f}").strip()

    if least_ess == float("inf"):
        least_ess = 0.0  # no grouped sites → treat as a failure, not a pass

    passed = (
        worst_rhat <= rhat_max
        and least_ess >= ess_min
        and n_divergences <= max_divergences
        and bool(grouped)
    )
    return ConvergenceReport(
        passed=passed,
        rhat_max=worst_rhat,
        ess_min=least_ess,
        n_divergences=int(n_divergences),
        rhat_max_param=worst_rhat_p,
        ess_min_param=least_ess_p,
        offenders=offenders,
    )


def gate(
    samples: dict[str, np.ndarray],
    *,
    n_divergences: int = 0,
    rhat_max: float = RHAT_MAX,
    ess_min: float = ESS_MIN,
    max_divergences: int = MAX_DIVERGENCES,
) -> ConvergenceReport:
    """Like `check`, but RAISES `ConvergenceError` on failure — the publish-blocking gate.

    `HierarchicalProjector.fit` calls this; a failed fit therefore cannot produce a
    snapshot. Returns the (passing) report on success so callers can log it.
    """
    report = check(
        samples,
        n_divergences=n_divergences,
        rhat_max=rhat_max,
        ess_min=ess_min,
        max_divergences=max_divergences,
    )
    if not report.passed:
        raise ConvergenceError(
            "Convergence gate BLOCKED publish — " + report.summary()
            + (f"; offenders={report.offenders}" if report.offenders else "")
        )
    return report
