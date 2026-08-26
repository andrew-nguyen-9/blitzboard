"""Arm execution and matched-pair validation for the C05 promotion protocol.

An `ArmRun` is one arm's evaluation of one `(year, league_id, base_seed)` slice, serialisable so
the two arms can be produced by two different checkouts (v5 at the baseline SHA, v6 at the frozen
candidate SHA) and analysed offline. `validate_pair` enforces the preregistered common-random-
number contract — identical board, seats and seeds — and every analysis entry point calls it
BEFORE touching a number, so a mismatched pair can never contaminate a statistic.
"""
from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
import zlib
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

__all__ = [
    "ArmRun",
    "HeldOutGuard",
    "HeldOutLeakError",
    "NondeterminismError",
    "PairingError",
    "PromotionError",
    "assert_deterministic",
    "board_fingerprint",
    "derive_eval_seed",
    "pair_slice",
    "run_arm",
    "validate_pair",
]


class PromotionError(RuntimeError):
    """Base for every protocol violation — all of them abort the experiment, never degrade it."""


class PairingError(PromotionError):
    """The two arms are not the preregistered matched pair (board/seat/seed/config mismatch)."""


class HeldOutLeakError(PromotionError):
    """Held-out season data was requested outside the confirm stage."""


class NondeterminismError(PromotionError):
    """Two identical invocations produced different results."""


def derive_eval_seed(base_seed: int, year: int, league_id: str) -> int:
    """The preregistered per-slice seed: `base_seed + crc32(f"{year}/{league_id}") % 1_000_000`."""
    return int(base_seed) + zlib.crc32(f"{year}/{league_id}".encode()) % 1_000_000


def board_fingerprint(players: Any) -> str:
    """sha256 of the draft board identity: `(player_id, position, projection)` in board order."""
    rows = [
        (p.player_id, p.position, float(p.projection))
        for p in sorted(players, key=lambda p: (-p.projection, p.player_id))
    ]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


@dataclass(frozen=True)
class ArmRun:
    """One arm × one slice. `per_season` is the paired `(n_seasons, teams)` points matrix."""

    arm: str
    policy_sha: str
    year: int
    league_id: str
    base_seed: int
    eval_seed: int
    board_hash: str
    seat_policy: tuple[str, ...]
    per_season: tuple[tuple[float, ...], ...]
    h2h_win_rate: tuple[float, ...]
    playoff_proxy: tuple[float, ...] | None = None  # C02 deliverable; None until it lands
    championship_proxy: tuple[float, ...] | None = None
    runtime_s: float = 0.0
    max_rss_mb: float = 0.0
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ArmRun:
        d = dict(d)
        for k in ("seat_policy", "h2h_win_rate", "playoff_proxy", "championship_proxy"):
            if d.get(k) is not None:
                d[k] = tuple(d[k])
        d["per_season"] = tuple(tuple(row) for row in d["per_season"])
        return cls(**d)

    @property
    def slice_key(self) -> str:
        return f"{self.year}/{self.league_id}/{self.base_seed}"


_PAIR_FIELDS = ("year", "league_id", "base_seed", "eval_seed", "board_hash", "seat_policy")


def validate_pair(candidate: ArmRun, control: ArmRun) -> None:
    """Enforce the CRN contract; raises `PairingError` before any statistic can be computed."""
    for f in _PAIR_FIELDS:
        a, b = getattr(candidate, f), getattr(control, f)
        if a != b:
            raise PairingError(f"{f} mismatch: candidate={a!r} control={b!r}")
    if candidate.arm == control.arm and candidate.policy_sha == control.policy_sha:
        raise PairingError("arms are identical — nothing is being compared")
    a_shape = np.asarray(candidate.per_season, dtype=float).shape
    b_shape = np.asarray(control.per_season, dtype=float).shape
    if a_shape != b_shape:
        raise PairingError(f"per_season shape mismatch: {a_shape} vs {b_shape}")
    want = derive_eval_seed(candidate.base_seed, candidate.year, candidate.league_id)
    if want != candidate.eval_seed:
        raise PairingError("eval_seed does not follow the preregistered derivation formula")


