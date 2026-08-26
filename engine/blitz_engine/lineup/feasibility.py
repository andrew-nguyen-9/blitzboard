"""E4 — the weekly lineup-**feasibility surface** that replaces the flat bye shave.

The old question was "how many bye conflicts does this roster have?", answered with a constant
per-conflict penalty. The real question is per week: **can this roster field a legal starting
lineup in week w, and what does that week cost against the roster's own best week?**

    surface = feasibility_surface(roster, matrix_row)      # 18 x WeekFeasibility
    surface.weeks[3].legal / .expected_points / .cost_vs_baseline

Three signals feed one surface, and they are genuinely independent (see `gotchas` in the unit
note): **byes** are hard — a player on bye cannot fill a slot, enforced by the existing IP
(`optimize_lineup(..., week=w)`); **availability** is e2a's `p_startable` (P(dresses and takes
>=10 % of his team's snaps) — a snap-presence signal), read through
`AvailabilityModel`/`is_effectively_unavailable` and never hard-coded; **injury** is e3's
*clinical* event (club designation Out/Doubtful or RES/PUP/NFI), read from
`fixtures/injury_rates.json`, which carries an explicit ``"event"`` string. Because e3's event
contains no snap-presence signal, availability x injury is a product of independent factors,
not a squared one.

Expectation vs. distribution — both, from ONE chain:

* `feasibility_surface` is the **expectation**. A player's weekly weight is
  ``value x p_startable x E[playing multiplier]``, the expectation taken over the injury
  Markov chain below. `legal` here is deterministic: byes plus effectively-unavailable
  exclusions.
* `sample_surface` is the **distribution**, drawn from the *same* transition matrix — nothing
  is fitted twice. It returns per-sample weekly points and per-week P(no legal lineup), which
  the analytic surface cannot express because "is this player out" is binary in a season.

The chain (per position, states = IN0 baseline / IN1..IN6 weeks-since-return / OUT):

* onset hazard lambda = e3's ``onset_hazard_per_week``, elevated just after a return by e3's
  ``reinjury`` ratio ``1 + elevation * exp(-(k-1)/decay)``;
* recovery is geometric, its rate calibrated (one bisection, seeded by the alternating-renewal
  identity ``E[D] = rate / (lambda (1 - rate))``) so the chain's stationary P(out) reproduces
  e3's *published* ``injuryRate`` to 1e-9 — asserted in the tests. e3's number is the ground
  truth here; no duration distribution is re-derived;
* the playing multiplier is 1.0 in IN0, e3's ``return_curve[k-1]`` in IN_k, 0.0 in OUT.

The chain **starts stationary**, so a roster with no byes and no exclusions has the same
expected points every week and a zero-cost surface — byes and roster shape are then the only
things the surface measures, which is the point. Callers who know a player is hurt right now
pass `out_now=`; his rows then recover week by week.

Ponytail: legality and optimal assignment are NOT reimplemented — every week is one
`optimize_lineup` call. The week is normalised away before the solve (bye players dropped,
`bye_week` cleared), so a process-wide memo collapses weeks that share a bye set *and* repeats
across rosters inside e5's season loop: 18 weeks costs 2.1 ms warm, ~60 ms cold.
"""
from __future__ import annotations

import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.survival.availability import ZERO_AVAILABILITY_EPS, is_effectively_unavailable
from blitz_engine.value.roster_solver import (
    InfeasibleRosterError,
    Player,
    RosterRequirements,
    optimize_lineup,
)

#: Fantasy regular season the surface covers (NFL weeks 1..18).
WEEKS = 18

#: Canonical starter order — how a league site lists the slots, and the order the IP fills them.
SLOT_ORDER: tuple[str, ...] = ("QB", "RB", "WR", "TE", "FLEX", "SUPERFLEX", "K", "DST")

_RATES_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "injury_rates.json"

Row = dict[str, Any]


