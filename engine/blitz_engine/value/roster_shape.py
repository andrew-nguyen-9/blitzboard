"""E6 — bench positional *bounds*, derived against the E5 metric (never hand-set).

The v4 draft policy hand-set `overfillDepth {QB:3, RB:5, WR:5, TE:2, K:1, DST:1}` with a flat
`overfillPenaltyPerExtra: 25` and a constant `kdstCapRoundsFromEnd: 2`. This module replaces all
of that with numbers *measured* from `simulation.season_eval` — the imperfect-information
evaluator whose score is `SeasonEvalResult.started_points` (points a LOCKED lineup actually
scored). Nothing here ever touches the retired hindsight metric.

## The experiment

For each arm (a candidate bench shape) we run **two mirrored half-leagues**: in the first, half the
seats play the arm and half play the FILLER baseline (a bench of best-available skill bodies, no
positional intent); in the second the halves swap. `draft_league` shuffles `seat_policy` with the
same permutation both times, so every seat plays the arm in exactly one run and the baseline in the
other, and the paired per-seat difference cancels the snake-draft-slot effect exactly — the same
construct e5's own bench-insurance ablation uses. Arms travel as the seat's "policy" string
(`shape_pick_fn`) and come back out of `SeasonEvalResult.seat_policy`. Starters are drafted
identically in every arm, so a measured delta is a pure BENCH effect. Only half the league runs the
arm, so it is priced as a deviation against a normal board, not in a degenerate equilibrium.

* marginal value of the Nth body at P = `v(N at P) - v(N-1 at P)`, both vs. the filler baseline;
* **bounds**, not a point: `lo` is the deepest body whose own marginal value clears one standard
  error, `hi` the deepest depth still within one standard error of the best. e8b turns these into a
  grid-wide invariant, and a hard single integer would make that invariant brittle.
* K/DST timing rides the same machinery: `kdst_at:<c>` arms take K/DST as soon as `c` rounds
  remain; the argmax over `c` IS `kdstCapRoundsFromEnd` and the curve's slope IS the soft penalty
  (started points per round too early), so neither is a constant any more.
* `ablate(row)` is the block-release gate: the derived numbers (`e6` preset) head to head against
  v4's hand-set `overfillDepth` + `kdstCapRoundsFromEnd: 2` (`v4` preset).

## Public surface (e8b asserts on `bench_bounds`)

    bench_bounds(row) -> BenchBounds        # (lo, hi) per position, for ANY of the 432 rows
    kdst_timing(row)  -> KdstTiming         # cap_rounds_from_end + soft_penalty
    to_requirements(row) -> RosterRequirements   # the roster_solver consumer

`bench_bounds` reads `fixtures/bench_shape.json`, produced by the single documented entry point
`python -m blitz_engine.value.roster_shape` (seeded; `--full` sweeps `matrix.all()`, default is
`matrix.smoke()`). Rows that were measured return `measured=True`; every other row is
*interpolated* from the measured neighbours (documented as interpolation, never as measurement).

Ponytail: no fitting library, no search — the "fit" is an argmax over a measured curve.
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.value.roster_solver import RosterRequirements

#: Positions a bench can hold, in a stable order.
BENCH_POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE", "K", "DST")

#: Positions the FILLER baseline draws from (best-available skill body, no positional intent).
FILLER_POSITIONS: tuple[str, ...] = ("RB", "WR", "TE")

#: Derivation seed — the same one e5/e7b use, so the whole chain is one seed.
SHAPE_SEED = 20260825

#: Deepest bench body priced per position (cost discipline; deeper is never optimal in practice).
MAX_DEPTH: dict[str, int] = {"QB": 3, "RB": 5, "WR": 5, "TE": 3, "K": 2, "DST": 2}

#: `kdst_at:<c>` arms — take K/DST as soon as `c` rounds remain (never before). The natural
#: projection-ordered draft already takes them last, so the arm that *forces* them EARLIER is the
#: one that prices the timing; the argmax over `c` is the derived cap.
KDST_HOLD_ARMS: tuple[int, ...] = (2, 3, 4, 6, 9, 13)

_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "bench_shape.json"
_C02C_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "fixtures" / "bench_shape_c02c.json"
)
#: The v4 hand-set constants this unit replaces (`frontend/lib/draftAI.ts` DEFAULT_POLICY) — kept
#: ONLY as the control arm of the block-release ablation. Never used as an answer.
V4_OVERFILL_DEPTH: dict[str, int] = {"QB": 3, "RB": 5, "WR": 5, "TE": 2, "K": 1, "DST": 1}
V4_KDST_CAP_ROUNDS_FROM_END = 2

#: Evidence bar for a bench FLOOR (hard constraint, 2 sigma) vs a CEILING (soft, 1 sigma).
FLOOR_SIGMA = 2.0

_BASELINE = "filler"
_GOLDEN_YEAR = 2024
_ROW_KEYS = ("id", "teams", "qb_mode", "scoring", "te_premium", "bench_slots", "ir_slots")


# ── shapes as pick-policy strings ──────────────────────────────────────────────────────


def shape_key(position: str, depth: int) -> str:
    """The arm name for `depth` bench bodies at `position` (`filler` for the baseline)."""
    return _BASELINE if depth <= 0 else f"{position}:{depth}"


def parse_shape(key: str) -> dict[str, int]:
    """Bench demand implied by an arm name. Unknown/`filler`/`kdst_hold:*` -> no demand."""
    if ":" not in key or key.startswith("kdst_at") or key.startswith("bye_"):
        return {}
    pos, _, depth = key.partition(":")
    return {pos: int(depth)} if pos in BENCH_POSITIONS else {}


@dataclass(frozen=True)
class Preset:
    """A whole bench policy as one arm: positional demand, ceilings, and K/DST timing."""

    demand: tuple[tuple[str, int], ...]  # fill in this order
    ceiling: tuple[tuple[str, int], ...] = ()
    kdst_at: int | None = None

    def wants(self) -> dict[str, int]:
        return dict(self.demand)

    def caps(self) -> dict[str, int]:
        return dict(self.ceiling)


def ablation_presets(
    row: Mapping[str, Any],
    bounds: BenchBounds | None = None,
    timing: KdstTiming | None = None,
) -> dict[str, Preset]:
    """The block-release ablation arms: `v4` (hand-set constants) vs `e6` (derived numbers).

    v4's `overfillDepth` is a per-position ROSTER depth, so its implied bench demand is that depth
    minus the row's starting requirement, filled RB/WR-first the way the v4 policy's positional
    weights do. e6's arm demands its derived floors and is capped by its derived ceilings, and
    holds K/DST to the derived round instead of the hand-set 2.
    """
    bnd = bounds if bounds is not None else bench_bounds(row)
    tim = timing if timing is not None else kdst_timing(row)
    need = {p: 0 for p in BENCH_POSITIONS}
    for slot, n in row["starting_slots"].items():
        if slot in need:
            need[slot] += int(n)
    order = ("RB", "WR", "QB", "TE", "K", "DST")
    v4 = tuple(
        (p, max(0, V4_OVERFILL_DEPTH[p] - need[p])) for p in order if V4_OVERFILL_DEPTH[p] > need[p]
    )
    e6 = tuple((p, bnd.lo[p]) for p in order if bnd.lo[p] > 0)
    return {
        "v4": Preset(demand=v4, kdst_at=V4_KDST_CAP_ROUNDS_FROM_END),
        "e6": Preset(
            demand=e6,
            ceiling=tuple((p, bnd.hi[p]) for p in BENCH_POSITIONS),
            kdst_at=tim.cap_rounds_from_end,
        ),
    }


def shape_pick_fn(presets: Mapping[str, Preset] | None = None) -> Any:
    """A `draft_league` `pick_fn` whose *arm* is the seat's `policy` string.

    Starters are chosen identically in every arm — best projected body at an unmet starting slot,
    then best skill body for the flex slots — so the arms are matched on starters and differ only
    on the BENCH, exactly like e5's acceptance construct. Bench picks then satisfy the arm's
    positional demand, falling back to the filler (best-available skill body).

    Arms understood: `filler`, `<POS>:<n>`, `kdst_at:<c>`, `bye_spread`, `bye_cluster`, plus any
    name in `presets` (a whole bench policy at once — see `ablation_presets`).
    """
    named = dict(presets or {})
    from blitz_engine.simulation.season_eval import (  # lazy: value <- simulation cycle
        SeasonPlayer,
        _roster_counts,
        _starting_needs,
        slot_positions,
    )

    def pick(
        policy: str,
        roster: list[SeasonPlayer],
        board: list[SeasonPlayer],
        slots: Mapping[str, int],
        rounds: int,
        rates: Mapping[str, float],
        top_k: int = 40,
    ) -> SeasonPlayer:
        need = _starting_needs(slots)
        counts = _roster_counts(roster)
        unmet = {p: n - counts.get(p, 0) for p, n in need.items() if counts.get(p, 0) < n}
        flex = sum(int(n) for slot, n in slots.items() if len(slot_positions(slot)) > 1)
        starters = sum(int(n) for n in slots.values())
        rounds_left = rounds - len(roster)

        preset = named.get(policy)

        # ── K/DST timing: the ONE knob the `kdst_at:<c>` arms move ──
        at = int(policy.split(":")[1]) if policy.startswith("kdst_at:") else None
        if preset is not None:
            at = preset.kdst_at
        if at is not None:
            late = {p: n for p, n in unmet.items() if p in ("K", "DST")}
            if late and rounds_left <= max(at, sum(late.values())):
                # the arm's round has arrived (or time is up): take the K/DST now
                got = [p for p in board if p.position in late]
                if got:
                    return got[0]
            unmet = {p: n for p, n in unmet.items() if p not in ("K", "DST")}

        # ── starters: identical in every arm ──
        if unmet or len(roster) < starters - flex:
            pool = [p for p in board if p.position in unmet] or board
            return pool[0]
        if len(roster) < starters:  # flex slots: best available skill body
            return next((p for p in board if p.position in FILLER_POSITIONS), board[0])

        # ── bench: the arm's positional demand, then filler ──
        demand = preset.wants() if preset is not None else parse_shape(policy)
        for pos, want in demand.items():
            if counts.get(pos, 0) - need.get(pos, 0) < want:
                got = next((p for p in board if p.position == pos), None)
                if got is not None:
                    return got
        caps = preset.caps() if preset is not None else {}
        window = [
            p
            for p in board
            if p.position in FILLER_POSITIONS
            and counts.get(p.position, 0) - need.get(p.position, 0) < caps.get(p.position, 99)
        ][:top_k] or board[:top_k]
        if policy in ("bye_spread", "bye_cluster"):
            byes = {p.bye_week for p in roster[:starters]}
            best = window[0].projection
            band = [p for p in window if p.projection >= 0.9 * best] or window[:1]
            want_shared = policy == "bye_cluster"
            match = [p for p in band if (p.bye_week in byes) is want_shared]
            return (match or band)[0]
        return window[0]

    return pick


# ── the measurement ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ArmResult:
    """One arm's paired advantage over the filler baseline, in started points per season."""

    arm: str
    delta: float  # mean paired difference vs. the baseline
    stderr: float
    p_value: float
    n_pairs: int


