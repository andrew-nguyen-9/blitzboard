"""
Kicker & Defense projectors — K and D/ST get their own treatment (not the
offensive ensemble).

Why separate (D9 + reality):
  • K and D/ST are stat-sparse in nflverse and notoriously volatile year-to-year
    (especially D/ST), so a regression on skill-position features is meaningless.
  • The league's K scoring is distance-based and its D/ST scoring has a yardage-
    allowed component — different value shape than offense.
  • Everyone effectively drafts K/D-ST off consensus rank, so we piggyback the
    consensus ORDERING (FFC ADP) onto a calibrated points BASELINE for the slot.

Each projector returns a distribution (mean + floor/ceiling/stdev) like the rest,
so Monte Carlo (P7) and VORP consume them uniformly. Baselines are tuned to the
Smores ruleset (distance K is a touch higher; tiered D/ST is swingy → wider σ).
"""
from __future__ import annotations

from .projector import Projector, Projection
from .adp import fetch_ffc_adp, positional_order


def _baseline_curve(top: float, bottom: float, n: int) -> list[float]:
    """Monotonic rank→points baseline (rank 0 = best)."""
    if n <= 1:
        return [top]
    step = (top - bottom) / (n - 1)
    return [round(top - step * i, 1) for i in range(n)]


class _ConsensusSlotProjector(Projector):
    """Base: rank a position by ADP, assign points from a calibrated baseline.

    If ADP is unavailable, every player at the slot gets the mid-baseline (the
    honest 'these are streamers, draft late' signal) rather than a fake spread.
    """

    position: str = ""        # our DB position (matched against the player)
    adp_position: str = ""    # FFC's position code for this slot (K→"PK", DST→"DEF")
    match_by: str = "name"    # how to join FFC entry → our player: "name" | "team"
    _top: float = 150.0
    _bottom: float = 80.0
    _n: int = 32
    _sigma_frac: float = 0.30

    def __init__(self, store, rules, target_season, teams: int = 12, fmt: str = "half-ppr"):
        super().__init__(store, rules, target_season)
        self._adp = fetch_ffc_adp(teams, fmt, target_season)
        self._order = positional_order(self._adp, self.adp_position or self.position) if self._adp else []
        self._curve = _baseline_curve(self._top, self._bottom, self._n)
        # kickers join on player name; defenses on team abbrev (FFC names defenses
        # "Denver Defense" but carries team="DEN", which matches our nfl_team).
        if self.match_by == "team":
            self._index = {str(e.get("team", "")).upper(): i for i, e in enumerate(self._order)}
        else:
            self._index = {e["name"].lower(): i for i, e in enumerate(self._order)}

    def project(self, player):
        if player.get("position") != self.position:
            return None
        key = (player.get("nfl_team") or "").upper() if self.match_by == "team" else (player.get("full_name") or "").lower()
        if key in self._index:
            rank = self._index[key]
            mean = self._curve[rank] if rank < len(self._curve) else self._curve[-1]
        else:
            mean = self._curve[len(self._curve) // 2]  # unranked → mid baseline
        stdev = max(mean * self._sigma_frac, 5.0)
        return Projection(
            player_id=player["id"], season=self.target_season, source="consensus_st",
            mean=round(mean, 2), stdev=round(stdev, 2),
            floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
        )


class KickerProjector(_ConsensusSlotProjector):
    """Distance-based K scoring nudges the baseline up vs flat-3 leagues.
    FFC labels kickers 'PK'."""
    position = "K"
    adp_position = "PK"
    _top, _bottom, _n = 165.0, 110.0, 32
    _sigma_frac = 0.22


class DefenseProjector(_ConsensusSlotProjector):
    """D/ST with a yardage-allowed component — high variance → widest σ.
    Player rows are canonicalized to 'DST'; FFC labels defenses 'DEF'."""
    position = "DST"
    adp_position = "DEF"
    match_by = "team"
    _top, _bottom, _n = 150.0, 60.0, 32
    _sigma_frac = 0.38
