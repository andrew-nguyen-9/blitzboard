"""
ValueEngine — projections × LeagueRules → player value (ARCH §3 / D5).

Two implementations behind one interface; the UI toggles which cached set it reads:
  • VorpEngine        — deterministic value-over-replacement (shipped skeleton here)
  • MonteCarloEngine  — simulates N drafts/seasons (P7)

Both are batch-precomputed in the pipeline and written to `player_value` keyed by
(engine, scoring_profile). Draft/Trade/Waiver tools are thin consumers — they never
compute value themselves.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .league_rules import LeagueRules, BASE_POSITIONS
from .projector import Projection

# ── Value-shaping constants (#4: non-linear positional weighting + future value) ─
ELITE_PREMIUM = 0.65    # top-of-position convex bonus (elite RB ≫ mid RB)
ELITE_SCALE = 7.0       # how fast the premium decays down the position ranks
CLIFF_W = 0.45          # "tier cliff" bonus = separation over the next tier below
CLIFF_LOOKAHEAD = 4     # compare to the player N spots lower at the position
UPSIDE_W = 0.33         # reward ceiling over mean (boom = trade/league-winner equity)
YOUTH_W = 0.18          # future value: ascending youth up, aging down
CONSENSUS_W = 18.0      # consensus (Sleeper search_rank) nudge for the deep/bench pool
# rough positional peak ages (value-trajectory, not just this season)
PEAK_AGE = {"RB": 24, "WR": 26, "TE": 26, "QB": 29, "K": 30, "DST": 99}


def _youth_factor(pos: str, age: int | None) -> float:
    if age is None:
        return 1.0
    peak = PEAK_AGE.get(pos, 27)
    # young (below peak) gets up to +, old gets down; clamped and gentle
    delta = (peak - age) / 8.0
    return 1.0 + YOUTH_W * max(-0.8, min(1.0, delta))


@dataclass
class PlayerValue:
    player_id: str
    engine: str                # 'vorp' | 'monte_carlo'
    value: float               # shaped DRAFT value (non-linear, future-aware) — ranks the board
    vor: float                 # raw value-over-replacement (linear, interpretable; used for lineup sums)
    replacement: float
    rank: int
    boom: float | None = None
    bust: float | None = None
    adp: float | None = None
    tier: int | None = None


class ValueEngine(ABC):
    name: str = "abstract"

    @abstractmethod
    def compute(
        self, projections: dict[str, Projection], positions: dict[str, str], rules: LeagueRules,
        meta: dict | None = None,
    ) -> list[PlayerValue]:
        """projections: player_id→Projection; positions: player_id→pos;
        meta: player_id→{age, years_exp, adp} (optional, drives future-value)."""
        ...


class VorpEngine(ValueEngine):
    """Value Over Replacement Player.

    Replacement baseline per position = the league-wide starter demand from
    LeagueRules.replacement_ranks() — which is SUPERFLEX-AWARE (D9): for Smores,
    QB replacement is set deep (~OP-inflated) so elite QBs price correctly.
    """

    name = "vorp"

    def compute(self, projections, positions, rules, meta=None):
        meta = meta or {}
        repl_rank = rules.replacement_ranks()

        # group projected means by position, descending (with mean kept for cliffs)
        by_pos: dict[str, list[tuple[str, float]]] = {p: [] for p in BASE_POSITIONS}
        for pid, proj in projections.items():
            pos = positions.get(pid)
            if pos in by_pos:
                by_pos[pos].append((pid, proj.mean))
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: x[1], reverse=True)

        # replacement value = the Nth-ranked player's projection at that position
        replacement: dict[str, float] = {}
        pos_rank: dict[str, int] = {}        # player_id → 1-based rank within position
        pos_means: dict[str, list[float]] = {}
        for pos, ranked in by_pos.items():
            n = repl_rank.get(pos, 1)
            replacement[pos] = ranked[n - 1][1] if len(ranked) >= n else (ranked[-1][1] if ranked else 0.0)
            pos_means[pos] = [m for _, m in ranked]
            for i, (pid, _) in enumerate(ranked, 1):
                pos_rank[pid] = i

        out: list[PlayerValue] = []
        for pid, proj in projections.items():
            pos = positions.get(pid)
            if pos not in by_pos:
                continue
            repl = replacement.get(pos, 0.0)
            vor = proj.mean - repl                      # raw, linear, interpretable
            rk = pos_rank.get(pid, 999)
            m = meta.get(pid, {})

            # 1) convex ELITE premium — the top of a position towers over the middle
            elite = 1.0 + ELITE_PREMIUM * math.exp(-(rk - 1) / ELITE_SCALE)
            # 2) tier CLIFF bonus — separation over the player N spots below (scarcity of THIS tier)
            means = pos_means.get(pos, [])
            below = means[rk - 1 + CLIFF_LOOKAHEAD] if rk - 1 + CLIFF_LOOKAHEAD < len(means) else (means[-1] if means else proj.mean)
            cliff = max(0.0, proj.mean - below) * CLIFF_W
            # 3) UPSIDE — ceiling over mean = future trade equity / league-winner odds
            upside = max(0.0, proj.ceiling - proj.mean) * UPSIDE_W
            # 4) future-value YOUTH factor
            youth = _youth_factor(pos, m.get("age"))

            if vor > 0:
                shaped = (vor * elite + cliff + upside) * youth
            else:
                # deep/bench pool: real projections are thin & nearly tied here, so
                # order by Sleeper's consensus rank (search_rank) + a little upside.
                sr = m.get("search_rank")
                consensus = CONSENSUS_W * (1 - min(sr, 800) / 800) if (sr and sr < 999) else 0.0
                shaped = (vor + upside * 0.5) * youth + consensus

            out.append(PlayerValue(
                player_id=pid, engine=self.name, value=round(shaped, 2), vor=round(vor, 2),
                replacement=repl, rank=0,
                boom=round(proj.ceiling - repl, 2), bust=round(proj.floor - repl, 2),
                adp=m.get("adp"),
            ))
        # rank by SHAPED value (so elite/upside/youth reorder the board)
        out.sort(key=lambda v: v.value, reverse=True)
        # assign overall rank + per-position tiers (gaps in shaped value = tier breaks)
        by_pos_vals: dict[str, list[PlayerValue]] = {}
        for i, v in enumerate(out, 1):
            v.rank = i
            by_pos_vals.setdefault(positions.get(v.player_id, "?"), []).append(v)
        for pos, vs in by_pos_vals.items():
            _assign_tiers(vs)
        return out


def _assign_tiers(vs: list[PlayerValue]) -> None:
    """Tier players within a position by gaps in shaped value. A big drop = a real
    tier break (the 'cliff' a drafter feels). vs must be sorted desc by value."""
    if not vs:
        return
    vals = [v.value for v in vs]
    gaps = [vals[i - 1] - vals[i] for i in range(1, len(vals))]
    avg = (sum(gaps) / len(gaps)) if gaps else 0.0
    tier = 1
    vs[0].tier = 1
    for i in range(1, len(vs)):
        if (vals[i - 1] - vals[i]) > max(6.0, avg * 1.6):
            tier += 1
        vs[i].tier = tier


class MonteCarloEngine(ValueEngine):
    """Simulate N drafts/seasons from projection distributions + opponent behavior.

    Superflex opponent model (QB-hungry drafting) lives here. Implemented in P7;
    Projector already emits distributions so this isn't blocked."""

    name = "monte_carlo"

    def __init__(self, n_sims: int = 10_000):
        self.n_sims = n_sims

    def compute(self, projections, positions, rules, meta=None):
        raise NotImplementedError("MonteCarloEngine lands in P7 (Projector already emits dists)")