@dataclass(frozen=True)
class ShapeStudy:
    """Everything one row's derivation measured — the audit trail behind its bounds."""

    row_id: str
    bench_slots: int
    arms: dict[str, ArmResult]

    def value(self, position: str, depth: int) -> float:
        """Cumulative value of `depth` bodies at `position` vs. the filler baseline."""
        if depth <= 0:
            return 0.0
        arm = self.arms.get(shape_key(position, depth))
        return 0.0 if arm is None else arm.delta

    def stderr(self, position: str, depth: int) -> float:
        arm = self.arms.get(shape_key(position, depth))
        return 0.0 if arm is None else arm.stderr

    def marginal(self, position: str) -> list[float]:
        """Marginal value of the 1st, 2nd, ... body at `position` (the curve, in order)."""
        depths = [
            d for d in range(1, MAX_DEPTH.get(position, 3) + 1)
            if shape_key(position, d) in self.arms
        ]
        return [self.value(position, d) - self.value(position, d - 1) for d in depths]


def _arm_menu(row: Mapping[str, Any]) -> list[str]:
    bench = int(row["bench_slots"])
    arms = [_BASELINE]
    for pos in BENCH_POSITIONS:
        for depth in range(1, min(MAX_DEPTH[pos], bench) + 1):
            arms.append(shape_key(pos, depth))
    arms += [f"kdst_at:{c}" for c in KDST_HOLD_ARMS if c < roster_size(row)]
    arms += ["bye_spread", "bye_cluster"]
    return arms


