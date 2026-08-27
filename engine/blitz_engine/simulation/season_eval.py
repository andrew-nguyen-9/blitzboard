"""E5 — the imperfect-information season evaluator. **The metric this cycle is tuned against.**

The retired metric (`docs/modeling/backtest-report.md`) scored a *perfect-hindsight weekly-optimal
lineup*: you "start whoever actually scored". Under it a bench can never pay, because the only
thing a bench buys is protection against not knowing — and hindsight always knows. Every v4 bench
ablation came back neutral for that reason, and that null is what this module exists to end.

**THE METRIC** (`SeasonEvalResult.started_points`, and `evaluate_season(...).metric`):

    Mean regular-season fantasy points scored by the lineup a manager LOCKED IN BEFORE each week,
    per team, over weeks 1..W of one league season, averaged over `n_seasons` sampled
    availability/injury trajectories, in a league whose seats are drafted by a documented MIX of
    policies from one pool. Population = every seat of one `fixtures/league_matrix.json` row on one
    `fixtures/seasons/<year>.json` corpus season. Horizon = the whole regular season (W = the
    corpus season's week count, no playoff bracket). Higher = the roster kept more points in the
    starting lineup once you can no longer see the future: fewer holes from injuries, byes and
    inactives, and better weekly start/sit decisions from information available at lock time.

`h2h_win_rate` is the companion metric: fraction of head-to-head weeks won against a round-robin
schedule of the *other policies*, which is only meaningful because the seats are mixed-policy.

Three seams make it honest, and each is enforced mechanically rather than by convention:

1. **Time-honest lineups.** Week `w`'s lineup is chosen from a decision frame containing only
   weeks `< w`; `backtest.harness.detect_leakage` is called on (decision, outcome) every week of
   every season, so a leaked row raises `LeakageError` instead of quietly inflating the score.
2. **Factorised production and availability.** The corpus's realised weekly points are read as
   "what he scores *if he plays*"; whether he plays is SAMPLED from e2a's availability and e3's
   clinical-injury chain (via e4's `InjuryDynamics`). Those two are independent by construction
   (e3's fixture carries an `event` string asserting zero snap-presence signal), so sampling both
   does not double-count — and history's own absences never leak into the manager's decision.
3. **Contested waivers.** A hole can be patched from a shared, finite free-agent pool in waiver
   priority order. That is what gives a bench player a real *opportunity cost*: depth that waivers
   can trivially replace is worth less than depth they cannot, and the hindsight metric could not
   see either.

`ponytail:` no framework — a week is a greedy slot fill, a season is a loop over weeks, and the
whole trajectory is three vectorised numpy draws made up front.
"""
from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from blitz_engine.backtest.harness import detect_leakage
from blitz_engine.survival.availability import (
    AvailabilityModel,
    is_effectively_unavailable,
)

if TYPE_CHECKING:
    from blitz_engine.lineup.feasibility import InjuryDynamics

# `blitz_engine.lineup.feasibility` (via `blitz_engine.value`) imports `simulation.league`, so
# importing `InjuryDynamics` at module scope here would close the cycle
# `simulation.__init__ -> season_eval -> lineup.feasibility -> value -> simulation.league`. It is
# therefore imported lazily inside the two functions that use it, same as the helpers below.

__all__ = [
    "DEFAULT_POLICY_MIX",
    "SEASON_EVAL_SEED",
    "EvalConfig",
    "SeasonEvalResult",
    "SeasonPlayer",
    "build_players",
    "draft_league",
    "evaluate_rosters",
    "evaluate_season",
    "full_sweep_enabled",
    "hindsight_points",
    "paired_ci",
    "paired_effect",
    "policy_names",
    "round_robin",
]

#: One seed drives an entire evaluation: draft seats, injury paths, availability draws and waiver
#: order all derive from it by `np.random.default_rng(seed + <stream offset>)`. Matches e7b's
#: `corpus.GOLDEN_SEED` so a golden draft and an eval of it share a lineage.
SEASON_EVAL_SEED = 20260825

_INJURY_STREAM = 101
_AVAIL_STREAM = 202
_DRAFT_STREAM = 303

#: Greedy fill order — every dedicated slot first, then flexible slots and aliases.
_SLOT_ORDER = ("QB", "RB", "WR", "TE", "K", "DST", "FLEX", "SUPERFLEX", "OP", "SFLX")

#: The documented policy mix. `static_proxy` stands in for `frontend/lib/draftAI.ts` (e10 replaces
#: it with the real TypeScript policy over the v5-architecture §5 node bridge — see gotchas).
DEFAULT_POLICY_MIX = ("static_proxy", "vorp_adp", "engine_msv")


def full_sweep_enabled() -> bool:
    """True iff `BLITZ_EVAL_FULL=1` — the flag gating `matrix.all()` behind `matrix.smoke()`."""
    return os.environ.get("BLITZ_EVAL_FULL", "") == "1"


