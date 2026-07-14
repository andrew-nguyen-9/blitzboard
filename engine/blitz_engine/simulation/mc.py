"""Correlated Monte-Carlo core (E3) — the memory-critical joint simulation.

Given per-player marginals (`mean`, `stdev` from the E1 `Projection.quantiles`) and the
E3 correlation matrix, this draws correlated player-week fantasy outcomes and reduces them
to the per-player draft signals: positional-finish probabilities, boom/bust rates,
median ± 95 %, and P(beats ADP).

THE constraint (docs/design/v4-engine-architecture.md §"M1 / 16 GB budget"): a publish run
is up to **1,000,000** draws and must NEVER materialise a 1M × players array. The reduction
is therefore *streaming* — draws are generated in batches (`SimConfig.batch_size`), each
batch is collapsed into integer **counters** (top-k finishes, boom/bust, ADP beats) and then
freed. Peak memory is bounded by one batch (`batch × P × float32`), independent of the total
run count; only the P×P correlation/Cholesky is unavoidable. `simulate` estimates that peak,
degrades `batch_size` to stay under budget, and flags a cloud-burst when even a floor batch
(or the P×P matrix itself) won't fit 16 GB — cloud-burst is opt-in, never the default.

Marginals are Gaussian(mean, stdev) clipped at 0 — the same summary E7 calibrates on, so
the sim is projection- and calibration-preserving (its per-player mean equals the input).

`ponytail:` numpy's vectorised `argsort` ranks a whole batch within each position at once;
the RNG is `numpy.random.Generator` — a library sampler, never a hand-rolled one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import pandas as pd

from blitz_engine.simulation.correlation import (
    CorrelationSpec,
    build_correlation,
    cholesky_factor,
)

if TYPE_CHECKING:
    from blitz_engine.projection.inference import Projection
    from blitz_engine.snapshot import Snapshot

__all__ = [
    "FINISH_RANKS",
    "INTERACTIVE_RUNS",
    "PUBLISH_RUNS",
    "SimConfig",
    "SimResult",
    "sample_correlated",
    "simulate",
    "simulate_projection",
    "to_snapshot",
]

# Adaptive-scale presets: fast interactive sweep vs. a publish-grade run.
INTERACTIVE_RUNS = 10_000
PUBLISH_RUNS = 1_000_000
# Positional-finish tiers reported per player (top-3 / top-5 / top-10 / top-12).
FINISH_RANKS: tuple[int, ...] = (3, 5, 10, 12)
# Bytes touched per draw-cell across the transient batch arrays (z, correlated, points,
# ranking scratch) — used only to *estimate* peak and pick a safe batch size.
_BYTES_PER_CELL = 5 * 4
_DEFAULT_SPEC = CorrelationSpec()


@dataclass(frozen=True)
class SimConfig:
    """Knobs for one simulation. `n_runs` is the adaptive-scale dial (10k → 1M)."""

    n_runs: int = 100_000
    batch_size: int = 10_000
    finish_ranks: tuple[int, ...] = FINISH_RANKS
    bust_frac: float = 0.5   # a "bust" is < bust_frac × projected mean
    boom_frac: float = 1.5   # a "boom" is > boom_frac × projected mean
    seed: int = 20240813
    memory_budget_bytes: int = 12 * 1024**3  # soft cap, under the 16 GB machine budget
    min_batch: int = 1_000   # smallest batch we'll degrade to before suggesting cloud-burst


_DEFAULT_CONFIG = SimConfig()


@dataclass(frozen=True)
class SimResult:
    """Per-player MC outputs + the correlation matrix that ships in the snapshot."""

    outputs: pd.DataFrame          # per-player finish/boom/bust/median/ADP signals (mc_probs)
    corr_matrix: pd.DataFrame      # the P×P correlation used (snapshot `corr_matrix` table)
    n_runs: int
    batch_size: int                # the (possibly degraded) batch actually streamed
    peak_bytes: int                # estimated peak resident bytes of the streaming reduction
    cloud_burst_suggested: bool    # True iff the run couldn't fit the budget comfortably
    within_budget: bool = field(default=True)


def sample_correlated(
    mean: npt.NDArray[np.float64],
    sd: npt.NDArray[np.float64],
    chol: npt.NDArray[np.float64],
    n: int,
    rng: np.random.Generator,
) -> npt.NDArray[np.float32]:
    """Draw `n` correlated player-point vectors (float32), clipped at 0.

    `chol` is the lower-Cholesky factor of the P×P correlation. This is the single batch
    primitive the streaming loop calls; exposed so callers/tests can pull a small draw set
    without the full reduction. Gaussian marginals ⇒ the sample correlation recovers `chol`'s
    correlation (up to the mild attenuation of the zero-clip).
    """
    p = mean.shape[0]
    z = rng.standard_normal((n, p), dtype=np.float32)
    x = z @ chol.T.astype(np.float32)
    pts = mean.astype(np.float32) + sd.astype(np.float32) * x
    np.maximum(pts, 0.0, out=pts)
    return pts


def _estimate_peak(batch: int, p: int, n_counters: int) -> int:
    """Estimated peak resident bytes: one transient batch + the P×P factor + counters."""
    return batch * p * _BYTES_PER_CELL + 2 * p * p * 8 + p * n_counters * 8


def _plan_batch(p: int, cfg: SimConfig) -> tuple[int, int, bool]:
    """Pick a batch that fits the budget; return (batch, peak_bytes, cloud_burst_suggested).

    Streaming makes peak depend on batch, not on `n_runs`, so we shrink the batch until it
    fits. If even `min_batch` (or the unavoidable P×P factor) blows the budget, we clamp and
    flag a cloud-burst — the caller may still run locally, just warned.
    """
    n_counters = len(cfg.finish_ranks) + 3
    fixed = 2 * p * p * 8 + p * n_counters * 8
    room = cfg.memory_budget_bytes - fixed
    want = min(cfg.batch_size, cfg.n_runs)
    if room <= 0:
        return max(cfg.min_batch, 1), _estimate_peak(cfg.min_batch, p, n_counters), True
    feasible = int(room // (p * _BYTES_PER_CELL))
    batch = max(cfg.min_batch, min(want, feasible))
    suggested = feasible < cfg.min_batch or batch < want
    return batch, _estimate_peak(batch, p, n_counters), suggested


def _positional_adp(
    adp: pd.Series | dict[str, float] | None, pid: npt.NDArray[np.object_]
) -> npt.NDArray[np.float64] | None:
    """Align a player_id → positional-ADP-rank map to the player order (NaN = unknown)."""
    if adp is None:
        return None
    s = pd.Series(adp) if not isinstance(adp, pd.Series) else adp
    s.index = s.index.astype(str)
    return np.array([s.get(str(x), np.nan) for x in pid], dtype=np.float64)


def simulate(
    marginals: pd.DataFrame,
    players: pd.DataFrame,
    *,
    corr: pd.DataFrame | None = None,
    spec: CorrelationSpec = _DEFAULT_SPEC,
    config: SimConfig = _DEFAULT_CONFIG,
    adp: pd.Series | dict[str, float] | None = None,
) -> SimResult:
    """Correlated MC over player-week marginals → per-player draft signals.

    `marginals`: `player_id`, `mean`, `stdev` (straight from `Projection.quantiles`).
    `players`:   `player_id`, `position`, `team`, optional `opponent` (for game-stack / DST).
    `corr`:      an explicit correlation matrix; built from `players`+`spec` when omitted.
    `adp`:       optional `player_id → positional ADP rank` for the P(beats ADP) output.

    Streams `config.n_runs` draws in memory-bounded batches, accumulating integer counters
    only. Returns a `SimResult` whose `outputs` is the per-player `mc_probs` table and whose
    `corr_matrix` is the matrix that ships in the snapshot.
    """
    meta = players.copy()
    meta["player_id"] = meta["player_id"].astype(str)
    marg = marginals.copy()
    marg["player_id"] = marg["player_id"].astype(str)
    # Align marginals onto the player universe (order = `players`).
    df = meta.merge(marg[["player_id", "mean", "stdev"]], on="player_id", how="inner")
    if df.empty:
        raise ValueError("no players in common between `marginals` and `players`")

    pid = df["player_id"].to_numpy(dtype=object)
    pos = df["position"].astype("string").str.upper().to_numpy(dtype=object)
    mean = df["mean"].to_numpy(dtype=np.float64)
    sd = np.clip(df["stdev"].to_numpy(dtype=np.float64), 1e-9, None)
    p = len(pid)

    if corr is None:
        corr = build_correlation(df, spec)
    else:
        corr = corr.loc[pid, pid]
    chol = cholesky_factor(corr)

    ranks = tuple(config.finish_ranks)
    batch, peak, burst = _plan_batch(p, config)
    rng = np.random.default_rng(config.seed)

    bust_thr = config.bust_frac * mean
    boom_thr = config.boom_frac * mean
    adp_rank = _positional_adp(adp, pid)

    # position → column indices, precomputed once (ranking is per-position)
    groups = {q: np.flatnonzero(pos == q) for q in np.unique(pos)}

    finish = np.zeros((p, len(ranks)), dtype=np.int64)
    bust = np.zeros(p, dtype=np.int64)
    boom = np.zeros(p, dtype=np.int64)
    beats = np.zeros(p, dtype=np.int64)
    adp_known = np.zeros(p, dtype=np.int64)

    done = 0
    while done < config.n_runs:
        b = min(batch, config.n_runs - done)
        pts = sample_correlated(mean, sd, chol, b, rng)
        bust += (pts < bust_thr).sum(axis=0)
        boom += (pts > boom_thr).sum(axis=0)
        for idx in groups.values():
            g = pts[:, idx]
            # 0-based rank within position, 0 = highest scorer this draw
            rank0 = (-g).argsort(axis=1).argsort(axis=1)
            for ki, k in enumerate(ranks):
                finish[idx, ki] += (rank0 < k).sum(axis=0)
            if adp_rank is not None:
                ar = adp_rank[idx]
                known = ~np.isnan(ar)
                if known.any():
                    kidx = idx[known]
                    # beat ADP = finish at least as high as the ADP-implied rank (1-based)
                    beats[kidx] += (rank0[:, known] < ar[known][None, :]).sum(axis=0)
                    adp_known[kidx] += b
        done += b

    inv = 1.0 / config.n_runs
    out = pd.DataFrame({"player_id": pid, "position": pos, "mean": mean, "stdev": sd})
    if "team" in df.columns:
        out["team"] = df["team"].to_numpy()
    # marginal median ± 95 % (Gaussian, clipped at 0 — matches the simulated marginal)
    out["median"] = np.clip(mean, 0.0, None)
    out["p2_5"] = np.clip(mean - 1.959963985 * sd, 0.0, None)
    out["p97_5"] = np.clip(mean + 1.959963985 * sd, 0.0, None)
    for ki, k in enumerate(ranks):
        out[f"top{k}"] = finish[:, ki] * inv
    out["bust_pct"] = bust * inv
    out["boom_pct"] = boom * inv
    if adp_rank is not None:
        with np.errstate(invalid="ignore", divide="ignore"):
            out["beats_adp"] = np.where(adp_known > 0, beats / np.maximum(adp_known, 1), np.nan)

    return SimResult(
        outputs=out,
        corr_matrix=corr,
        n_runs=config.n_runs,
        batch_size=batch,
        peak_bytes=peak,
        cloud_burst_suggested=burst,
        within_budget=peak <= config.memory_budget_bytes,
    )


def simulate_projection(
    projection: Projection,
    players: pd.DataFrame,
    *,
    corr: pd.DataFrame | None = None,
    spec: CorrelationSpec = _DEFAULT_SPEC,
    config: SimConfig = _DEFAULT_CONFIG,
    adp: pd.Series | dict[str, float] | None = None,
) -> SimResult:
    """Convenience: run `simulate` straight off an E1 `Projection` (its `quantiles` frame)."""
    return simulate(
        projection.quantiles, players, corr=corr, spec=spec, config=config, adp=adp
    )


def to_snapshot(projection: Projection, result: SimResult, **kw: object) -> Snapshot:
    """Assemble the full `Snapshot`: E1 values/quantiles + E3 corr_matrix + mc_probs.

    Completes `Projection.to_snapshot` (which leaves corr/mc empty) with the simulation's
    correlation matrix and per-player probabilities — the two E3 fields the frontend's live
    re-sim reads.
    """
    from blitz_engine.snapshot import Snapshot

    return Snapshot(
        values=projection.quantiles,
        quantiles=projection.quantiles,
        corr_matrix=result.corr_matrix,
        mc_probs=result.outputs,
        **kw,  # type: ignore[arg-type]
    )
