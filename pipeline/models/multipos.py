"""
multipos.py (E2) — per-position analytics for multi-eligible players.

A player Sleeper lists at more than one fantasy slot (e.g. a pass-catching back
eligible at RB *and* WR, or a move TE at TE/WR) is worth a DIFFERENT amount at each
slot, because positional scarcity differs: the same projected points buy more value
at the scarcer position. This module turns a player's eligibility + one projected
point total into a per-position value breakdown, and names the slot where the
player is most valuable.

Pure + dependency-free (no DB, no network): it takes the eligible positions off the
player row (``metadata.fantasy_positions``, populated by ``player_ingest.normalize``)
and a ``replacement_by_pos`` baseline (the last-startable projection per position,
which the ValueEngine already computes — passed IN, never imported, so this stays
orthogonal to that unit). VOR at a slot = projected_pts − replacement[slot].

Single-position players degrade to a one-line breakdown (primary = their only slot),
so callers can render this uniformly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# The fantasy slots we analyze (mirrors player_ingest.FANTASY_POSITIONS minus the
# team-scored ones, which have no cross-eligibility). K/DEF never share a player.
_SKILL = ("QB", "RB", "WR", "TE")


@dataclass(frozen=True)
class PositionLine:
    position: str
    projected_pts: float
    replacement: float
    vor: float               # projected_pts − replacement (value over replacement at this slot)
    primary: bool            # the slot with the highest VOR (where you'd roster them)


def eligible_positions(player: dict) -> tuple[str, ...]:
    """Skill positions a player is eligible at, from ``metadata.fantasy_positions``
    (falling back to the primary ``position``). De-duplicated, order-stable, and
    filtered to the slots we analyze. Empty tuple when nothing is known."""
    meta = player.get("metadata") or {}
    raw = meta.get("fantasy_positions") or []
    if not raw and player.get("position"):
        raw = [player["position"]]
    seen: list[str] = []
    for p in raw:
        if p in _SKILL and p not in seen:
            seen.append(p)
    return tuple(seen)


def is_multi_position(player: dict) -> bool:
    return len(eligible_positions(player)) > 1


def analyze(
    player: dict,
    projected_pts: float,
    replacement_by_pos: Mapping[str, float],
) -> list[PositionLine]:
    """Per-eligible-position VOR breakdown, sorted best-value first.

    ``projected_pts`` is the player's single ensemble projection (position-agnostic —
    the same points score regardless of which slot they fill). ``replacement_by_pos``
    supplies the replacement baseline per position. Returns [] only when the player
    has no known eligible skill position.
    """
    positions = eligible_positions(player)
    if not positions:
        return []
    best_vor = max(projected_pts - float(replacement_by_pos.get(p, 0.0)) for p in positions)
    lines = [
        PositionLine(
            position=p,
            projected_pts=round(projected_pts, 2),
            replacement=round(float(replacement_by_pos.get(p, 0.0)), 2),
            vor=round(projected_pts - float(replacement_by_pos.get(p, 0.0)), 2),
            primary=(projected_pts - float(replacement_by_pos.get(p, 0.0))) == best_vor,
        )
        for p in positions
    ]
    # Highest VOR first; ties keep eligibility order. Exactly one `primary` flag is
    # set on the max even if VORs tie (first max wins) — normalize that here.
    lines.sort(key=lambda l: l.vor, reverse=True)
    seen_primary = False
    out: list[PositionLine] = []
    for l in lines:
        if l.primary and not seen_primary:
            seen_primary = True
            out.append(l)
        else:
            out.append(PositionLine(l.position, l.projected_pts, l.replacement, l.vor, False))
    return out


def primary_position(player: dict, projected_pts: float,
                     replacement_by_pos: Mapping[str, float]) -> str | None:
    """The slot a multi-eligible player is most valuable at (highest VOR), or their
    only/primary slot. None when eligibility is unknown."""
    lines = analyze(player, projected_pts, replacement_by_pos)
    return lines[0].position if lines else None