def measure(
    row: Mapping[str, Any],
    *,
    year: int = _GOLDEN_YEAR,
    n_seasons: int = 12,
    seed: int = SHAPE_SEED,
    arms: Sequence[str] | None = None,
    baseline: str = _BASELINE,
    presets: Mapping[str, Preset] | None = None,
    players: Any = None,
) -> ShapeStudy:
    """Price every arm of `row`'s menu against the E5 metric. Deterministic in `seed`.

    **Mirrored half-league design.** For each arm we run two leagues: in the first, half the seats
    play the arm and half play the filler baseline; in the second the two halves swap. Because
    `draft_league` shuffles `seat_policy` with the *same* permutation for both runs (same seed,
    same list length), every seat plays the arm in exactly one run and the baseline in the other —
    so the paired difference at a seat cancels the snake-draft-slot effect exactly, the way e5's
    own acceptance ablation does. Half the league (not all of it) runs the arm, so the arm is
    priced as a deviation against a normal board rather than in a degenerate equilibrium.

    Yields `teams x n_seasons` paired observations per arm.
    """
    from blitz_engine.backtest.ablation import paired_permutation_p
    from blitz_engine.simulation import season_eval as se

    teams = int(row["teams"])
    menu = [a for a in (list(arms) if arms is not None else _arm_menu(row)) if a != baseline]
    pool = players if players is not None else se.build_players(year, row["id"])
    cfg = se.EvalConfig(n_seasons=n_seasons, seed=seed)
    pick_fn = shape_pick_fn(presets)

    out: dict[str, ArmResult] = {}
    for arm in menu:
        runs = []
        for parity in (0, 1):
            seats = [arm if i % 2 == parity else baseline for i in range(teams)]
            runs.append(
                se.evaluate_season(
                    year, row, config=cfg, policies=seats, pick_fn=pick_fn, players=pool
                )
            )
        diffs = []
        for s in range(teams):
            a_run = 0 if runs[0].seat_policy[s] == arm else 1
            if runs[1 - a_run].seat_policy[s] != baseline:
                continue  # not mirrored at this seat (defensive; the shuffle guarantees it is)
            diffs.append(runs[a_run].per_season[:, s] - runs[1 - a_run].per_season[:, s])
        if not diffs:
            continue
        d = np.concatenate(diffs)
        out[arm] = ArmResult(
            arm=arm,
            delta=float(d.mean()),
            stderr=float(d.std(ddof=1) / math.sqrt(d.size)) if d.size > 1 else 0.0,
            p_value=float(paired_permutation_p(d, seed=seed % 1000)),
            n_pairs=int(d.size),
        )
    return ShapeStudy(row_id=str(row["id"]), bench_slots=int(row["bench_slots"]), arms=out)


