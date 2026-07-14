"""Value types for multi-source NFL team reconciliation.

An `TeamObservation` is one source's claim about a player's current NFL team at a
point in time; a `TeamResolution` is the reconciled verdict. `PublishBlocked` is
the non-zero signal the validation gate raises when the reconciled set fails the
publish bar — it carries the offending players so the caller can surface them.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TeamObservation:
    """One source's claim: `player_id` is on `team` as of `as_of`.

    `team=None` (or an unassigned marker like "FA") means the source reports the
    player as a free agent. `as_of=None` sorts as the oldest possible time.
    """

    player_id: str
    team: str | None
    source: str
    as_of: datetime | None = None


@dataclass(frozen=True, slots=True)
class TeamResolution:
    """The reconciled team for a player, with provenance.

    `team=None` means no source assigned a team (genuinely unassigned).
    `confidence` is the fraction of team-assigning sources that agreed with the
    winner. `mismatch` is True when assigning sources disagreed on the team.
    """

    player_id: str
    team: str | None
    confidence: float
    source: str
    sources_considered: int
    mismatch: bool

    @property
    def unassigned(self) -> bool:
        return self.team is None


class PublishBlocked(RuntimeError):
    """Raised by `validate_publish` when reconciled teams fail the publish bar."""

    def __init__(
        self,
        message: str,
        *,
        unassigned: Sequence[str],
        mismatched: Sequence[str],
    ) -> None:
        super().__init__(message)
        self.unassigned: tuple[str, ...] = tuple(unassigned)
        self.mismatched: tuple[str, ...] = tuple(mismatched)
