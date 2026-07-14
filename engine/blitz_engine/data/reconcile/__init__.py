"""Multi-source NFL team reconciliation + publish gate (E4fix-team-reconcile).

Public API:
    obs = from_sleeper(...) + from_espn(...) + from_nflverse(...)
    resolutions = reconcile_teams(obs)          # per-player team + confidence + source
    validate_publish(resolutions)               # raises PublishBlocked if too dirty

See `core` for the precedence rule and gate thresholds.
"""
from __future__ import annotations

from .core import (
    MAX_MISMATCH_FRAC,
    MAX_UNASSIGNED_FRAC,
    SOURCE_AUTHORITY,
    canon_team,
    reconcile_teams,
    validate_publish,
)
from .model import PublishBlocked, TeamObservation, TeamResolution
from .sources import from_espn, from_nflverse, from_sleeper, observations_from

__all__ = [
    "MAX_MISMATCH_FRAC",
    "MAX_UNASSIGNED_FRAC",
    "SOURCE_AUTHORITY",
    "PublishBlocked",
    "TeamObservation",
    "TeamResolution",
    "canon_team",
    "from_espn",
    "from_nflverse",
    "from_sleeper",
    "observations_from",
    "reconcile_teams",
    "validate_publish",
]