# ── reading bounds off the curve ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class BenchBounds:
    """Per-position bench count bounds for one league config. `lo[p] <= hi[p]` always."""

    row_id: str
    bench_slots: int
    lo: dict[str, int]
    hi: dict[str, int]
    measured: bool  # False => interpolated from measured neighbours, not simulated

    def as_pairs(self) -> tuple[tuple[str, int, int], ...]:
        """`(position, lo, hi)` triples — the form `RosterRequirements` consumes."""
        return tuple((p, self.lo[p], self.hi[p]) for p in BENCH_POSITIONS)

    def contains(self, counts: Mapping[str, int]) -> bool:
        """True if a bench's positional counts sit inside the bounds (the e8b predicate)."""
        return all(self.lo[p] <= int(counts.get(p, 0)) <= self.hi[p] for p in BENCH_POSITIONS)

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "bench_slots": self.bench_slots,
            "lo": dict(self.lo),
            "hi": dict(self.hi),
            "measured": self.measured,
        }


def bounds_from_study(study: ShapeStudy) -> BenchBounds:
    """Read bounds off each position's measured cumulative-value curve.

    * `lo` = how deep the bench MUST go: the longest run of leading bodies whose own marginal
      value clears `FLOOR_SIGMA` standard errors. A floor is a hard constraint asserted across all
      432 configs, so it carries a ~95% bar; a ceiling is soft and carries ~68%. A body the data
      cannot show is worth having never becomes a floor — that is what keeps e8b's invariant from
      being brittle.
    * `hi` = how deep it MAY go: the deepest depth whose cumulative value is still within one
      standard error of the best depth's. Past that the data says the slot is being wasted.

    `lo` is then shrunk (cheapest marginal first) until it fits the bench budget, and `hi` capped
    at the budget minus the other positions' floors.
    """
    bench = study.bench_slots
    lo: dict[str, int] = {}
    hi: dict[str, int] = {}
    for pos in BENCH_POSITIONS:
        depths = [
            d for d in range(1, min(MAX_DEPTH[pos], bench) + 1)
            if shape_key(pos, d) in study.arms
        ]
        floor = 0
        for d in depths:
            marginal = study.value(pos, d) - study.value(pos, d - 1)
            noise = max(study.stderr(pos, d), study.stderr(pos, d - 1))
            if marginal <= FLOOR_SIGMA * noise:
                break
            floor = d
        vals = {d: study.value(pos, d) for d in [0, *depths]}
        best = max(vals, key=lambda d: vals[d])
        thresh = vals[best] - study.stderr(pos, best)
        ceiling = max((d for d in vals if vals[d] >= thresh), default=0)
        lo[pos], hi[pos] = floor, max(floor, ceiling)
    return _fit_to_budget(study, lo, hi, bench)