def pair_slice(candidate: ArmRun, control: ArmRun) -> dict[str, Any]:
    """Validated per-slice paired deltas — the ONLY door from arm runs into the analysis."""
    from blitz_engine.promotion.stats import seat_deltas

    validate_pair(candidate, control)
    cand = np.asarray(candidate.per_season, dtype=float)
    ctrl = np.asarray(control.per_season, dtype=float)
    out: dict[str, Any] = {
        "slice_key": candidate.slice_key,
        "year": candidate.year,
        "league_id": candidate.league_id,
        "base_seed": candidate.base_seed,
        "synthetic": candidate.synthetic or control.synthetic,
        "started_points": seat_deltas(cand, ctrl),
        "h2h_win_rate": np.asarray(candidate.h2h_win_rate, dtype=float)
        - np.asarray(control.h2h_win_rate, dtype=float),
    }
    for k in ("playoff_proxy", "championship_proxy"):
        a, b = getattr(candidate, k), getattr(control, k)
        out[k] = None if a is None or b is None else np.asarray(a, float) - np.asarray(b, float)
    return out


class HeldOutGuard:
    """Mechanical held-out separation: fit-stage code cannot even read a held-out year.

    Every access is logged so the receipts prove when the held-out data was first touched.
    """

    def __init__(self, fit_years: list[int], held_out_years: list[int]) -> None:
        overlap = set(fit_years) & set(held_out_years)
        if overlap:
            raise HeldOutLeakError(f"years in both fit and held-out sets: {sorted(overlap)}")
        self.fit_years = tuple(fit_years)
        self.held_out_years = tuple(held_out_years)
        self.access_log: list[dict[str, Any]] = []

    def check(self, year: int, *, stage: str) -> None:
        self.access_log.append({"year": int(year), "stage": stage})
        if year in self.held_out_years and stage != "confirm":
            raise HeldOutLeakError(
                f"held-out year {year} requested during stage {stage!r}; only 'confirm' may read it"
            )
        if stage == "confirm" and year not in self.held_out_years:
            raise HeldOutLeakError(f"confirm stage may only read held-out years, got {year}")


def _max_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1e6 if sys.platform == "darwin" else rss / 1e3  # bytes on macOS, KiB on Linux


def run_arm(
    arm: str,
    policy_sha: str,
    year: int,
    row: dict[str, Any],
    base_seed: int,
    *,
    n_seasons: int,
    guard: HeldOutGuard,
    stage: str,
    policies: tuple[str, ...] | None = None,
) -> ArmRun:
    """Execute one arm × slice through the real evaluator, with runtime/memory receipts.

    The caller runs this once per arm from the arm's own checkout; the pairing fields it records
    are exactly what `validate_pair` later enforces.
    """
    from blitz_engine.simulation import season_eval as se

    guard.check(year, stage=stage)
    eval_seed = derive_eval_seed(base_seed, year, str(row["id"]))
    t0 = time.perf_counter()
    pool = se.build_players(year, str(row["id"]))
    cfg = se.EvalConfig(n_seasons=n_seasons, seed=eval_seed)
    mix = tuple(policies) if policies else se.DEFAULT_POLICY_MIX
    res = se.evaluate_season(year, row, config=cfg, policies=mix)
    return ArmRun(
        arm=arm,
        policy_sha=policy_sha,
        year=year,
        league_id=str(row["id"]),
        base_seed=int(base_seed),
        eval_seed=eval_seed,
        board_hash=board_fingerprint(pool),
        seat_policy=tuple(res.seat_policy),
        per_season=tuple(tuple(float(v) for v in r) for r in res.per_season),
        h2h_win_rate=tuple(float(v) for v in res.h2h_win_rate),
        playoff_proxy=None,  # populated once C02's paired proxies exist on SeasonEvalResult
        championship_proxy=None,
        runtime_s=time.perf_counter() - t0,
        max_rss_mb=_max_rss_mb(),
    )


def assert_deterministic(run_twice: Any) -> ArmRun:
    """Call `run_twice()` twice; identical results return the run, differing ones raise."""
    a, b = run_twice(), run_twice()
    for f in ("per_season", "h2h_win_rate", "seat_policy", "board_hash", "eval_seed"):
        if getattr(a, f) != getattr(b, f):
            raise NondeterminismError(f"repeated run differs in {f}")
    return a