# ── the player universe ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SeasonPlayer:
    """One draftable player, with production and availability deliberately factorised.

    `points_if_plays[w]` is what he scores in week `w` **given he plays** — the corpus's realised
    week if it exists, otherwise his own realised median game. Whether he plays is never read from
    history; it is sampled from e2a/e3. `depth_rank` is his pre-season rank within his NFL team and
    position — the signal e2a actually fitted `p_startable` on.
    """

    player_id: str
    position: str
    nfl_team: str
    bye_week: int  # 1-based; 0 = none
    points_if_plays: tuple[float, ...]
    projection: float  # pre-season SEASON total (the only pre-week-1 information)
    depth_rank: int


def build_players(year: int, row_id: str) -> list[SeasonPlayer]:
    """The e7b corpus pool for one matrix row, as `SeasonPlayer`s (projection-desc order)."""
    from blitz_engine.testing import corpus

    pool = corpus.player_pool(year, row_id)
    weeks = int(corpus.season(year)["weeks"])
    by_unit: dict[tuple[str, str], int] = {}
    out: list[SeasonPlayer] = []
    for p in pool:
        weekly = list(p["weekly_points"])[:weeks]
        weekly += [None] * (weeks - len(weekly))
        played = [float(v) for v in weekly if v is not None]
        typical = float(np.median(played)) if played else 0.0
        key = (str(p["nfl_team"]), str(p["position"]))
        by_unit[key] = by_unit.get(key, 0) + 1
        out.append(
            SeasonPlayer(
                player_id=str(p["player_id"]),
                position=str(p["position"]),
                nfl_team=str(p["nfl_team"]),
                bye_week=int(p["bye_week"] or 0),
                points_if_plays=tuple(
                    float(v) if v is not None else typical for v in weekly
                ),
                projection=float(p["projection"]),
                depth_rank=by_unit[key],
            )
        )
    return out


# ── draft policies ─────────────────────────────────────────────────────────────────────


def policy_names() -> tuple[str, ...]:
    """The policies this module can seat, in a stable order."""
    return DEFAULT_POLICY_MIX


def slot_positions(slot: str) -> frozenset[str]:
    """Positions a template slot accepts — `value.mcts`'s definition, imported lazily."""
    from blitz_engine.value.mcts import slot_positions as _sp

    return _sp(slot)


def _starting_needs(slots: Mapping[str, int]) -> dict[str, int]:
    """Minimum bodies per concrete position implied by the row's starting slots."""
    need: dict[str, int] = {}
    for slot, n in slots.items():
        pos = slot_positions(slot)
        if len(pos) == 1:
            need[next(iter(pos))] = need.get(next(iter(pos)), 0) + int(n)
    return need