def _fit_to_budget(
    study: ShapeStudy, lo: dict[str, int], hi: dict[str, int], bench: int
) -> BenchBounds:
    # Floors must be affordable: drop the least valuable marginal body until sum(lo) <= bench.
    while sum(lo.values()) > bench:
        pos = min(
            (p for p in BENCH_POSITIONS if lo[p] > 0),
            key=lambda p: study.value(p, lo[p]) - study.value(p, lo[p] - 1),
        )
        lo[pos] -= 1
    for pos in BENCH_POSITIONS:
        head_room = bench - (sum(lo.values()) - lo[pos])
        hi[pos] = max(lo[pos], min(hi[pos], head_room))
    return BenchBounds(
        row_id=study.row_id, bench_slots=bench, lo=lo, hi=hi, measured=True
    )


@dataclass(frozen=True)
class KdstTiming:
    """Derived K/DST draft timing: hold them until `cap_rounds_from_end` rounds remain."""

    cap_rounds_from_end: int
    soft_penalty: float  # started points lost per round of drafting K/DST too early
    measured: bool
    #: "low" when the measured cap falls outside the structurally defensible band (K/DST taken
    #: before the bench phase even starts). e5 models no K/DST STREAMING — waivers only fill a
    #: genuinely unfillable slot — so the metric over-rewards locking in a good kicker early.
    #: e10 must not ship a low-confidence cap without re-deriving under a streaming-aware eval.
    confidence: str = "high"

    def penalty_for(self, rounds_remaining: int) -> float:
        """Penalty a policy should charge for taking a K/DST with this many rounds left."""
        early = max(0, int(rounds_remaining) - self.cap_rounds_from_end)
        return float(early * self.soft_penalty)