# -- e3's published injury dynamics ----------------------------------------------------------
@dataclass(frozen=True)
class InjuryDynamics:
    """e3's fitted clinical-injury model as this unit consumes it — read, never re-fitted.

    Everything comes from `fixtures/injury_rates.json`; nothing here is a typed constant. The
    fixture's ``"event"`` string is kept in `event` so a caller can check what it is multiplying
    by (it must say *clinical injury*, not snap-presence unavailability — otherwise multiplying
    by e2a's availability would double-count one signal).
    """

    onset: Mapping[str, float]
    rate: Mapping[str, float]
    return_curve: Mapping[str, Sequence[float]]
    elevation: float = 0.0
    decay_weeks: float = 1.0
    event: str = ""
    #: Per-position memo (mutating a dict is legal on a frozen dataclass).
    _cache: dict[Any, Any] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def load(cls, path: Path | str | None = None) -> InjuryDynamics:
        """Read the published fixture (cached)."""
        return _load_dynamics(str(path or _RATES_PATH))

    @classmethod
    def healthy(cls) -> InjuryDynamics:
        """A degenerate model with no injuries at all — for isolating bye/availability effects."""
        return cls(onset={}, rate={}, return_curve={}, event="none (injury disabled)")

    def mean_spell(self, position: str) -> float:
        """E[weeks out per spell] — the calibrated recovery rate inverted."""
        return 1.0 / self.recovery_rate(position)

    def recovery_rate(self, position: str) -> float:
        """Weekly P(return | out), calibrated so the chain reproduces e3's published rate.

        The alternating-renewal identity ``E[D] = rate / (lambda (1 - rate))`` is the starting
        point, but e3's re-injury elevation raises the *effective* onset hazard above lambda, so
        the closed form lands a few tenths of a point high. One monotone bisection on the
        recovery rate pins stationary P(out) to the published `injuryRate` exactly — e3's number
        is the ground truth this chain is fitted to, not an approximation of it.
        """
        hit = self._cache.get(("rho", position))
        if hit is not None:
            return float(hit)
        lam = float(self.onset.get(position, 0.0))
        target = float(self.rate.get(position, 0.0))
        if lam <= 0.0 or not 0.0 < target < 1.0:
            rho = 1.0
        else:
            lo, hi = 1e-6, 1.0
            for _ in range(60):
                rho = 0.5 * (lo + hi)
                if self._stationary_for(position, rho)[-1] > target:
                    lo = rho  # too much time out -> recover faster
                else:
                    hi = rho
            rho = 0.5 * (lo + hi)
        self._cache[("rho", position)] = rho
        return rho

    def transition(self, position: str, rho: float | None = None) -> np.ndarray:
        """Row-stochastic (S, S) matrix over [IN0, IN1..INk, OUT] for one week."""
        curve = list(self.return_curve.get(position, ()))
        n_ret = len(curve)
        size = n_ret + 2
        lam = float(self.onset.get(position, 0.0))
        rho = self.recovery_rate(position) if rho is None else rho
        out = size - 1
        t = np.zeros((size, size), dtype=np.float64)
        for s in range(size - 1):  # IN0 .. IN_n_ret
            ratio = 1.0 + self.elevation * np.exp(-(s - 1) / max(self.decay_weeks, 1e-9))
            hazard = min(1.0, lam * (ratio if s >= 1 else 1.0))
            nxt = s + 1 if 1 <= s < n_ret else 0
            t[s, out] = hazard
            t[s, nxt] = 1.0 - hazard
        t[out, 1 if n_ret else 0] = rho
        t[out, out] = 1.0 - rho
        return t

    def multipliers(self, position: str) -> np.ndarray:
        """Playing multiplier per state: 1.0 baseline, the return curve after a return, 0 out."""
        curve = list(self.return_curve.get(position, ()))
        return np.array([1.0, *curve, 0.0], dtype=np.float64)

    def stationary(self, position: str) -> np.ndarray:
        """Long-run state distribution — its OUT mass IS e3's published `injuryRate`."""
        hit = self._cache.get(("pi", position))
        if hit is None:
            hit = self._stationary_for(position, self.recovery_rate(position))
            self._cache[("pi", position)] = hit
        return hit

    def _stationary_for(self, position: str, rho: float) -> np.ndarray:
        t = self.transition(position, rho)
        vec = np.full(t.shape[0], 1.0 / t.shape[0])
        for _ in range(500):  # power iteration; the chain is tiny, aperiodic and irreducible
            nxt = vec @ t
            if np.abs(nxt - vec).max() < 1e-14:
                vec = nxt
                break
            vec = nxt
        return vec / vec.sum()

    def state_path(self, position: str, weeks: int, *, out_now: bool = False) -> np.ndarray:
        """(weeks, S) state distribution per week, from the stationary (or OUT) start."""
        t = self.transition(position)
        if out_now:
            vec = np.zeros(t.shape[0])
            vec[-1] = 1.0
        else:
            vec = self.stationary(position)
        path = np.empty((weeks, t.shape[0]), dtype=np.float64)
        for w in range(weeks):
            path[w] = vec
            vec = vec @ t
        return path

    def play_weight(self, position: str, weeks: int, *, out_now: bool = False) -> np.ndarray:
        """(weeks,) E[playing multiplier] — 0 while out, the return curve just after."""
        path = self.state_path(position, weeks, out_now=out_now)
        return (path @ self.multipliers(position)).astype(np.float32)

    def sample_weight(
        self,
        position: str,
        weeks: int,
        size: int,
        rng: np.random.Generator,
        *,
        out_now: bool = False,
    ) -> np.ndarray:
        """(size, weeks) sampled multipliers from the SAME chain — 0.0 means out that week."""
        t = self.transition(position)
        cdf = np.cumsum(t, axis=1)
        start = self.stationary(position)
        state = (
            np.full(size, t.shape[0] - 1)
            if out_now
            else np.searchsorted(np.cumsum(start), rng.random(size))
        )
        mult = self.multipliers(position)
        drawn = np.empty((size, weeks), dtype=np.float32)
        for w in range(weeks):
            drawn[:, w] = mult[state]
            u = rng.random(size)
            state = (u[:, None] > cdf[state]).sum(axis=1).clip(0, t.shape[0] - 1)
        return drawn