def _roster_counts(roster: Sequence[SeasonPlayer]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in roster:
        counts[p.position] = counts.get(p.position, 0) + 1
    return counts


def _pick(
    policy: str,
    roster: list[SeasonPlayer],
    board: list[SeasonPlayer],
    slots: Mapping[str, int],
    rounds: int,
    injury_rate: Mapping[str, float],
    top_k: int = 24,
) -> SeasonPlayer:
    """One pick. Every policy sees the same board; they differ only in how they rank it."""
    need = _starting_needs(slots)
    counts = _roster_counts(roster)
    unmet = {pos: n - counts.get(pos, 0) for pos, n in need.items() if counts.get(pos, 0) < n}
    slots_left = rounds - len(roster)
    # Nobody may punt a starting slot: once the picks left equal the unmet starters, force them.
    forced = sum(unmet.values()) >= slots_left
    cands = [p for p in board if (not forced or p.position in unmet)][:top_k]
    if not cands:
        cands = board[:top_k]

    if policy == "vorp_adp":
        # Raw value-over-replacement: projection minus the next man up at the same position.
        return max(cands, key=lambda p: p.projection - _replacement(board, p.position))

    if policy == "engine_msv":
        # The engine seam: pick the player that most raises the best legal starting lineup.
        from blitz_engine.value.policy import marginal_starter_value

        template = _template(slots)
        values = {p.player_id: p.projection for p in [*roster, *cands]}
        positions = {p.player_id: p.position for p in [*roster, *cands]}
        value_fn = marginal_starter_value(values, positions, template)
        have = frozenset(p.player_id for p in roster)
        base = value_fn(have)
        return max(cands, key=lambda p: value_fn(have | {p.player_id}) - base)

    # static_proxy: VORP, plus positional need, plus injury/bye COVER on bench picks.
    def score(p: SeasonPlayer) -> float:
        s = p.projection - _replacement(board, p.position)
        if p.position in unmet:
            s *= 1.0 + 0.25 * unmet[p.position]
        elif counts.get(p.position, 0):
            # a backup is worth the starter's exposure to being out
            s *= float(injury_rate.get(p.position, 0.1)) * 3.0
            if any(q.position == p.position and q.bye_week == p.bye_week for q in roster):
                s *= 0.5  # a same-bye backup covers nothing on the week you need him
        return s

    return max(cands, key=score)


def _replacement(board: Sequence[SeasonPlayer], position: str, depth: int = 12) -> float:
    """Projection of the `depth`-th best remaining player at `position` (0.0 if none)."""
    same = [p.projection for p in board if p.position == position]
    if not same:
        return 0.0
    return float(same[min(depth, len(same)) - 1])


def _template(slots: Mapping[str, int]) -> list[str]:
    return [s for slot, n in slots.items() for s in [slot] * int(n)]


def draft_league(
    players: Sequence[SeasonPlayer],
    row: Mapping[str, Any],
    *,
    seed: int = SEASON_EVAL_SEED,
    policies: Sequence[str] = DEFAULT_POLICY_MIX,
    pick_fn: Any = None,
) -> tuple[list[list[SeasonPlayer]], list[str]]:
    """Snake-draft one league; seats get policies deterministically from `seed`.

    Returns `(rosters, seat_policy)`. `pick_fn(policy, roster, board, slots, rounds, rates)` may be
    injected to seat an arbitrary policy (the bench-insurance ablation does exactly that).
    """
    teams = int(row["teams"])
    slots = dict(row["starting_slots"])
    rounds = sum(int(n) for n in slots.values()) + int(row["bench_slots"])
    rates = _injury_rates()
    rng = np.random.default_rng(seed + _DRAFT_STREAM)
    seat_policy = [policies[i % len(policies)] for i in range(teams)]
    rng.shuffle(seat_policy)  # deterministic in the seed, but not aligned to draft order
    take = pick_fn or _pick

    board = sorted(players, key=lambda p: (-p.projection, p.player_id))
    rosters: list[list[SeasonPlayer]] = [[] for _ in range(teams)]
    for r in range(rounds):
        order = range(teams) if r % 2 == 0 else range(teams - 1, -1, -1)
        for t in order:
            choice = take(seat_policy[t], rosters[t], board, slots, rounds, rates)
            rosters[t].append(choice)
            board.remove(choice)
    return rosters, seat_policy


def _injury_rates() -> dict[str, float]:
    """e3's published per-position clinical-injury rate — READ, never hard-coded here."""
    from blitz_engine.lineup.feasibility import InjuryDynamics

    dyn = InjuryDynamics.load()
    return {pos: float(v) for pos, v in dyn.rate.items()}


# ── schedule ───────────────────────────────────────────────────────────────────────────


def round_robin(teams: int, weeks: int) -> list[list[tuple[int, int]]]:
    """Circle-method round robin, repeated to `weeks`. Every week pairs every team exactly once."""
    ids = list(range(teams))
    if teams % 2:
        ids.append(-1)
    n = len(ids)
    base: list[list[tuple[int, int]]] = []
    for _ in range(n - 1):
        pairs = [
            (ids[i], ids[n - 1 - i])
            for i in range(n // 2)
            if ids[i] != -1 and ids[n - 1 - i] != -1
        ]
        base.append(pairs)
        ids = [ids[0], ids[-1], *ids[1:-1]]
    return [base[w % len(base)] for w in range(weeks)]


# ── the evaluator ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EvalConfig:
    """Knobs for one evaluation. `n_seasons` is the only accuracy/cost dial.

    C02 realism knobs (decision semantics preregistered in
    `.orchestrator-v6/experiments/waiver-realism-v1.json`): `proactive_moves_per_week`
    bounds point-in-time UPSIDE claims — roster-wide feasible (drop, add) swaps under
    actual slot eligibility, cross-position through FLEX/OP role space, K/DST streaming
    included; `upgrade_margin` is the relative anti-churn gate such a claim must clear.
    `waiver_cost` (fantasy points per claim) is BOTH a decision gate — a claim whose
    per-week believed gain × remaining weeks does not strictly exceed it never executes —
    and a single accounting charge at season aggregation (H2H weeks and the
    playoff/championship proxies stay on-field: seeding uses wins with GROSS season
    points). The weekly move budget is shared across all claim types
    (waiver-realism-v4): total claims per team-week ≤ max(`waiver_moves_per_week`,
    `proactive_moves_per_week`), emergencies ≤ `waiver_moves_per_week` drawing first,
    upside ≤ `proactive_moves_per_week` from the remainder. `season_moves_cap`
    hard-bounds total claims per team-season; `playoff_slots` sizes the playoff proxy.
    """

    n_seasons: int = 8
    seed: int = SEASON_EVAL_SEED
    shrink_kappa: float = 4.0  # pseudo-games of pre-season projection in the weekly forecast
    waiver_moves_per_week: int = 1
    waivers: bool = True
    proactive_moves_per_week: int = 1
    upgrade_margin: float = 0.15
    waiver_cost: float = 0.0
    season_moves_cap: int = 25
    playoff_slots: int = 4
    injury: InjuryDynamics | None = None  # default: e3's published fixture


#: Module-level singleton so the default is not a call in a signature (ruff B008).
DEFAULT_EVAL_CONFIG = EvalConfig()


_EMPTY = lambda: np.empty((0, 0), dtype=np.float64)  # noqa: E731 - dataclass default factory


@dataclass(frozen=True)
class SeasonEvalResult:
    """Per-seat outcome of one evaluation. `started_points` IS the metric.

    C02 adds paired per-season samples for every outcome family: `per_season` (points,
    net of transaction cost), `per_season_h2h` (weekly win rate), `per_season_playoff`
    and `per_season_champ` (0/1 proxy outcomes — seeding by wins with season points as
    tiebreak; the champion proxy is the highest-scoring playoff team, because the corpus
    has no bracket weeks to play). `waiver_adds = emergency_adds + upside_adds`.
    """

    started_points: np.ndarray  # (teams,) mean points the LOCKED lineup actually scored
    h2h_win_rate: np.ndarray  # (teams,) fraction of head-to-head weeks won
    seat_policy: list[str]
    starts_lost: np.ndarray  # (teams,) mean starting slots left empty/zeroed by a surprise
    waiver_adds: np.ndarray  # (teams,) mean successful waiver claims (all kinds)
    n_seasons: int
    weeks: int
    per_season: np.ndarray = field(  # (n_seasons, teams) — the paired vector for ablation
        default_factory=_EMPTY
    )
    emergency_adds: np.ndarray = field(default_factory=lambda: np.empty(0))  # (teams,) mean
    upside_adds: np.ndarray = field(default_factory=lambda: np.empty(0))  # (teams,) mean
    playoff_rate: np.ndarray = field(default_factory=lambda: np.empty(0))  # (teams,) mean
    champ_rate: np.ndarray = field(default_factory=lambda: np.empty(0))  # (teams,) mean
    per_season_h2h: np.ndarray = field(default_factory=_EMPTY)  # (n_seasons, teams)
    per_season_playoff: np.ndarray = field(default_factory=_EMPTY)  # (n_seasons, teams) 0/1
    per_season_champ: np.ndarray = field(default_factory=_EMPTY)  # (n_seasons, teams) 0/1

    @property
    def metric(self) -> float:
        """League-mean started points — the single number a fit maximises."""
        return float(self.started_points.mean())

    def by_policy(self) -> pd.DataFrame:
        """Per-policy mean of every column — the mixed-policy read-out."""
        df = pd.DataFrame(
            {
                "policy": self.seat_policy,
                "started_points": self.started_points,
                "h2h_win_rate": self.h2h_win_rate,
                "starts_lost": self.starts_lost,
                "waiver_adds": self.waiver_adds,
                "emergency_adds": self.emergency_adds,
                "upside_adds": self.upside_adds,
                "playoff_rate": self.playoff_rate,
                "champ_rate": self.champ_rate,
            }
        )
        return df.groupby("policy", as_index=False).mean(numeric_only=True)


def _availability(players: Sequence[SeasonPlayer]) -> np.ndarray:
    """e2a `p_startable` per player, read through the public model (never hard-coded)."""
    frame = pd.DataFrame(
        {
            "player_id": [p.player_id for p in players],
            "depth_rank": [p.depth_rank for p in players],
        }
    )
    return AvailabilityModel().p_startable(frame).to_numpy(dtype=float)


def _injury_multipliers(
    players: Sequence[SeasonPlayer], weeks: int, dyn: InjuryDynamics, rng: np.random.Generator
) -> np.ndarray:
    """(P, weeks) sampled playing multipliers from e3's chain — 0.0 means clinically out."""
    mult = np.ones((len(players), weeks), dtype=np.float32)
    order: dict[str, list[int]] = {}
    for i, p in enumerate(players):
        order.setdefault(p.position, []).append(i)
    for pos, idx in order.items():
        mult[idx] = dyn.sample_weight(pos, weeks, len(idx), rng)
    return mult


def _fill(
    ids: Sequence[int],
    slots: Mapping[str, int],
    positions: Sequence[str],
    proj: np.ndarray,
    usable: np.ndarray,
) -> list[int]:
    """Greedy legal lineup: best believed-usable body into the most specific slot first."""
    pool = sorted((i for i in ids if usable[i]), key=lambda i: -proj[i])
    used: set[int] = set()
    chosen: list[int] = []
    for slot in sorted(slots, key=lambda s: (_SLOT_ORDER.index(s) if s in _SLOT_ORDER else 99)):
        accepts = slot_positions(slot)
        for _ in range(int(slots[slot])):
            pick = next((i for i in pool if i not in used and positions[i] in accepts), None)
            if pick is not None:
                used.add(pick)
                chosen.append(pick)
    return chosen


def evaluate_rosters(
    players: Sequence[SeasonPlayer],
    rosters: Sequence[Sequence[SeasonPlayer]],
    row: Mapping[str, Any],
    *,
    seat_policy: Sequence[str] | None = None,
    config: EvalConfig = DEFAULT_EVAL_CONFIG,
    leak: Mapping[str, Any] | None = None,
) -> SeasonEvalResult:
    """Play `rosters` through an imperfect-information season. See the module docstring.

    `leak` is a test hook: `{"week": w}` injects a week-`w` row into the decision frame, which
    `detect_leakage` must reject — proving the guard is live rather than decorative.
    """
    slots = dict(row["starting_slots"])
    weeks = len(players[0].points_if_plays)
    teams = len(rosters)
    idx = {p.player_id: i for i, p in enumerate(players)}
    positions = [p.position for p in players]
    byes = np.array([p.bye_week for p in players], dtype=np.int64)
    season_proj = np.array([p.projection for p in players], dtype=np.float64)
    if_plays = np.array([p.points_if_plays for p in players], dtype=np.float64)
    from blitz_engine.lineup.feasibility import InjuryDynamics

    dyn = config.injury or InjuryDynamics.load()
    p_avail = _availability(players)
    dead = np.array([is_effectively_unavailable(v) for v in p_avail])
    schedule = round_robin(teams, weeks)
    bench_cap = sum(int(n) for n in slots.values()) + int(row["bench_slots"])

    drafted = {p.player_id for r in rosters for p in r}
    free_pool = [i for i, p in enumerate(players) if p.player_id not in drafted]

    per_season = np.zeros((config.n_seasons, teams), dtype=np.float64)
    per_season_h2h = np.zeros((config.n_seasons, teams), dtype=np.float64)
    per_season_playoff = np.zeros((config.n_seasons, teams), dtype=np.float64)
    per_season_champ = np.zeros((config.n_seasons, teams), dtype=np.float64)
    wins = np.zeros(teams, dtype=np.float64)
    lost = np.zeros(teams, dtype=np.float64)
    emerg = np.zeros(teams, dtype=np.float64)
    upside = np.zeros(teams, dtype=np.float64)

    for s in range(config.n_seasons):
        inj_rng = np.random.default_rng(config.seed + _INJURY_STREAM + s)
        av_rng = np.random.default_rng(config.seed + _AVAIL_STREAM + s)
        mult = _injury_multipliers(players, weeks, dyn, inj_rng)
        avail_draw = av_rng.random((len(players), weeks)) < p_avail[:, None]
        on_bye = (byes[:, None] == np.arange(1, weeks + 1)[None, :]) & (byes[:, None] > 0)
        plays = (mult > 0.0) & avail_draw & ~on_bye & ~dead[:, None]
        realised = if_plays * mult * plays

        squads = [[idx[p.player_id] for p in r] for r in rosters]
        free = list(free_pool)
        obs_sum = np.zeros(len(players))
        obs_n = np.zeros(len(players))
        season_wins = np.zeros(teams)
        season_pts = np.zeros(teams)
        season_emerg = np.zeros(teams)
        season_upside = np.zeros(teams)
        moves_left = np.full(teams, config.season_moves_cap, dtype=np.int64)

        for w in range(weeks):
            # ── the decision frame: weeks strictly before w, checked, not trusted ──
            decision = _decision_frame(w, obs_n, leak)
            detect_leakage(decision, pd.DataFrame({"week": [w]}), time_col="week")

            per_game = season_proj / weeks
            proj = (config.shrink_kappa * per_game + obs_sum) / (config.shrink_kappa + obs_n)
            # Known at lock time: byes, and last week's injury report (state as of w-1).
            known_out = on_bye[:, w] | dead
            if w:
                known_out = known_out | (mult[:, w - 1] == 0.0)

            n_slots = sum(int(n) for n in slots.values())
            week_scores = np.zeros(teams)
            for t in range(teams):
                started = _fill(squads[t], slots, positions, proj, ~known_out)
                week_scores[t] = float(realised[started, w].sum()) if started else 0.0
                lost[t] += sum(1 for i in started if not plays[i, w]) + n_slots - len(started)
            season_pts += week_scores

            for home, away in schedule[w]:
                if week_scores[home] > week_scores[away]:
                    season_wins[home] += 1
                elif week_scores[away] > week_scores[home]:
                    season_wins[away] += 1
                else:
                    season_wins[home] += 0.5
                    season_wins[away] += 0.5

            observed = plays[:, w]
            obs_sum[observed] += realised[observed, w]
            obs_n[observed] += 1.0

            if config.waivers and w + 1 < weeks:
                e, u = _run_waivers(
                    squads, free, season_wins, slots, positions, proj,
                    known_out=(on_bye[:, w + 1] | dead | (mult[:, w] == 0.0)),
                    limit=config.waiver_moves_per_week, cap=bench_cap,
                    proactive_limit=config.proactive_moves_per_week,
                    upgrade_margin=config.upgrade_margin, moves_left=moves_left,
                    cost=config.waiver_cost, weeks_left=weeks - 1 - w,
                )
                season_emerg += e
                season_upside += u

        # Transaction friction: each claim costs `waiver_cost` started points at season
        # aggregation. Weekly H2H is decided on the field, so weekly scores are untouched.
        per_season[s] = season_pts - config.waiver_cost * (season_emerg + season_upside)
        per_season_h2h[s] = season_wins / weeks
        # Playoff proxy: top `playoff_slots` seats by (wins, season points); the champion
        # proxy is the highest-scoring playoff seat (the corpus has no bracket weeks).
        n_po = min(config.playoff_slots, teams)
        seeding = np.lexsort((-season_pts, -season_wins))
        po = seeding[:n_po]
        per_season_playoff[s, po] = 1.0
        per_season_champ[s, po[np.argmax(season_pts[po])]] = 1.0
        wins += season_wins
        emerg += season_emerg
        upside += season_upside

    inv = 1.0 / config.n_seasons
    return SeasonEvalResult(
        started_points=per_season.mean(axis=0),
        h2h_win_rate=wins * inv / weeks,
        seat_policy=list(seat_policy or ["?"] * teams),
        starts_lost=lost * inv,
        waiver_adds=(emerg + upside) * inv,
        n_seasons=config.n_seasons,
        weeks=weeks,
        per_season=per_season,
        emergency_adds=emerg * inv,
        upside_adds=upside * inv,
        playoff_rate=per_season_playoff.mean(axis=0),
        champ_rate=per_season_champ.mean(axis=0),
        per_season_h2h=per_season_h2h,
        per_season_playoff=per_season_playoff,
        per_season_champ=per_season_champ,
    )


def _decision_frame(week: int, obs_n: np.ndarray, leak: Mapping[str, Any] | None) -> pd.DataFrame:
    """Rows the manager is allowed to see before week `week` — plus an optional injected leak."""
    rows = list(range(week))
    if leak is not None and int(leak.get("week", -1)) == week:
        rows.append(week)  # the deliberate violation the guard must catch
    if not rows:
        return pd.DataFrame({"week": pd.Series(dtype=float)})
    return pd.DataFrame({"week": rows, "n": [float(obs_n.sum())] * len(rows)})


def _run_waivers(
    squads: list[list[int]],
    free: list[int],
    season_wins: np.ndarray,
    slots: Mapping[str, int],
    positions: Sequence[str],
    proj: np.ndarray,
    *,
    known_out: np.ndarray,
    limit: int,
    cap: int,
    proactive_limit: int = 0,
    upgrade_margin: float = 0.15,
    moves_left: np.ndarray | None = None,
    cost: float = 0.0,
    weeks_left: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Contested waivers: worst record claims first from ONE shared pool. Bounded fidelity.

    Decision semantics are preregistered in
    `.orchestrator-v6/experiments/waiver-realism-v1.json`. Two claim kinds, both
    point-in-time (they read only the believed projection built from weeks already
    observed), both charged against `moves_left` (the season cap), and both gated by the
    transaction cost: a claim executes only when its expected remaining-horizon
    improvement (per-week believed gain × `weeks_left`) STRICTLY exceeds `cost` — an
    equal-or-below-cost claim never transacts. `cost` is also charged once per executed
    claim at season aggregation (accounting), which is a separate, single charge, not a
    second gate.

    The weekly move budget is shared across BOTH claim kinds (waiver-realism-v4):
    total claims per team-week ≤ max(`limit`, `proactive_limit`), with emergencies
    additionally capped by `limit` (drawing from the shared allowance first) and
    upside claims capped by `proactive_limit` (using only the remainder).

    - EMERGENCY: an unfillable starting slot claims the best free agent at the missing
      position; its per-week gain is the added projection (the alternative is a 0-point
      hole).
    - UPSIDE: the roster-wide feasible (drop, add) swap chosen by `_best_upgrade` —
      slot-eligibility aware, cross-position through FLEX/OP role space, lowest
      forward-looking nonstarter preferred as the drop, `upgrade_margin` retained as
      the relative anti-churn gate. K/DST streams through the same rule.

    Priority is reverse standings and the pool is shared, so two teams wanting the same
    player is a real contest. Deliberately OMITTED: FAAB budgets, trades, multi-week
    speculative stashes, and hoarding a handcuff.

    Returns `(emergency_adds, upside_adds)` per team for this week.
    """
    emerg = np.zeros(len(squads), dtype=np.float64)
    upside = np.zeros(len(squads), dtype=np.float64)
    if moves_left is None:
        moves_left = np.full(len(squads), np.iinfo(np.int64).max, dtype=np.int64)
    # waiver-realism-v4: ONE total per-team weekly budget shared across claim types —
    # max(limit, proactive_limit) — with each kind also capped by its own knob.
    # Emergencies draw from the shared allowance first; upside uses the remainder.
    week_left = np.full(len(squads), max(limit, proactive_limit), dtype=np.int64)
    order = sorted(range(len(squads)), key=lambda t: (season_wins[t], t))
    for t in order:
        e_used = 0
        while True:
            if e_used >= limit or week_left[t] <= 0 or moves_left[t] <= 0:
                break
            usable = ~known_out
            filled = _fill(squads[t], slots, positions, proj, usable)
            hole = _first_hole(squads[t], slots, positions, proj, usable, filled)
            if hole is None:
                break
            best = max(
                (i for i in free if positions[i] in hole and not known_out[i]),
                key=lambda i: proj[i], default=None,
            )
            if best is None:
                break
            if float(proj[best]) * weeks_left <= cost:
                break  # filling the hole cannot repay the transaction cost
            if len(squads[t]) >= cap:
                droppable = [i for i in squads[t] if i not in set(filled)]
                if not droppable:
                    break
                drop = min(droppable, key=lambda i: proj[i])
                squads[t].remove(drop)
                free.append(drop)
            squads[t].append(best)
            free.remove(best)
            emerg[t] += 1.0
            e_used += 1
            moves_left[t] -= 1
            week_left[t] -= 1
    for t in order:
        for _ in range(proactive_limit):
            if week_left[t] <= 0 or moves_left[t] <= 0:
                break
            swap = _best_upgrade(
                squads[t], free, positions, proj, known_out, upgrade_margin,
                slots=slots, cost=cost, weeks_left=weeks_left,
            )
            if swap is None:
                break
            drop, best = swap
            squads[t].remove(drop)
            free.append(drop)
            squads[t].append(best)
            free.remove(best)
            upside[t] += 1.0
            moves_left[t] -= 1
            week_left[t] -= 1
    return emerg, upside


def _best_upgrade(
    squad: Sequence[int],
    free: Sequence[int],
    positions: Sequence[str],
    proj: np.ndarray,
    known_out: np.ndarray,
    margin: float,
    slots: Mapping[str, int] | None = None,
    cost: float = 0.0,
    weeks_left: int = 1,
) -> tuple[int, int] | None:
    """The feasible roster-wide (drop, add) swap with the largest believed edge, else None.

    Preregistered rule (waiver-realism-v3, superseding v1's role-space restriction):
    for every free agent not known out and eligible for at least one actual lineup
    slot, the drop candidate is the lowest forward-looking NONSTARTER roster-wide —
    it need not share the add's nominal position or role space, so a dead or
    configuration-ineligible bench body is droppable for any legal add (removing a
    nonstarter can never reduce lineup coverage). Only when no nonstarter exists may
    a STARTED body be replaced, and then only if the post-swap lineup still fills at
    least as many slots — exactly K/DST streaming, while dropping a slot's only
    possible filler stays forbidden. A swap executes only if it clears BOTH gates,
    strictly:

      proj[add] > proj[drop] × (1 + margin)          (relative anti-churn margin)
      (proj[add] − proj[drop]) × weeks_left > cost   (remaining-horizon cost gate)

    With `slots=None` there is no lineup to consult and the drop candidate is the
    lowest-believed-projection body (the manifest's no-slots fallback).
    """
    usable = ~known_out
    if slots is not None:
        eligible = {
            pos: frozenset(s for s in slots if pos in slot_positions(s))
            for pos in set(positions[i] for i in [*squad, *free])
        }
        started = _fill(squad, slots, positions, proj, usable)
        n_now = len(started)
        started_set = set(started)
        nonstarters = sorted(
            (i for i in squad if i not in started_set), key=lambda i: (float(proj[i]), i)
        )
        starters_lowfirst = sorted(started, key=lambda i: (float(proj[i]), i))
    else:
        eligible = None
        nonstarters = sorted(squad, key=lambda i: (float(proj[i]), i))
        starters_lowfirst = []
        n_now = 0

    best: tuple[int, int] | None = None
    best_edge = 0.0
    for f in free:
        if known_out[f]:
            continue
        if eligible is not None and not eligible[positions[f]]:
            continue  # no lineup slot can ever use this body — infeasible add
        if nonstarters:
            drop = nonstarters[0]  # lowest forward-looking nonstarter, roster-wide
        else:
            # empty bench: a started body is replaceable only if the post-swap lineup
            # still fills at least as many slots (streaming, never a sole-filler drop)
            drop = next(
                (
                    d for d in starters_lowfirst
                    if len(_fill([*(i for i in squad if i != d), f],
                                 slots, positions, proj, usable)) >= n_now
                ),
                None,
            )
            if drop is None:
                continue
        gain = float(proj[f] - proj[drop])
        if proj[f] <= proj[drop] * (1.0 + margin):
            continue
        if gain * weeks_left <= cost:
            continue
        if gain > best_edge:
            best_edge = gain
            best = (drop, f)
    return best


def _first_hole(
    squad: Sequence[int],
    slots: Mapping[str, int],
    positions: Sequence[str],
    proj: np.ndarray,
    usable: np.ndarray,
    filled: Sequence[int],
) -> frozenset[str] | None:
    """The accepted-position set of the first starting slot this squad cannot fill, else None."""
    if len(filled) == sum(int(n) for n in slots.values()):
        return None
    used: set[int] = set()
    for slot in sorted(slots, key=lambda s: (_SLOT_ORDER.index(s) if s in _SLOT_ORDER else 99)):
        accepts = slot_positions(slot)
        for _ in range(int(slots[slot])):
            pick = next(
                (i for i in sorted(squad, key=lambda i: -proj[i])
                 if usable[i] and i not in used and positions[i] in accepts),
                None,
            )
            if pick is None:
                return accepts
            used.add(pick)
    return None


def evaluate_season(
    year: int,
    row: Mapping[str, Any],
    *,
    config: EvalConfig = DEFAULT_EVAL_CONFIG,
    policies: Sequence[str] = DEFAULT_POLICY_MIX,
    pick_fn: Any = None,
    players: Sequence[SeasonPlayer] | None = None,
) -> SeasonEvalResult:
    """**The public entry point.** Draft one mixed-policy league and evaluate it. See module doc."""
    pool = list(players) if players is not None else build_players(year, row["id"])
    rosters, seat_policy = draft_league(
        pool, row, seed=config.seed, policies=policies, pick_fn=pick_fn
    )
    return evaluate_rosters(
        pool, rosters, row, seat_policy=seat_policy, config=config
    )


# ── the retired metric, kept ONLY as the contrast in the acceptance test ───────────────


def hindsight_points(
    players: Sequence[SeasonPlayer],
    rosters: Sequence[Sequence[SeasonPlayer]],
    row: Mapping[str, Any],
) -> np.ndarray:
    """The RETIRED metric: perfect-hindsight weekly-optimal lineup points per team.

    Each week you start whoever actually scored most — no sampling, no lock, no waivers. Kept so
    `test_league_sim.py` can show a bench-insurance ablation that this metric cannot see and the
    new one can. **Never use it to tune anything.**
    """
    weeks = len(players[0].points_if_plays)
    idx = {p.player_id: i for i, p in enumerate(players)}
    positions = [p.position for p in players]
    byes = np.array([p.bye_week for p in players], dtype=np.int64)
    actual = np.array([p.points_if_plays for p in players], dtype=np.float64)
    slots = dict(row["starting_slots"])
    out = np.zeros(len(rosters), dtype=np.float64)
    for t, roster in enumerate(rosters):
        squad = [idx[p.player_id] for p in roster]
        for w in range(weeks):
            usable = ~((byes == w + 1) & (byes > 0))
            started = _fill(squad, slots, positions, actual[:, w], usable)
            out[t] += float(actual[started, w].sum())
    return out


def bench_cover_pick_fn(cover: bool) -> Any:
    """A `pick_fn` for `draft_league` that drafts WITH or WITHOUT bench insurance.

    Starters are chosen identically in both arms (best available at an unmet starting slot) and
    bench picks are drawn from the SAME `top_k` window of the same board, so raw roster talent is
    held near-constant and the arms differ only in *whether the bench can cover a hole*: the cover
    arm takes bodies at the thinnest starting position on a bye its starters do not share, the
    no-cover arm deliberately stacks the deepest position on the starters' own bye weeks. This is
    the acceptance construct: the imperfect-information metric must see the difference; hindsight,
    which faces no bye and no surprise, must not.
    """
    cover_pos = ("RB", "WR", "TE")

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
        flex = sum(
            int(n) for slot, n in slots.items() if len(slot_positions(slot)) > 1
        )
        starters = sum(int(n) for n in slots.values())
        if unmet or len(roster) < starters - flex:
            pool = [p for p in board if p.position in unmet] or board
            return pool[0]
        if len(roster) < starters:  # flex slots: best available skill player
            pool = [p for p in board if p.position in cover_pos] or board
            return pool[0]
        # ── bench: same window, same positions, opposite cover logic ──
        window = [p for p in board if p.position in cover_pos][:top_k]
        if not window:
            return board[0]
        # Talent band: both arms may only choose within 10% of the best body in the window, so
        # the arms are matched on raw production and differ only on cover.
        floor = 0.9 * window[0].projection
        window = [p for p in window if p.projection >= floor] or window[:1]
        starter_byes = {p.bye_week for p in roster[:starters] if p.bye_week}
        thin = {pos: counts.get(pos, 0) - need.get(pos, 0) for pos in cover_pos}
        if cover:
            key = lambda p: (  # noqa: E731 - a local ranking key, not a function
                p.bye_week in starter_byes, thin.get(p.position, 0), -p.projection
            )
        else:
            key = lambda p: (  # noqa: E731
                p.bye_week not in starter_byes, -thin.get(p.position, 0), -p.projection
            )
        return min(window, key=key)

    return pick


def paired_effect(a: SeasonEvalResult, b: SeasonEvalResult, seats: Iterable[int]) -> float:
    """Mean per-season started-points gap between two arms on the same seats (a − b)."""
    s = list(seats)
    return float((a.per_season[:, s] - b.per_season[:, s]).mean())


def paired_ci(
    a: SeasonEvalResult,
    b: SeasonEvalResult,
    seats: Iterable[int],
    field: str = "per_season",
) -> dict[str, float]:
    """Paired per-season delta (a − b) on `seats` with a normal-approx CI95 and sample count.

    `field` names any (n_seasons, teams) sample array on the result: `per_season`
    (points), `per_season_h2h`, `per_season_playoff`, `per_season_champ`. The paired
    sample is the per-season seat-mean delta, so `n` = n_seasons and the two arms must
    share seeds/seats for the pairing to mean anything. Returns {mean, lo, hi, n}.
    """
    s = list(seats)
    da, db = getattr(a, field), getattr(b, field)
    d = (da[:, s] - db[:, s]).mean(axis=1)
    n = len(d)
    mean = float(d.mean())
    half = 1.96 * float(d.std(ddof=1)) / np.sqrt(n) if n > 1 else float("inf")
    return {"mean": mean, "lo": mean - half, "hi": mean + half, "n": float(n)}