def kdst_from_study(study: ShapeStudy) -> KdstTiming:
    """`cap_rounds_from_end` = the best hold arm; `soft_penalty` = the curve's slope per round."""
    arms = {c: study.arms[f"kdst_at:{c}"] for c in KDST_HOLD_ARMS if f"kdst_at:{c}" in study.arms}
    if not arms:
        return KdstTiming(
            cap_rounds_from_end=2, soft_penalty=0.0, measured=False, confidence="low"
        )
    best = max(arms, key=lambda c: arms[c].delta)
    # Slope: how much value is given up per round of holding BEYOND the optimum (i.e. the cost of
    # spending an early pick on K/DST is the mirror image of holding one round too few).
    worse = [c for c in arms if c < best]
    if worse:
        near = max(worse)
        slope = (arms[best].delta - arms[near].delta) / max(1, best - near)
    else:
        near = min(c for c in arms if c > best)
        slope = (arms[best].delta - arms[near].delta) / max(1, near - best)
    return KdstTiming(
        cap_rounds_from_end=int(best), soft_penalty=float(abs(slope)), measured=True
    )


# ── the fixture: measured rows + interpolation for the rest of the 432 ─────────────────


def _load_fixture() -> dict[str, Any]:
    if not _FIXTURE_PATH.exists():
        return {"rows": {}}
    return json.loads(_FIXTURE_PATH.read_text())


def _load_accepted_c02c_fixture() -> dict[str, Any]:
    if not _C02C_FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"{_C02C_FIXTURE_PATH} is missing — accepted C02C bounds cannot be preserved"
        )
    return json.loads(_C02C_FIXTURE_PATH.read_text())


def _load_bounds_fixture() -> dict[str, Any]:
    data = _load_fixture()
    return _load_accepted_c02c_fixture() if data.get("schema_version") == 2 else data


def _row_features(row: Mapping[str, Any]) -> tuple[float, float, float, float]:
    qb = {"1qb": 1.0, "superflex": 1.5, "2qb": 2.0}.get(str(row["qb_mode"]), 1.0)
    return (
        float(row["teams"]),
        qb,
        float(row["bench_slots"]),
        float(row["ir_slots"]),
    )


def bench_bounds(row: Mapping[str, Any]) -> BenchBounds:
    """**The public bounds accessor** (e8b's entry point). Never simulates.

    Measured rows come straight from `fixtures/bench_shape.json`; any other row is interpolated
    from the measured row nearest in (teams, qb_mode, bench_slots, ir_slots), rescaled to this
    row's bench budget. `BenchBounds.measured` says which you got.
    """
    data = _load_bounds_fixture()
    rows = data.get("rows", {})
    rid = str(row["id"])
    if rid in rows:
        rec = rows[rid]["bounds"]
        return BenchBounds(
            row_id=rid,
            bench_slots=int(rec["bench_slots"]),
            lo=dict(rec["lo"]),
            hi=dict(rec["hi"]),
            measured=True,
        )
    if not rows:
        raise FileNotFoundError(
            f"{_FIXTURE_PATH} is missing or empty — run "
            "`python -m blitz_engine.value.roster_shape` to derive it"
        )
    want = _row_features(row)
    scale = (1.0, 3.0, 0.5, 1.0)  # qb_mode dominates, bench_slots is rescalable so it matters least

    def dist(rec: Mapping[str, Any]) -> tuple[float, str]:
        got = _row_features(rec["row"])
        return (
            sum(s * (a - b) ** 2 for s, a, b in zip(scale, want, got, strict=True)),
            str(rec["bounds"]["row_id"]),
        )

    near = min(rows.values(), key=dist)["bounds"]
    bench = int(row["bench_slots"])
    lo = {p: min(int(near["lo"][p]), bench) for p in BENCH_POSITIONS}
    hi = {p: min(int(near["hi"][p]), bench) for p in BENCH_POSITIONS}
    study_free = _rescale(lo, hi, bench)
    return BenchBounds(
        row_id=rid, bench_slots=bench, lo=study_free[0], hi=study_free[1], measured=False
    )