@lru_cache(maxsize=4)
def _load_dynamics(path: str) -> InjuryDynamics:
    raw = json.loads(Path(path).read_text())
    reinjury = raw.get("reinjury", {})
    return InjuryDynamics(
        onset=dict(raw.get("onset_hazard_per_week", {})),
        rate=dict(raw.get("injuryRate", {})),
        return_curve={k: list(v) for k, v in raw.get("return_curve", {}).items()},
        elevation=float(reinjury.get("elevation", 0.0)),
        decay_weeks=float(reinjury.get("decay_weeks", 1.0)),
        event=str(raw.get("event", "")),
    )


# -- league config --------------------------------------------------------------------------
def requirements_from_row(row: Row) -> RosterRequirements:
    """`RosterRequirements` for an e7a matrix row — superflex/2QB change which lineups are legal.

    `starting_slots` is the row's own derived slot count, so ``qb_mode`` is already baked into
    it (1qb -> one QB; 2qb -> two QB; superflex -> QB + a SUPERFLEX slot the IP lets any of
    QB/RB/WR/TE fill). `ir_slots` is a roster-budget field, not a lineup-legality one — see
    `FeasibilitySurface.ir_stashed`.
    """
    slots = row["starting_slots"]
    starters = tuple(
        slot for slot in (*SLOT_ORDER, *sorted(set(slots) - set(SLOT_ORDER)))
        for _ in range(int(slots.get(slot, 0)))
    )
    return RosterRequirements(starters=starters, bench_size=int(row.get("bench_slots", 6)))


# -- the surface ----------------------------------------------------------------------------
@dataclass(frozen=True)
class WeekFeasibility:
    """One week of the surface."""

    week: int
    legal: bool
    expected_points: float
    cost_vs_baseline: float
    reason: str = ""

    @property
    def is_baseline(self) -> bool:
        return self.legal and self.cost_vs_baseline == 0.0


@dataclass(frozen=True)
class FeasibilitySurface:
    """Weeks 1..N of expected legality and cost, plus the roster's own baseline week.

    `cost_vs_baseline` is **roster-relative** (baseline = this roster's best legal week), so a
    surface is comparable across league configs of different scoring or size. An illegal week
    scores 0 points and therefore costs the full baseline — maximally costly, by construction.
    """

    weeks: tuple[WeekFeasibility, ...]
    baseline: float
    excluded: tuple[str, ...] = ()
    ir_stashed: int = 0
    ir_overflow: int = 0

    def week(self, week: int) -> WeekFeasibility:
        return self.weeks[week - 1]

    @property
    def legal(self) -> bool:
        """True iff a legal lineup exists in every week."""
        return all(w.legal for w in self.weeks)

    def infeasible_weeks(self) -> tuple[int, ...]:
        return tuple(w.week for w in self.weeks if not w.legal)

    def total_cost(self) -> float:
        """Season points lost to byes / unavailability, versus the roster's own best week."""
        return float(sum(w.cost_vs_baseline for w in self.weeks))

    def points(self) -> np.ndarray:
        return np.array([w.expected_points for w in self.weeks], dtype=np.float32)

    def costs(self) -> np.ndarray:
        return np.array([w.cost_vs_baseline for w in self.weeks], dtype=np.float32)


