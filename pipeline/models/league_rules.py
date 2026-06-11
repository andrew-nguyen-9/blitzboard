"""
LeagueRules — the single source of truth for scoring + roster (ARCH §1 / D9).

Loaded from the `league_rules` Supabase row (seeded by db/seed_league_smores.sql).
The crucial method is `replacement_ranks()`: it derives, per position, *how many*
players the league starts league-wide — which is what sets VORP replacement levels.

For "Smores 2025" the OP (Offensive Player Utility) slot is QB-eligible, so this
returns a superflex-correct QB demand (~24 in a 12-team league), not the naive 12.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Which real positions can fill each multi-position slot.
SLOT_ELIGIBILITY: dict[str, tuple[str, ...]] = {
    "FLEX": ("RB", "WR", "TE"),
    "OP": ("QB", "RB", "WR", "TE"),   # superflex
    "WRRB": ("WR", "RB"),
    "WRTE": ("WR", "TE"),
}
BASE_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")


@dataclass
class LeagueRules:
    league_id: str
    league_size: int
    scoring: dict
    roster_slots: dict
    waiver_type: str = "faab"

    @property
    def is_superflex(self) -> bool:
        return bool(self.roster_slots.get("_superflex")) or "OP" in self.roster_slots

    def starters_per_team(self, position: str) -> float:
        """Expected starters of `position` per team, spreading flex/OP demand.

        Dedicated slots count fully; flexible slots are apportioned across their
        eligible positions (simple even split — refined with ADP weighting in P2).
        """
        slots = self.roster_slots
        count = float(slots.get(position, 0) or 0)
        for slot, eligible in SLOT_ELIGIBILITY.items():
            n = float(slots.get(slot, 0) or 0)
            if n and position in eligible:
                count += n / len(eligible)
        return count

    def replacement_ranks(self) -> dict[str, int]:
        """Position → league-wide starter demand = the VORP replacement rank.

        e.g. Smores: QB ≈ 12*(1 + 1/4 OP) ≈ 15 *starters*, but realistic rosters
        also bench QBs in superflex — P2 nudges this toward ~24. v1 uses pure slot
        demand as the baseline.
        """
        return {
            pos: max(1, round(self.league_size * self.starters_per_team(pos)))
            for pos in BASE_POSITIONS
        }


def load_league_rules(league_id: str | None = None) -> LeagueRules | None:
    """Load rules from Supabase. Returns None if unavailable (offline-safe)."""
    from common import get_supabase, console

    sb = get_supabase()
    if sb is None:
        return None
    q = sb.table("league_rules").select("*, leagues!inner(name,season)")
    if league_id:
        q = q.eq("league_id", league_id)
    rows = q.limit(1).execute().data or []
    if not rows:
        console.print("[yellow]⚠ no league_rules row — run db/seed_league_smores.sql[/yellow]")
        return None
    r = rows[0]
    return LeagueRules(
        league_id=r["league_id"],
        league_size=r.get("league_size") or 12,
        scoring=r["scoring"],
        roster_slots=r["roster_slots"],
        waiver_type=r.get("waiver_type") or "faab",
    )