def _rescale(
    lo: dict[str, int], hi: dict[str, int], bench: int
) -> tuple[dict[str, int], dict[str, int]]:
    """Shrink floors to the budget (deepest position first) and cap ceilings at the head room."""
    while sum(lo.values()) > bench:
        pos = max((p for p in BENCH_POSITIONS if lo[p] > 0), key=lambda p: (lo[p], p))
        lo[pos] -= 1
    for pos in BENCH_POSITIONS:
        head_room = bench - (sum(lo.values()) - lo[pos])
        hi[pos] = max(lo[pos], min(hi[pos], head_room))
    return lo, hi


def kdst_timing(row: Mapping[str, Any]) -> KdstTiming:
    """**Public K/DST timing accessor.** Measured rows from the fixture, else the measured mean.

    The rule is a function of roster size and league size, not a constant: the fixture stores the
    measured `cap_rounds_from_end` per row and unmeasured rows take the measured row nearest in
    roster size (`starters + bench`) and league size.
    """
    data = _load_bounds_fixture()
    rows = data.get("rows", {})
    rid = str(row["id"])
    if rid in rows and rows[rid].get("kdst"):
        rec = rows[rid]["kdst"]
        cap = int(rec["cap_rounds_from_end"])
        return KdstTiming(
            cap_rounds_from_end=cap,
            soft_penalty=float(rec["soft_penalty"]),
            measured=True,
            confidence=_kdst_confidence(row, cap),
        )
    if not rows:
        raise FileNotFoundError(
            f"{_FIXTURE_PATH} is missing or empty — run "
            "`python -m blitz_engine.value.roster_shape` to derive it"
        )
    size = roster_size(row)
    teams = float(row["teams"])

    def dist(rec: Mapping[str, Any]) -> tuple[float, str]:
        other = rec["row"]
        return (
            (_measured_roster_size(str(other["id"])) - size) ** 2
            + 0.5 * (float(other["teams"]) - teams) ** 2,
            str(rec["bounds"]["row_id"]),
        )

    near = min(rows.values(), key=dist)["kdst"]
    cap = int(near["cap_rounds_from_end"])
    return KdstTiming(
        cap_rounds_from_end=cap,
        soft_penalty=float(near["soft_penalty"]),
        measured=False,
        confidence=_kdst_confidence(row, cap),
    )


def _kdst_confidence(row: Mapping[str, Any], cap: int) -> str:
    """"high" only if the measured cap keeps K/DST inside the bench phase of the draft."""
    return "high" if cap <= int(row["bench_slots"]) + 2 else "low"


@cache
def _measured_roster_size(row_id: str) -> int:
    """Roster size of a measured row (the fixture stores shape factors, not the slot map)."""
    from blitz_engine.testing import matrix

    return roster_size(matrix.by_id(row_id))


def roster_size(row: Mapping[str, Any]) -> int:
    """Starting slots + bench slots — the row's draftable rounds."""
    return sum(int(n) for n in row["starting_slots"].values()) + int(row["bench_slots"])


# ── the roster_solver consumer ─────────────────────────────────────────────────────────


def starters_tuple(row: Mapping[str, Any]) -> tuple[str, ...]:
    """The row's starting slots as `RosterRequirements.starters` labels."""
    order = ("QB", "RB", "WR", "TE", "FLEX", "SUPERFLEX", "SFLX", "K", "DST")
    slots = row["starting_slots"]
    keys = sorted(slots, key=lambda s: order.index(s) if s in order else 99)
    return tuple(s for k in keys for s in [k] * int(slots[k]))


def to_requirements(
    row: Mapping[str, Any], bounds: BenchBounds | None = None
) -> RosterRequirements:
    """Build the solver's `RosterRequirements` for a matrix row from DERIVED numbers.

    Slot layout comes from the row; the bench positional bounds and the K/DST cap round come from
    this module's derivation instead of `RosterRequirements`' hand-set defaults.
    """
    bnd = bounds if bounds is not None else bench_bounds(row)
    timing = kdst_timing(row)
    return RosterRequirements(
        starters=starters_tuple(row),
        bench_size=int(row["bench_slots"]),
        final_rounds=int(timing.cap_rounds_from_end),
        bench_bounds=bnd.as_pairs(),
    )