def _availability(
    roster: Sequence[Player], availability: Mapping[str, float] | None
) -> tuple[np.ndarray, tuple[str, ...]]:
    """Per-player p_startable and the ids e2a flags as effectively unavailable.

    Values come from the caller (e2a's `AvailabilityModel().p_startable` output); the cut-off is
    e2a's own `is_effectively_unavailable`, never a number typed here. A practice-squad body now
    lands below that epsilon and is dropped outright rather than heavily discounted.
    """
    probs = np.array(
        [float((availability or {}).get(p.id, 1.0)) for p in roster], dtype=np.float32
    )
    excluded = tuple(
        p.id for p, q in zip(roster, probs, strict=True) if is_effectively_unavailable(float(q))
    )
    return probs, excluded


def _weekly_weights(
    roster: Sequence[Player],
    injury: InjuryDynamics,
    weeks: int,
    out_now: Collection[str],
) -> np.ndarray:
    """(n_players, weeks) float32 E[playing multiplier], one chain solve per (position, state)."""
    cache: dict[tuple[str, bool], np.ndarray] = {}
    rows = []
    for p in roster:
        key = (p.position, p.id in out_now)
        if key not in cache:
            cache[key] = injury.play_weight(p.position, weeks, out_now=key[1])
        rows.append(cache[key])
    return np.array(rows, dtype=np.float32).reshape(len(roster), weeks)


def feasibility_surface(
    roster: Sequence[Player],
    row: Row | RosterRequirements | None = None,
    *,
    availability: Mapping[str, float] | None = None,
    injury: InjuryDynamics | None = None,
    out_now: Collection[str] = (),
    weeks: int = WEEKS,
) -> FeasibilitySurface:
    """The **expected** feasibility surface for one roster under one league config.

    Args:
        roster: The owned players (`value` = points when started, `bye_week` honoured hard).
        row: An e7a matrix row, a ready `RosterRequirements`, or None for the engine default.
        availability: player_id -> e2a `p_startable`. Missing ids default to 1.0; ids below
            e2a's `ZERO_AVAILABILITY_EPS` are excluded from the pool, which can make a week
            genuinely infeasible rather than merely expensive.
        injury: e3's published dynamics; defaults to `InjuryDynamics.load()`. Pass
            `InjuryDynamics.healthy()` to isolate byes.
        out_now: Ids known to be injured today — their chain starts in OUT and recovers.
        weeks: Surface length (default 18).

    Returns:
        `FeasibilitySurface` — never raises for an infeasible roster; the week is marked
        ``legal=False`` with `expected_points` 0.0 and the full baseline as its cost.
    """
    reqs = (
        row
        if isinstance(row, RosterRequirements)
        else requirements_from_row(row) if row else RosterRequirements()
    )
    injury = injury or InjuryDynamics.load()
    probs, excluded = _availability(roster, availability)
    keep = [(p, q) for p, q in zip(roster, probs, strict=True) if p.id not in set(excluded)]
    pool = [p for p, _ in keep]
    scale = np.array([q for _, q in keep], dtype=np.float32)
    weights = _weekly_weights(pool, injury, weeks, set(out_now)) * scale[:, None]

    out: list[WeekFeasibility] = []
    for w in range(1, weeks + 1):
        legal, pts, reason = _solve_week(pool, weights[:, w - 1], reqs, w)
        out.append(WeekFeasibility(week=w, legal=legal, expected_points=pts, cost_vs_baseline=0.0,
                                   reason=reason))

    baseline = max((w.expected_points for w in out if w.legal), default=0.0)
    ir = int((row or {}).get("ir_slots", 0)) if isinstance(row, dict) else 0
    return FeasibilitySurface(
        weeks=tuple(
            replace(w, cost_vs_baseline=float(baseline - w.expected_points)) for w in out
        ),
        baseline=float(baseline),
        excluded=excluded,
        ir_stashed=min(len(excluded), ir),
        ir_overflow=max(len(excluded) - ir, 0),
    )


