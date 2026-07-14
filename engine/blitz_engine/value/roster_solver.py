"""Integer-program roster solver — the structural fix for empty starters + K/DST hoarding.

Given a pool of players and a league's slot requirements, an IP (ortools CP-SAT) **selects a
roster and assigns a full legal starting lineup in one solve**:

* every starter slot (incl. FLEX / SUPERFLEX) is a *hard* constraint — an empty-starter board
  is infeasible, not merely penalized;
* K and DST are capped at 1 until the final rounds — kicker/defense hoarding is infeasible too;
* bench players are valued by expected contribution (`bench.py`), so the objective never trades
  a startable flyer for a second kicker.

Because "fill the starters" is a hard constraint and bench worth is discounted, the solver fills
legal starters *before* luxuries by construction. Slots are data (`RosterRequirements`), so the
default superflex / half-PPR snake format and any other format share one model.

The problem is tiny (~15 slots, a few dozen candidates) — it fits trivially; scalars stay
float32-friendly Python floats, scaled to ints only for the CP-SAT objective.

Ponytail: ortools owns the branch-and-bound; there is no hand-rolled search here.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from ortools.sat.python import cp_model

from blitz_engine.value.bench import default_bench_value

# Position eligibility for the composite starter slots.
FLEX_ELIGIBLE = frozenset({"RB", "WR", "TE"})
SUPERFLEX_ELIGIBLE = frozenset({"QB", "RB", "WR", "TE"})

# Default league: snake, superflex, half-PPR — the format we fix first.
DEFAULT_STARTERS: tuple[str, ...] = (
    "QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPERFLEX", "K", "DST",
)

_VALUE_SCALE = 1000  # CP-SAT is integer; scale float32 values to ints without losing order.


class InfeasibleRosterError(ValueError):
    """Raised when no legal full starting lineup can be built from the pool + constraints."""


def slot_accepts(slot: str, position: str) -> bool:
    """True if a player at ``position`` may fill starter ``slot``."""
    if slot == "FLEX":
        return position in FLEX_ELIGIBLE
    if slot in ("SUPERFLEX", "SFLX"):
        return position in SUPERFLEX_ELIGIBLE
    return slot == position


@dataclass(frozen=True)
class Player:
    """A draftable / rostered player.

    ``value`` is start-worthiness (value when started). ``bench_value``, if supplied by the
    caller (e.g. from a richer `bench.bench_value` computation with real depth/E[starts]), is
    used as the player's worth when benched; otherwise a position-scaled default is derived,
    which already zeroes a second K/DST.
    """

    id: str
    position: str
    value: float
    bye_week: int | None = None
    bench_value: float | None = None

    def worth_on_bench(self) -> float:
        if self.bench_value is not None:
            return float(self.bench_value)
        return default_bench_value(self.position, self.value)


@dataclass(frozen=True)
class RosterRequirements:
    """League slot + cap rules. Defaults = superflex, half-PPR, snake."""

    starters: tuple[str, ...] = DEFAULT_STARTERS
    bench_size: int = 6
    final_rounds: int = 2  # within this many picks of the end, the K/DST cap lifts
    k_late_cap: int = 2
    dst_late_cap: int = 2

    @property
    def roster_size(self) -> int:
        return len(self.starters) + self.bench_size

    def k_cap(self, rounds_remaining: int) -> int:
        """Max kickers allowed on the roster given rounds left (1 until the final rounds)."""
        return self.k_late_cap if rounds_remaining <= self.final_rounds else 1

    def dst_cap(self, rounds_remaining: int) -> int:
        """Max defenses allowed on the roster given rounds left (1 until the final rounds)."""
        return self.dst_late_cap if rounds_remaining <= self.final_rounds else 1


# Shared immutable default (frozen dataclass) — avoids a call in argument defaults.
_DEFAULT_REQS = RosterRequirements()


@dataclass(frozen=True)
class Lineup:
    """Result of a solve: the assigned starters + valued bench."""

    starters: tuple[tuple[str, Player], ...]  # (slot label, player), in requirement order
    bench: tuple[Player, ...]
    starter_value: float
    bench_value_total: float

    @property
    def total_value(self) -> float:
        return self.starter_value + self.bench_value_total

    @property
    def is_legal(self) -> bool:
        """Every starter slot is filled (the solver guarantees this on success)."""
        return len(self.starters) > 0 and all(p is not None for _, p in self.starters)

    def counts(self) -> dict[str, int]:
        """Rostered players per position (starters + bench) — handy for cap assertions."""
        out: dict[str, int] = {}
        for _, p in self.starters:
            out[p.position] = out.get(p.position, 0) + 1
        for p in self.bench:
            out[p.position] = out.get(p.position, 0) + 1
        return out


def solve_roster(
    pool: Sequence[Player],
    requirements: RosterRequirements = _DEFAULT_REQS,
    *,
    rounds_remaining: int = 99,
    forced_ids: Iterable[str] = (),
    week: int | None = None,
) -> Lineup:
    """Select a roster from ``pool`` and assign a full legal starting lineup, in one IP solve.

    Args:
        pool: Candidate players (owned + available).
        requirements: Slot layout, bench size, and K/DST cap rule.
        rounds_remaining: Draft rounds left; the K/DST cap lifts within ``final_rounds``.
        forced_ids: Player ids that must be rostered (already drafted).
        week: If given, players on their bye that week cannot fill a starter slot.

    Returns:
        The optimal `Lineup` (starters filled, remaining picks benched).

    Raises:
        InfeasibleRosterError: No legal full starting lineup exists under these constraints.
    """
    return _build_and_solve(
        pool,
        requirements,
        rounds_remaining=rounds_remaining,
        forced_ids=forced_ids,
        week=week,
        enforce_pos_caps=True,
    )


def optimize_lineup(
    roster: Sequence[Player],
    requirements: RosterRequirements = _DEFAULT_REQS,
    *,
    week: int | None = None,
) -> Lineup:
    """Assign the best legal starting lineup from an *owned* roster (no selection, no caps).

    Every player in ``roster`` is kept; the solver only decides who starts vs. sits, honoring
    FLEX/SUPERFLEX eligibility and (optionally) byes. Use `solve_roster` for draft selection.

    Raises:
        InfeasibleRosterError: The roster cannot field a legal full lineup (too few / wrong
            positions).
    """
    reqs = replace(
        requirements,
        bench_size=max(0, len(roster) - len(requirements.starters)),
    )
    forced = tuple(p.id for p in roster)
    return _build_and_solve(
        roster,
        reqs,
        rounds_remaining=0,
        forced_ids=forced,
        week=week,
        enforce_pos_caps=False,
    )


def _build_and_solve(
    pool: Sequence[Player],
    requirements: RosterRequirements,
    *,
    rounds_remaining: int,
    forced_ids: Iterable[str],
    week: int | None,
    enforce_pos_caps: bool,
) -> Lineup:
    model = cp_model.CpModel()
    slots = list(enumerate(requirements.starters))  # [(0, "QB"), (1, "RB"), ...]

    # start[i, s] : player i fills starter slot s. Only created where eligible & not on bye.
    start: dict[tuple[int, int], cp_model.IntVar] = {}
    for i, p in enumerate(pool):
        if week is not None and p.bye_week == week:
            continue
        for s_idx, slot in slots:
            if slot_accepts(slot, p.position):
                start[i, s_idx] = model.new_bool_var(f"start_{i}_{s_idx}")

    bench = {i: model.new_bool_var(f"bench_{i}") for i in range(len(pool))}

    def player_starts(i: int) -> list[cp_model.IntVar]:
        return [start[i, s_idx] for s_idx, _ in slots if (i, s_idx) in start]

    # Every starter slot is filled by exactly one player -> a FULL legal lineup (hard).
    for s_idx, slot in slots:
        candidates = [start[i, s_idx] for i in range(len(pool)) if (i, s_idx) in start]
        if not candidates:
            raise InfeasibleRosterError(
                f"no pool player can fill starter slot {slot!r} (index {s_idx})"
            )
        model.add_exactly_one(candidates)

    # A player starts in at most one slot, and cannot both start and sit on the bench.
    for i in range(len(pool)):
        starts_i = player_starts(i)
        if starts_i:
            model.add(sum(starts_i) <= 1)
            model.add(sum(starts_i) + bench[i] <= 1)

    # Bench capacity.
    model.add(sum(bench.values()) <= requirements.bench_size)

    def rostered(i: int) -> cp_model.LinearExpr:
        return sum(player_starts(i)) + bench[i]

    # K / DST caps on the whole roster — this makes hoarding structurally impossible.
    if enforce_pos_caps:
        caps = (
            ("K", requirements.k_cap(rounds_remaining)),
            ("DST", requirements.dst_cap(rounds_remaining)),
        )
        for pos, cap in caps:
            idxs = [i for i, p in enumerate(pool) if p.position == pos]
            if idxs:
                model.add(sum(rostered(i) for i in idxs) <= cap)

    # Forced (already-drafted) players must be rostered.
    fset = set(forced_ids)
    for i, p in enumerate(pool):
        if p.id in fset:
            model.add(rostered(i) == 1)

    # Objective: starter value (dominant) + discounted bench worth.
    terms: list[cp_model.LinearExpr] = []
    for i, p in enumerate(pool):
        sv = int(round(p.value * _VALUE_SCALE))
        for s_idx, _ in slots:
            if (i, s_idx) in start:
                terms.append(sv * start[i, s_idx])
        bv = int(round(p.worth_on_bench() * _VALUE_SCALE))
        terms.append(bv * bench[i])
    model.maximize(sum(terms))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise InfeasibleRosterError(
            "no legal lineup under the given slot / cap / bye constraints"
        )

    return _extract_lineup(pool, slots, start, bench, solver)


def _extract_lineup(
    pool: Sequence[Player],
    slots: list[tuple[int, str]],
    start: dict[tuple[int, int], cp_model.IntVar],
    bench: dict[int, cp_model.IntVar],
    solver: cp_model.CpSolver,
) -> Lineup:
    starters: list[tuple[str, Player]] = []
    starter_value = 0.0
    for s_idx, slot in slots:
        for i, p in enumerate(pool):
            if (i, s_idx) in start and solver.Value(start[i, s_idx]):
                starters.append((slot, p))
                starter_value += p.value
                break
    bench_players = tuple(
        pool[i] for i in range(len(pool)) if solver.Value(bench[i])
    )
    bench_total = sum(p.worth_on_bench() for p in bench_players)
    return Lineup(
        starters=tuple(starters),
        bench=bench_players,
        starter_value=float(starter_value),
        bench_value_total=float(bench_total),
    )
