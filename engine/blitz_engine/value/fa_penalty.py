"""Truly-free-agent detection + heavy value penalty (v4 BUG FIX item 3).

The board bug (screenshot): players with NO NFL team and NO draft/role news were getting
drafted early because the interim value never knew they were unrostered. The fix:

    truly-FA  ==  (no team, from E4fix-team-reconcile)  AND  (no draft/role news)

A truly-FA player is not hidden — it is SUNK below the entire visible board and kept in
the list, so the drafter still sees it, just correctly at the bottom. Everyone else is
untouched.

Degrade-neutral: we penalize only when BOTH signals affirmatively say free agent. A
missing/unknown news signal (`has_news is None`) is NOT "no news" — so a player we're
unsure about is left alone rather than wrongly sunk.

`ponytail:` one truly-FA predicate + one multiplicative haircut, then a single rebase that
guarantees the sink relative to the board — no re-scoring of anyone's value.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from blitz_engine.survival.availability import (
    RosterState,
    is_effectively_unavailable,
    is_season_long_zero,
    roster_state_p,
)
from blitz_engine.value.interim import InterimValue

# Heavy multiplicative penalty: keep only this fraction of interim value (98% haircut).
# Kept as an explicit factor so ordering AMONG free agents (a hair of signal) survives.
FA_PENALTY_FACTOR = 0.02
# After the haircut, rebase every FA strictly below the visible board's lowest non-FA
# value by at least this margin — the guarantee that they sink beneath all rostered play.
FA_SINK_MARGIN = 1.0


@dataclass(frozen=True)
class FAStatus:
    """The signals the truly-FA predicate consumes.

    * `team`     — reconciled NFL team from E4fix-team-reconcile; `None`/`""` means no team.
    * `has_news` — any draft or role news signal for the player. `True` = has news,
      `False` = confirmed no news, `None` = signal absent (treated as unknown, NOT as FA).
    * `roster_status` — (e2a) the raw roster state from an availability feed when one
      exists ("RET", "UFA", "PS", "IR", …). Strictly better than the team/news proxy:
      when present it decides the question outright. `None` = no feed → fall back.
    """

    team: str | None = None
    has_news: bool | None = None
    roster_status: str | None = None


def availability_of(status: FAStatus | None) -> float:
    """`FAStatus` → the e2a season-long availability ceiling for that player.

    This is the seam that makes `is_truly_free_agent` a view of `p_startable` rather than
    a second opinion: an explicit `roster_status` goes straight to `ROSTER_STATE_P`; with
    no feed we *infer* `FREE_AGENT` from the old two-signal proxy (no team AND confirmed
    no news) and `ROSTERED` (1.0, neutral) from anything less certain.
    """
    if status is None:
        return roster_state_p(RosterState.ROSTERED)
    if status.roster_status is not None:
        return roster_state_p(status.roster_status)
    no_team = not status.team                  # None or "" → no team
    no_news = status.has_news is False         # must be *confirmed* absent, not unknown
    inferred = RosterState.FREE_AGENT if (no_team and no_news) else RosterState.ROSTERED
    return roster_state_p(inferred)


def is_truly_free_agent(status: FAStatus | None) -> bool:
    """`True` when this player will take no snaps all season — now an availability view.

    Same semantics as before for the team/news proxy (no status at all → not FA; no team
    AND explicitly no news → FA; unknown news → not FA, we don't sink on half a signal),
    but expressed as `availability ≈ 0`, so a real feed reporting RETIRED / unsigned FA /
    camp body sinks too. Weekly-zero states (IR, PUP, NFI, suspension) deliberately do NOT
    sink — those players still score once the designation lifts (`is_season_long_zero`).
    """
    if status is None:
        return False
    if status.roster_status is not None:
        return is_season_long_zero(status.roster_status)
    return is_effectively_unavailable(availability_of(status))


def apply_fa_penalty(
    surface: list[InterimValue],
    status_by_player: Mapping[str, FAStatus],
    *,
    factor: float = FA_PENALTY_FACTOR,
    margin: float = FA_SINK_MARGIN,
) -> list[InterimValue]:
    """Sink every truly-FA row below the whole visible board; leave non-FA rows untouched.

    Returns a NEW re-ranked surface (input is not mutated). Free agents stay in the list
    (visible), just re-based beneath the lowest non-FA value by at least `margin`. Their
    relative order is preserved via the multiplicative `factor`, so among the sunk pool the
    least-implausible FA still sorts highest.
    """
    fa_ids = {
        iv.player_id
        for iv in surface
        if is_truly_free_agent(status_by_player.get(iv.player_id))
    }
    if not fa_ids:
        return [replace(iv) for iv in surface]

    non_fa_values = [iv.value for iv in surface if iv.player_id not in fa_ids]
    floor = min(non_fa_values) if non_fa_values else 0.0

    # Haircut first, then translate the whole FA band so its TOP sits at `floor - margin`.
    # `fa_top` anchors the rebase, guaranteeing every FA lands strictly below `floor`
    # regardless of how badly the interim engine over-valued them (the original bug).
    haircut = {iv.player_id: iv.value * factor for iv in surface if iv.player_id in fa_ids}
    fa_top = max(haircut.values())
    offset = floor - margin - fa_top

    out = [
        replace(iv, value=haircut[iv.player_id] + offset) if iv.player_id in fa_ids else replace(iv)
        for iv in surface
    ]
    out.sort(key=lambda iv: iv.value, reverse=True)
    for i, iv in enumerate(out, 1):
        iv.rank = i
    return out