def _solve_week(
    pool: Sequence[Player],
    weight: np.ndarray,
    reqs: RosterRequirements,
    week: int,
) -> tuple[bool, float, str]:
    """One `optimize_lineup` call at this week's expected values.

    Legality is never reimplemented here. The week is normalised away first — players on bye
    are dropped and `bye_week` is cleared — so the memo key is just "this weighted squad", which
    means weeks sharing a bye set, and *different rosters* inside e5's season loop, hit the same
    cached solve.
    """
    weighted = tuple(
        replace(p, value=round(float(p.value) * float(m), 6), bye_week=None)
        for p, m in zip(pool, weight, strict=True)
        if p.bye_week != week
    )
    return _solve_squad(weighted, reqs)


@lru_cache(maxsize=8192)
def _solve_squad(
    squad: tuple[Player, ...], reqs: RosterRequirements
) -> tuple[bool, float, str]:
    if not squad:
        return False, 0.0, "no available players"
    try:
        lineup = optimize_lineup(squad, reqs)
    except InfeasibleRosterError as exc:
        return False, 0.0, str(exc)
    return True, float(lineup.starter_value), ""


def sample_surface(
    roster: Sequence[Player],
    row: Row | RosterRequirements | None = None,
    *,
    rng: np.random.Generator | int = 0,
    n_samples: int = 64,
    availability: Mapping[str, float] | None = None,
    injury: InjuryDynamics | None = None,
    out_now: Collection[str] = (),
    weeks: int = WEEKS,
) -> tuple[np.ndarray, np.ndarray]:
    """The **distribution** behind `feasibility_surface`, drawn from the same chain.

    Injury is binary in any one season, so a sampled week can have *no legal lineup* even when
    the expectation is comfortably legal — that risk is what e5 needs and what an expectation
    cannot carry.

    Args:
        rng: A `Generator` or a seed (deterministic).
        n_samples: Season trajectories to draw.

    Returns:
        ``(points, illegal_rate)`` — points is (n_samples, weeks) float32 with 0.0 in weeks that
        had no legal lineup; illegal_rate is (weeks,) float32, the fraction of samples in which
        the roster could not be fielded at all.
    """
    reqs = (
        row
        if isinstance(row, RosterRequirements)
        else requirements_from_row(row) if row else RosterRequirements()
    )
    injury = injury or InjuryDynamics.load()
    generator = rng if isinstance(rng, np.random.Generator) else np.random.default_rng(rng)
    probs, excluded = _availability(roster, availability)
    keep = [(p, q) for p, q in zip(roster, probs, strict=True) if p.id not in set(excluded)]
    pool = [p for p, _ in keep]
    scale = np.array([q for _, q in keep], dtype=np.float32)
    hurt = set(out_now)

    # (n_samples, weeks, n_players) sampled multipliers; 0.0 => out that week.
    draws = np.stack(
        [
            injury.sample_weight(p.position, weeks, n_samples, generator, out_now=p.id in hurt)
            for p in pool
        ],
        axis=-1,
    ).astype(np.float32) * scale[None, None, :]

    points = np.zeros((n_samples, weeks), dtype=np.float32)
    illegal = np.zeros(weeks, dtype=np.float32)
    for s in range(n_samples):
        for w in range(1, weeks + 1):
            wt = draws[s, w - 1]
            # An out player cannot fill a slot at all — drop him, don't zero-value him.
            idx = [i for i, m in enumerate(wt) if m > ZERO_AVAILABILITY_EPS]
            legal, pts, _ = _solve_week([pool[i] for i in idx], wt[idx], reqs, w)
            points[s, w - 1] = pts
            illegal[w - 1] += 0.0 if legal else 1.0
    return points, (illegal / max(n_samples, 1)).astype(np.float32)


__all__ = [
    "SLOT_ORDER",
    "WEEKS",
    "FeasibilitySurface",
    "InjuryDynamics",
    "WeekFeasibility",
    "feasibility_surface",
    "requirements_from_row",
    "sample_surface",
]