# ── the entry point ────────────────────────────────────────────────────────────────────


def derive(
    row: Mapping[str, Any], **kw: Any
) -> tuple[BenchBounds, KdstTiming, ShapeStudy]:
    """Measure one row end to end. The one call that turns simulation into numbers."""
    study = measure(row, **kw)
    return bounds_from_study(study), kdst_from_study(study), study


def derive_all(
    rows: Sequence[Mapping[str, Any]], *, verbose: bool = False, **kw: Any
) -> dict[str, Any]:
    """Derive every row and return the fixture payload (also the shape of the JSON on disk)."""
    out: dict[str, Any] = {}
    for i, row in enumerate(rows):
        bounds, timing, study = derive(row, **kw)
        out[str(row["id"])] = {
            "row": {
                k: row[k]
                for k in _ROW_KEYS
            },
            "bounds": bounds.as_dict(),
            "kdst": {
                "cap_rounds_from_end": timing.cap_rounds_from_end,
                "soft_penalty": round(timing.soft_penalty, 4),
            },
            "arms": {
                a: {
                    "delta": round(r.delta, 4),
                    "stderr": round(r.stderr, 4),
                    "p": round(r.p_value, 5),
                    "n": r.n_pairs,
                }
                for a, r in sorted(study.arms.items())
            },
        }
        if verbose:
            print(f"[{i + 1}/{len(rows)}] {row['id']}  lo={bounds.lo}  hi={bounds.hi} "
                  f"kdst={timing.cap_rounds_from_end}@{timing.soft_penalty:.2f}")
    return {"version": 1, "seed": SHAPE_SEED, "year": _GOLDEN_YEAR, "rows": out}


def ablate(
    row: Mapping[str, Any],
    *,
    bounds: BenchBounds | None = None,
    timing: KdstTiming | None = None,
    **kw: Any,
) -> ArmResult:
    """Block-release gate: does the DERIVED shape beat v4's hand-set constants on the E5 metric?

    Mirrored half-league, `e6` against `v4`. A positive `delta` with a small `p_value` is the only
    evidence that licenses shipping these numbers; anything else means the unit ships nothing.
    """
    presets = ablation_presets(row, bounds, timing)
    study = measure(row, arms=["e6"], baseline="v4", presets=presets, **kw)
    return study.arms["e6"]


def main(argv: Sequence[str] | None = None) -> int:
    """`python -m blitz_engine.value.roster_shape [--full] [--out PATH]` — re-derive everything."""
    from blitz_engine.testing import matrix

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--full", action="store_true", help="sweep matrix.all() (432 rows)")
    ap.add_argument("--rows", nargs="*", help="explicit row ids (overrides --full)")
    ap.add_argument("--seasons", type=int, default=12)
    ap.add_argument("--seed", type=int, default=SHAPE_SEED)
    ap.add_argument("--out", type=Path, default=_FIXTURE_PATH)
    ns = ap.parse_args(argv)

    if ns.rows:
        rows = [matrix.by_id(r) for r in ns.rows]
    else:
        rows = matrix.all() if ns.full else matrix.smoke()
    payload = derive_all(
        rows, verbose=True, n_seasons=ns.seasons, seed=ns.seed
    )
    ns.out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"wrote {ns.out} ({len(payload['rows'])} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())


__all__ = [
    "BENCH_POSITIONS",
    "KDST_HOLD_ARMS",
    "MAX_DEPTH",
    "FLOOR_SIGMA",
    "SHAPE_SEED",
    "ArmResult",
    "BenchBounds",
    "Preset",
    "V4_KDST_CAP_ROUNDS_FROM_END",
    "V4_OVERFILL_DEPTH",
    "ablate",
    "ablation_presets",
    "KdstTiming",
    "ShapeStudy",
    "bench_bounds",
    "bounds_from_study",
    "derive",
    "derive_all",
    "kdst_from_study",
    "kdst_timing",
    "measure",
    "parse_shape",
    "roster_size",
    "shape_key",
    "shape_pick_fn",
    "starters_tuple",
    "to_requirements",
]
