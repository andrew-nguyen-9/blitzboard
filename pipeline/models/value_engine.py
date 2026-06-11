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

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .league_rules import LeagueRules, BASE_POSITIONS
from .projector import Projection


@dataclass
class PlayerValue:
    player_id: str
    engine: str                # 'vorp' | 'monte_carlo'
    value: float
    vor: float
    replacement: float
    rank: int
    boom: float | None = None
    bust: float | None = None


class ValueEngine(ABC):
    name: str = "abstract"

    @abstractmethod
    def compute(
        self, projections: dict[str, Projection], positions: dict[str, str], rules: LeagueRules
    ) -> list[PlayerValue]:
        """projections: player_id→Projection; positions: player_id→pos."""
        ...


class VorpEngine(ValueEngine):
    """Value Over Replacement Player.

    Replacement baseline per position = the league-wide starter demand from
    LeagueRules.replacement_ranks() — which is SUPERFLEX-AWARE (D9): for Smores,
    QB replacement is set deep (~OP-inflated) so elite QBs price correctly.
    """

    name = "vorp"

    def compute(self, projections, positions, rules):
        repl_rank = rules.replacement_ranks()

        # group projected means by position, descending
        by_pos: dict[str, list[tuple[str, float]]] = {p: [] for p in BASE_POSITIONS}
        for pid, proj in projections.items():
            pos = positions.get(pid)
            if pos in by_pos:
                by_pos[pos].append((pid, proj.mean))
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: x[1], reverse=True)

        # replacement value = the Nth-ranked player's projection at that position
        replacement: dict[str, float] = {}
        for pos, ranked in by_pos.items():
            n = repl_rank.get(pos, 1)
            replacement[pos] = ranked[n - 1][1] if len(ranked) >= n else (ranked[-1][1] if ranked else 0.0)

        out: list[PlayerValue] = []
        for pid, proj in projections.items():
            pos = positions.get(pid)
            if pos not in by_pos:
                continue
            repl = replacement.get(pos, 0.0)
            vor = proj.mean - repl
            out.append(PlayerValue(
                player_id=pid, engine=self.name, value=vor, vor=vor,
                replacement=repl, rank=0,
                # crude boom/bust off the projection distribution until MC lands
                boom=proj.ceiling - repl, bust=proj.floor - repl,
            ))
        out.sort(key=lambda v: v.value, reverse=True)
        for i, v in enumerate(out, 1):
            v.rank = i
        return out


class MonteCarloEngine(ValueEngine):
    """Simulate N drafts/seasons from projection distributions + opponent behavior.

    Superflex opponent model (QB-hungry drafting) lives here. Implemented in P7;
    Projector already emits distributions so this isn't blocked."""

    name = "monte_carlo"

    def __init__(self, n_sims: int = 10_000):
        self.n_sims = n_sims

    def compute(self, projections, positions, rules):
        raise NotImplementedError("MonteCarloEngine lands in P7 (Projector already emits dists)")
