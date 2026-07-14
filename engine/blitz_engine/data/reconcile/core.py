"""Multi-source NFL team reconciliation + publish gate.

Fixes the "Mixon/Najee shown as FA" bug: one stale/incomplete source reporting a
player as a free agent must not override another source that knows the real team.

PRECEDENCE (documented, ponytail: a dict + a rule, not a rules engine):

  1. An *assigned* team beats *unassigned* — a "FA"/None claim never wins while any
     source has a real team. This is the direct FA-bug fix.
  2. Among assigning sources, higher AUTHORITY wins (`SOURCE_AUTHORITY`):
        nflverse > sleeper > espn
     nflverse rosters are canonical NFL truth; Sleeper is fantasy player metadata;
     ESPN is unofficial/fragile ("never the player backbone" — league_sync D1).
  3. Ties broken by RECENCY — the freshest `as_of` wins ("freshest authoritative
     source wins").

The validation gate (`validate_publish`) is a pure, idempotent function: too many
unassigned players OR too many cross-source mismatches raises `PublishBlocked`
(non-zero signal) carrying the offending players.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .model import PublishBlocked, TeamObservation, TeamResolution

# Authority rank per source (higher wins). Unknown sources rank 0.
SOURCE_AUTHORITY: dict[str, int] = {"nflverse": 3, "sleeper": 2, "espn": 1}

# Publish-gate defaults (fractions of the reconciled set).
MAX_UNASSIGNED_FRAC = 0.10
MAX_MISMATCH_FRAC = 0.05

# Tokens (upper-cased) that mean "no team" — a free agent / unassigned player.
_UNASSIGNED = {"", "FA", "FA*", "NONE", "FREE AGENT", "N/A"}

# Canonicalize cross-source abbreviation drift so it does not read as a mismatch.
_TEAM_ALIASES = {
    "JAC": "JAX", "WSH": "WAS", "LA": "LAR", "SD": "LAC", "OAK": "LV",
    "STL": "LAR", "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU",
    "KCC": "KC", "TBB": "TB", "GBP": "GB", "NEP": "NE", "NOS": "NO", "SFO": "SF",
}


def canon_team(team: str | None) -> str | None:
    """Uppercase + de-alias a team abbrev; None for any unassigned marker."""
    if team is None:
        return None
    t = team.strip().upper()
    if t in _UNASSIGNED:
        return None
    return _TEAM_ALIASES.get(t, t)


def _recency(o: TeamObservation) -> float:
    """Sortable recency; a missing `as_of` is treated as the oldest time."""
    return o.as_of.timestamp() if o.as_of is not None else 0.0


def _resolve(player_id: str, obs: list[TeamObservation]) -> TeamResolution:
    teamed = [(o, t) for o in obs if (t := canon_team(o.team)) is not None]
    considered = len(obs)
    if not teamed:
        return TeamResolution(player_id, None, 0.0, "", considered, False)
    # Precedence: authority first, recency as tie-breaker.
    winner, team = max(
        teamed, key=lambda ot: (SOURCE_AUTHORITY.get(ot[0].source, 0), _recency(ot[0]))
    )
    agree = sum(1 for _, t in teamed if t == team)
    distinct = {t for _, t in teamed}
    return TeamResolution(
        player_id=player_id,
        team=team,
        confidence=round(agree / len(teamed), 4),
        source=winner.source,
        sources_considered=considered,
        mismatch=len(distinct) > 1,
    )


def reconcile_teams(observations: Iterable[TeamObservation]) -> list[TeamResolution]:
    """Resolve every player's NFL team from all source observations.

    Deterministic: results are ordered by `player_id`. Pure — same input, same
    output, no side effects (safe to call repeatedly in a publish pipeline).
    """
    by_player: dict[str, list[TeamObservation]] = defaultdict(list)
    for o in observations:
        by_player[o.player_id].append(o)
    return [_resolve(pid, obs) for pid, obs in sorted(by_player.items())]


def validate_publish(
    resolutions: Iterable[TeamResolution],
    *,
    max_unassigned: float = MAX_UNASSIGNED_FRAC,
    max_mismatch: float = MAX_MISMATCH_FRAC,
) -> list[TeamResolution]:
    """Publish gate: raise `PublishBlocked` if the reconciled set is too dirty.

    Blocks when the unassigned fraction exceeds `max_unassigned` OR the mismatch
    fraction exceeds `max_mismatch`. Returns the resolutions unchanged on pass, so
    it drops into a publish flow as `snapshot = validate_publish(reconcile_teams(...))`.
    Idempotent: pure check, mutates nothing.
    """
    resolutions = list(resolutions)
    total = len(resolutions)
    if total == 0:
        return resolutions
    unassigned = [r.player_id for r in resolutions if r.team is None]
    mismatched = [r.player_id for r in resolutions if r.mismatch]
    u_frac = len(unassigned) / total
    m_frac = len(mismatched) / total
    if u_frac > max_unassigned or m_frac > max_mismatch:
        raise PublishBlocked(
            f"publish blocked: {len(unassigned)}/{total} unassigned ({u_frac:.1%} > "
            f"{max_unassigned:.1%}), {len(mismatched)}/{total} cross-source mismatch "
            f"({m_frac:.1%} > {max_mismatch:.1%})",
            unassigned=unassigned,
            mismatched=mismatched,
        )
    return resolutions
