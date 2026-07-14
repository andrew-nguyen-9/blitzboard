"""Thin normalizers: existing-adapter rows → `TeamObservation`s.

The engine REUSES the cron adapters (Sleeper `pipeline/adapters/sleeper_state.py`,
ESPN `pipeline/league_sync.py`, nflverse) rather than re-fetching — see
`blitz_engine.pipeline_bridge`. Those adapters emit dict rows; these functions map
those rows onto the reconcile input with the right source name + field. One generic
mapper (ponytail) backs three one-line wrappers.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from .model import TeamObservation


def observations_from(
    records: Iterable[Mapping[str, object]] | Mapping[str, Mapping[str, object]],
    source: str,
    *,
    id_field: str = "player_id",
    team_field: str = "team",
    as_of: datetime | None = None,
) -> list[TeamObservation]:
    """Map source rows to observations.

    `records` is an iterable of dict rows, OR a Mapping keyed by player id (the
    Sleeper `/players/nfl` shape) — the key backfills a missing `id_field`. Rows
    with no resolvable player id are skipped.
    """
    if isinstance(records, Mapping):
        rows: Iterable[Mapping[str, object]] = (
            r if id_field in r else {id_field: k, **r} for k, r in records.items()
        )
    else:
        rows = records
    out: list[TeamObservation] = []
    for r in rows:
        pid = r.get(id_field)
        if pid is None:
            continue
        team = r.get(team_field)
        out.append(TeamObservation(str(pid), None if team is None else str(team), source, as_of))
    return out


def from_sleeper(records, *, as_of: datetime | None = None) -> list[TeamObservation]:
    """Sleeper player metadata — team abbrev in `team` (None ⇒ free agent)."""
    return observations_from(records, "sleeper", team_field="team", as_of=as_of)


def from_espn(records, *, as_of: datetime | None = None) -> list[TeamObservation]:
    """ESPN roster rows — unofficial/fragile, lowest authority (league_sync D1)."""
    return observations_from(records, "espn", team_field="proTeam", as_of=as_of)


def from_nflverse(records, *, as_of: datetime | None = None) -> list[TeamObservation]:
    """nflverse rosters — canonical NFL team truth, highest authority."""
    return observations_from(records, "nflverse", team_field="team", as_of=as_of)
