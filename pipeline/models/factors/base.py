"""
Factor framework — base contract (F3).

A *factor* is a pure, deterministic, side-effect-free adjustment to a player's
point projection:

    factor(player, context) -> multiplier (identity 1.0)  OR  delta (identity 0.0)

Factors live ONE-PER-FILE in ``pipeline/models/factors/`` and are auto-discovered
by ``loader.discover_factors()`` — adding a factor requires ZERO edits to
``projector.py``. This is the seam E1/E2/E3/E5 build DISJOINT factor modules on.

Composition (see ``projector.apply_factors``):

    adjusted_mean = base_mean * ∏(multipliers) + Σ(deltas)

floor/ceiling/stdev scale with the multiplier and shift with the delta, so the
distribution shape (the ±1.28σ bounds) is preserved exactly. Factors are
ORTHOGONAL to the predictability discount f(ρ): that discount is applied LATER by
the ValueEngine on *value*, not here on the *projection*. A factor reshapes the
point projection; predictability then discounts unreproducible value on top.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

MULTIPLIER = "multiplier"
DELTA = "delta"


@dataclass
class FactorContext:
    """Everything a factor may need to compute its adjustment.

    Typed core fields cover identity / team / position / matchup / status; the
    ``metadata`` dict is the escape hatch so future signals (weather, betting
    lines, depth chart, scheme, snap share, college) fit WITHOUT changing this
    protocol. ``store`` (HistoryStore) and ``rules`` (LeagueRules) are provided so
    a factor can look at a player's historical lines or league scoring.
    """

    player_id: str
    full_name: str | None = None
    position: str | None = None
    positions: tuple[str, ...] = ()        # multi-position eligibility (fantasy_positions)
    nfl_team: str | None = None            # CANONICAL code (post roster-fix; see player_ingest)
    season: int = 0
    week: int | None = None                # None → season-long projection
    opponent: str | None = None            # team-vs-team / weekly matchup
    bye_week: int | None = None
    injury_status: str | None = None
    age: int | None = None
    years_exp: int | None = None
    college: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # depth chart, weather, betting, scheme…
    store: Any = None                      # HistoryStore
    rules: Any = None                      # LeagueRules

    @classmethod
    def from_player(
        cls,
        player: dict,
        season: int,
        *,
        store: Any = None,
        rules: Any = None,
        week: int | None = None,
        opponent: str | None = None,
    ) -> "FactorContext":
        """Build a context from a ``players``-row dict (id/full_name/position/
        nfl_team/age/years_exp/metadata). Safe on partial rows."""
        meta = player.get("metadata") or {}
        fp = meta.get("fantasy_positions")
        if not fp:
            fp = [player.get("position")] if player.get("position") else []
        return cls(
            player_id=player.get("id") or player.get("player_id") or "",
            full_name=player.get("full_name"),
            position=player.get("position"),
            positions=tuple(p for p in fp if p),
            nfl_team=player.get("nfl_team"),
            season=season,
            week=week if week is not None else player.get("week"),
            opponent=opponent,
            bye_week=player.get("bye_week"),
            injury_status=player.get("injury_status"),
            age=player.get("age"),
            years_exp=player.get("years_exp"),
            college=player.get("college") or meta.get("college"),
            metadata=meta,
            store=store,
            rules=rules,
        )


class Factor(ABC):
    """A pure projection adjustment. Subclass in ``factors/<name>.py``.

    Class attributes:
      * ``kind``      — ``MULTIPLIER`` (scales the projection) or ``DELTA`` (shifts
                        it in points). Default MULTIPLIER.
      * ``positions`` — optional whitelist tuple; ``None`` = every position.
      * ``enabled``   — ``False`` ships the factor DORMANT (discoverable but not
                        applied), useful for staging a factor behind a flag.

    Implement ``compute(ctx)`` only. Override ``applies(ctx)`` for gating richer
    than a positional whitelist. ``compute`` MUST be pure and deterministic.
    """

    kind: str = MULTIPLIER
    positions: tuple[str, ...] | None = None
    enabled: bool = True

    @property
    def name(self) -> str:
        return getattr(self, "_name", type(self).__name__)

    def identity(self) -> float:
        """The no-op value for this factor's kind."""
        return 1.0 if self.kind == MULTIPLIER else 0.0

    def applies(self, ctx: FactorContext) -> bool:
        """Gate: return False to leave this player untouched (identity)."""
        if self.positions is None:
            return True
        return ctx.position in self.positions

    @abstractmethod
    def compute(self, ctx: FactorContext) -> float:
        """Return a multiplier (kind=MULTIPLIER) or a points delta (kind=DELTA)."""
        ...

    def value_for(self, ctx: FactorContext) -> float:
        """Applied value: the identity when disabled or gated out."""
        if not self.enabled or not self.applies(ctx):
            return self.identity()
        return self.compute(ctx)
