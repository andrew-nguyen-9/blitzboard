"""`AvailabilityModel` — the player availability truth layer: one number per player-week.

THE NUMBER (every downstream unit consumes this; write it down once, here):

    p_startable(player, week)
      = P(the player is on an NFL active roster that week, dresses, and takes at least
         10% of his team's offensive snaps — given his team plays that week)

Not "is he injured". Not "does he have a team". Both of those are *inputs*. A healthy,
rostered RB3 buried on the depth chart has a low `p_startable`, and so does a retired
star, an unsigned free agent, a practice-squad body and a player on IR — because none of
them will take a snap for you. This is the fix for "the autodraft drafts players who will
not take a snap all season".

FIVE FACTORS, in precedence order (later ones can only pull the number down):

    base      the fitted `DiscreteTimeHazard` P(available) — or `neutral_p` (1.0) unfitted
    report    live injury-report designation `STATUS_P` (OUT→0, QUESTIONABLE→0.5, …); an
              explicit report OVERRIDES the statistical base for the week it covers, because
              it is a human game-time signal about this specific player
    usage     `usage_p(depth_rank, snap_share)` — the empirical, data-derived term (below)
    roster    `ROSTER_STATE_P[state]` — the ceiling a roster state puts on playing at all
    suspension  a truthy `suspended` flag forces 0 (certainty beats every model)

DEGRADE, NEVER CRASH, NEVER SILENTLY ZERO: every factor defaults to 1.0 when its column is
absent/blank/unparseable, and the absence is logged once per model per column. A frame with
no signals at all returns 1.0 for everyone (a pure no-op passthrough) — a missing source can
only ever *fail to help*, it can never invent unavailability. Unknown status strings and
unknown roster states resolve to "no signal", not to zero.

WHERE THE NUMBERS COME FROM — every constant in this module is now FITTED on ingested
nflverse data (2026-08 refit; the first cut shipped `ROSTER_STATE_P`/`DEPTH_RANK_P` as stated
priors because no roster or depth-chart feed existed yet — e9b then ingested them). Three
estimators, each re-runnable against the store, each named in the constant it produced:

    fit_roster_state_priors(weekly_rosters, snap_counts, player_ids)  -> ROSTER_STATE_P
    fit_depth_rank_priors(depth_charts,  snap_counts, player_ids)     -> DEPTH_RANK_P
    fit_usage_priors(snap_counts)                                     -> SNAP_SHARE_P, SNAP_RANK_P

    from blitz_engine.store import ParquetStore
    s = ParquetStore.open("~/.blitz_engine")
    fit_roster_state_priors(s.table("weekly_rosters").df(), s.table("snap_counts").df(),
                            s.table("player_ids").df())
    fit_usage_priors(s.table("snap_counts").df().rename(columns={"offense_pct": "snap_share",
                     "pfr_player_id": "player_id"}))

Two ceilings remain STATED PRIORS because the feed has no code for them at all: NFI and
HOLDOUT. They are marked `PRIOR:` inline in `ROSTER_STATE_P`; everything else is marked
`FITTED` with its raw rate and sample size.

THE JOIN, measured by e9b, not guessed: the status feeds (`weekly_rosters`, `depth_charts`,
`injuries`) key on `gsis_id`, `snap_counts` keys on `pfr_player_id`, and the ONLY sanctioned
bridge is the `player_ids` crosswalk (80.8% of snap_counts' distinct pfr ids).
`weekly_rosters.pfr_id` reaches only 55.0% — `gsis_to_pfr` exists so nobody re-derives this
by hand. Unbridged players are dropped from the FIT (never scored as "took no snaps") and
read as *missing status* at runtime, i.e. degrade-neutral, not healthy.

`ponytail:` one probability, four factors, no availability "subsystem" — the legacy
`p_available` name is kept as the alias downstream already imports.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import pandas as pd

from blitz_engine.survival.hazard import DiscreteTimeHazard

__all__ = [
    "DEPTH_RANK_P",
    "DEPTH_RANK_TAIL_P",
    "ROSTER_ACTIVITY_ORDER",
    "ROSTER_STATE_P",
    "SEASON_LONG_ZERO_STATES",
    "SNAP_RANK_P",
    "SNAP_RANK_TAIL_P",
    "SNAP_SHARE_P",
    "STATUS_P",
    "ZERO_AVAILABILITY_EPS",
    "AvailabilityModel",
    "RosterState",
    "collapse_roster_weeks",
    "depth_rank_p",
    "fit_depth_rank_priors",
    "fit_roster_state_priors",
    "fit_usage_priors",
    "gsis_to_pfr",
    "is_effectively_unavailable",
    "is_season_long_zero",
    "normalize_depth_charts",
    "resolve_roster_state",
    "resolve_status_p",
    "roster_state_p",
    "snap_share_p",
    "unavailable_ids",
    "usage_p",
]

log = logging.getLogger(__name__)

#: Injury-report designation → P(available) that week. Missing/blank ⇒ defer to the hazard.
#: Keys are upper-cased on lookup so "Out"/"out"/"OUT" all resolve.
STATUS_P: dict[str, float] = {
    "ACTIVE": 1.0,
    "HEALTHY": 1.0,
    "PROBABLE": 0.95,
    "QUESTIONABLE": 0.5,
    "DOUBTFUL": 0.10,
    "OUT": 0.0,
    "INACTIVE": 0.0,
    "DNP": 0.0,
    "IR": 0.0,
    "PUP": 0.0,
    "NFI": 0.0,
    "SUSP": 0.0,
    "SUSPENDED": 0.0,
}

#: Below this, a player is "effectively unavailable" — the draft must never take him.
#: 0.01 = under one startable week per two seasons; see `is_effectively_unavailable`.
ZERO_AVAILABILITY_EPS = 0.01


class RosterState(StrEnum):
    """Every roster state the availability layer must cover (brief §1)."""

    ROSTERED = "ROSTERED"              # on the 53, active
    INACTIVE = "INACTIVE"             # on the 53 but a game-day scratch (feed: INA / abbr I0x)
    PRACTICE_SQUAD = "PRACTICE_SQUAD"
    IR = "IR"
    PUP = "PUP"
    NFI = "NFI"
    SUSPENDED = "SUSPENDED"
    HOLDOUT = "HOLDOUT"
    CAMP_BODY = "CAMP_BODY"           # camp/tryout/waived — never made a 53
    FREE_AGENT = "FREE_AGENT"         # unsigned, no NFL team
    RETIRED = "RETIRED"


#: Roster state → the CEILING it places on `p_startable` for a given week, i.e. the state's
#: startable rate RELATIVE to being active (`P(startable | state) / P(startable | ROSTERED)`),
#: which is what makes it a multiplicative factor next to `usage_p`.
#:
#: FITTED (`fit_roster_state_priors`, on nflverse `weekly_rosters` × `snap_counts` 2014-2025,
#: REG, QB/RB/WR/TE, one row per player-week after `collapse_roster_weeks`) — see the values
#: and sample sizes in that function's docstring. ROSTERED is the 1.0 reference by definition.
#: NFI and HOLDOUT have no feed code at all and remain STATED PRIORS, marked `PRIOR:` below.
#: Format below: value = ceiling; comment = the RAW measured startable rate and sample size.
ROSTER_STATE_P: dict[RosterState, float] = {
    RosterState.ROSTERED: 1.0,           # FITTED reference: raw .7305, n=87,611
    RosterState.INACTIVE: 0.0011,        # FITTED raw .0008, n=9,555 — a game-day scratch
    RosterState.PRACTICE_SQUAD: 0.0043,  # FITTED raw .0031, n=19,907 — elevations rarely
    #                                    # clear the 10% snap bar (the old 0.06 prior was 14x
    #                                    # too generous, and kept PS bodies above the eps)
    RosterState.IR: 0.0012,              # FITTED raw .0009, n=13,228
    RosterState.PUP: 0.0,                # FITTED raw .0000, n=321
    RosterState.NFI: 0.0,                # PRIOR: no NFI code in `weekly_rosters`; by rule NFI
    #                                    # is the same minimum-4-week ineligibility as PUP
    RosterState.SUSPENDED: 0.0091,       # FITTED raw .0066, n=301 (SUS + exempt list)
    RosterState.HOLDOUT: 0.05,           # PRIOR: no holdout code in the feed. Most holdouts
    #                                    # end, but not for the week they are holding out
    RosterState.CAMP_BODY: 0.013,        # FITTED raw .0095, n=9,468 — cut/waived/not-with-team
    RosterState.FREE_AGENT: 0.0,         # FITTED raw .0000, but n=52 only: an unsigned player
    #                                    # is absent from a *roster* feed by construction, so
    #                                    # this stays the structural zero. THE BUG FIX.
    RosterState.RETIRED: 0.0,            # FITTED raw .0000, n=528
}

#: Most-active → least-active. `collapse_roster_weeks` uses this to pick ONE row when a
#: player-week carries several (transaction rows: ACT + TRC + TRD all key-distinct because
#: `status` is part of `weekly_rosters`' key — e9b). Without it every transaction week is
#: double-counted in the fit.
ROSTER_ACTIVITY_ORDER: tuple[RosterState, ...] = (
    RosterState.ROSTERED,
    RosterState.INACTIVE,
    RosterState.PRACTICE_SQUAD,
    RosterState.HOLDOUT,
    RosterState.IR,
    RosterState.PUP,
    RosterState.NFI,
    RosterState.SUSPENDED,
    RosterState.CAMP_BODY,
    RosterState.FREE_AGENT,
    RosterState.RETIRED,
)

#: States that mean "no snaps for anyone, all season" — the ones a *draft board* must sink
#: outright. Weekly-zero states (IR/PUP/NFI/SUSPENDED) are NOT here: those players are still
#: worth a late pick, they just score nothing while designated.
SEASON_LONG_ZERO_STATES = frozenset(
    {RosterState.RETIRED, RosterState.FREE_AGENT, RosterState.CAMP_BODY}
)

#: Raw feed spellings → `RosterState`. nflverse/PFR/ESPN all disagree; be liberal.
_ROSTER_ALIASES: dict[str, RosterState] = {
    "ACT": RosterState.ROSTERED, "ACTIVE": RosterState.ROSTERED,
    "ROSTERED": RosterState.ROSTERED, "RES/ACT": RosterState.ROSTERED,
    "A01": RosterState.ROSTERED, "HEALTHY": RosterState.ROSTERED,
    "PS": RosterState.PRACTICE_SQUAD, "PRACTICE SQUAD": RosterState.PRACTICE_SQUAD,
    "DEV": RosterState.PRACTICE_SQUAD, "P01": RosterState.PRACTICE_SQUAD,
    "IR": RosterState.IR, "RES/INJ": RosterState.IR, "INJURED RESERVE": RosterState.IR,
    "RESERVE/INJURED": RosterState.IR, "R01": RosterState.IR,
    "PUP": RosterState.PUP, "RES/PUP": RosterState.PUP, "RESERVE/PUP": RosterState.PUP,
    "PHYSICALLY UNABLE TO PERFORM": RosterState.PUP,
    "NFI": RosterState.NFI, "RES/NFI": RosterState.NFI, "RESERVE/NFI": RosterState.NFI,
    "NON-FOOTBALL INJURY": RosterState.NFI, "NON FOOTBALL INJURY": RosterState.NFI,
    "SUSP": RosterState.SUSPENDED, "SUSPENDED": RosterState.SUSPENDED,
    "EXE/SUSP": RosterState.SUSPENDED, "RES/SUSP": RosterState.SUSPENDED,
    "HOLDOUT": RosterState.HOLDOUT, "EXE/HOLDOUT": RosterState.HOLDOUT,
    "RES/HOLDOUT": RosterState.HOLDOUT, "DID NOT REPORT": RosterState.HOLDOUT,
    "CAMP": RosterState.CAMP_BODY, "CAMP BODY": RosterState.CAMP_BODY,
    "TRYOUT": RosterState.CAMP_BODY, "WAIVED": RosterState.CAMP_BODY,
    "CUT": RosterState.CAMP_BODY, "RELEASED": RosterState.CAMP_BODY,
    "UDFA": RosterState.CAMP_BODY,
    "FA": RosterState.FREE_AGENT, "UFA": RosterState.FREE_AGENT,
    "RFA": RosterState.FREE_AGENT, "ERFA": RosterState.FREE_AGENT,
    "FREE AGENT": RosterState.FREE_AGENT, "UNSIGNED": RosterState.FREE_AGENT,
    "UNRESTRICTED FREE AGENT": RosterState.FREE_AGENT,
    "RET": RosterState.RETIRED, "RETIRED": RosterState.RETIRED,
    "RES/RET": RosterState.RETIRED, "RESERVE/RETIRED": RosterState.RETIRED,
    "EXE/RET": RosterState.RETIRED,
    # nflverse `weekly_rosters.status` verbs (e9b) not already covered above.
    "INA": RosterState.INACTIVE, "INACTIVE": RosterState.INACTIVE,
    "RES": RosterState.IR,          # bare reserve; `status_description_abbr` refines which kind
    "SUS": RosterState.SUSPENDED, "EXE": RosterState.SUSPENDED,  # exempt list = ineligible
    "NWT": RosterState.CAMP_BODY,   # "not with team"
    "TRC": RosterState.ROSTERED, "TRD": RosterState.ROSTERED,    # trade transaction rows:
    "TRT": RosterState.ROSTERED,    # still on a 53; the abbr below says whether he dressed
}

#: `weekly_rosters.status_description_abbr` family letter → the state it refines a status verb
#: into (e9b's vocabulary: A01 active, P0x practice squad, I0x injured/inactive, R0x-R6x
#: reserve, W03 waived, E0x/E1x exempt). The abbr is the RESULTING designation, so it wins
#: over the ambiguous transaction verbs (`_ABBR_REFINABLE`) and loses to every verb that is
#: already a fact about the week. All three exclusions were measured, not assumed:
#:   * ACT+I01 (n=1,611) is 0.004 startable → the abbr must be able to demote an "active".
#:   * RES+A01 (n=1,173) is 0.613 → an activation off reserve; the abbr must promote it.
#:   * INA+A01 (n=6,942) is 0.000 → INACTIVE is a GAME-DAY fact, so it is NOT refinable;
#:     letting "A01" promote it back to ROSTERED dropped the fitted ROSTERED rate .734 → .677.
#:   * RET+R02 stays RETIRED (season-long) instead of collapsing into plain reserve.
_ABBR_ALIASES: dict[str, RosterState] = {
    "A": RosterState.ROSTERED,
    "P": RosterState.PRACTICE_SQUAD,
    "I": RosterState.INACTIVE,
    "R": RosterState.IR,
    "W": RosterState.CAMP_BODY,
    "E": RosterState.SUSPENDED,
}
#: The transaction verbs whose meaning the abbr may override (see the note above).
_ABBR_REFINABLE = frozenset(
    {RosterState.ROSTERED, RosterState.IR, RosterState.PRACTICE_SQUAD}
)

#: Depth rank as PUBLISHED BY THE TEAM (`depth_charts.depth_team` / 2025 `pos_rank`) →
#: P(≥10% of his team's offensive snaps that week | his team plays). Ranks 1-3 are FITTED
#: (`fit_depth_rank_priors`, nflverse `depth_charts` × `snap_counts` 2014-2024 REG,
#: QB/RB/WR/TE; n = 31,298 / 29,392 / 17,751). The published chart never goes past 3, so
#: ranks 4+ continue the ladder in the ratios of `SNAP_RANK_P` — same ordering, measured on
#: a different estimator, rescaled to rank 3 so the sequence stays monotone.
DEPTH_RANK_P: dict[int, float] = {1: 0.896, 2: 0.625, 3: 0.416, 4: 0.379, 5: 0.261, 6: 0.150}
#: Rank 7 and deeper: a "camp body on the depth chart", extended the same way.
DEPTH_RANK_TAIL_P = 0.052

#: The OTHER ladder: rank by trailing offensive snap share within (season, week, team,
#: position) → P(plays next week). FITTED by `fit_usage_priors` on `snap_counts` 2014-2025
#: (n=71,404). Used only to extend `DEPTH_RANK_P` past the published chart's rank 3.
SNAP_RANK_P: dict[int, float] = {1: 0.942, 2: 0.831, 3: 0.651, 4: 0.593, 5: 0.408, 6: 0.234}
SNAP_RANK_TAIL_P = 0.081

#: Trailing offensive snap share, in 10-point bands (index = floor(share*10)) → the same
#: next-week play probability. FITTED alongside `DEPTH_RANK_P` on the same 2014-2025 rows.
SNAP_SHARE_P: tuple[float, ...] = (
    0.262, 0.613, 0.784, 0.860, 0.893, 0.911, 0.928, 0.941, 0.952, 0.953,
)

#: What `usage_p` returns when NEITHER depth rank nor snap share is known: 1.0, i.e. the
#: usage factor is a no-op. Degrade-neutral by construction (brief §3).
DEFAULT_USAGE_P = 1.0


def resolve_status_p(status: object, table: Mapping[str, float] = STATUS_P) -> float | None:
    """Map a raw report status to P(available), or ``None`` to defer to the hazard model."""
    if status is None:
        return None
    s = str(status).strip().upper()
    if not s or s in {"NAN", "NA", "NONE"}:
        return None
    return table.get(s)


def _clean(value: object) -> str:
    """Feed cell → an upper-cased token, or "" for every flavour of missing."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = str(value).strip().upper()
    return "" if s in {"NAN", "NA", "NONE", "UNKNOWN"} else s


def resolve_roster_state(status: object, abbr: object = None) -> RosterState | None:
    """Raw feed status (+ optional `status_description_abbr`) → `RosterState`.

    ``None`` is "no signal", never a state: an unparseable string must not sink a player.
    `abbr` is nflverse's transaction detail code; it refines only the ambiguous verbs
    (ACT/RES/DEV/INA and the TR* trade rows) — see `_ABBR_ALIASES`.
    """
    if isinstance(status, RosterState):
        state: RosterState | None = status
    else:
        s = _clean(status)
        state = (_ROSTER_ALIASES.get(s) or _ROSTER_ALIASES.get(s.replace("_", " "))) if s else None
    a = _clean(abbr)
    refined = _ABBR_ALIASES.get(a[0]) if a else None
    if refined is not None and (state is None or state in _ABBR_REFINABLE):
        return refined
    return state


def roster_state_p(status: object, *, default: float = 1.0, abbr: object = None) -> float:
    """Roster-state ceiling on `p_startable`; `default` (1.0, neutral) when unknown."""
    state = resolve_roster_state(status, abbr)
    return default if state is None else ROSTER_STATE_P[state]


def is_season_long_zero(status: object, abbr: object = None) -> bool:
    """Is this roster state "zero snaps all season" (retired / unsigned FA / camp body)?

    The predicate the draft board uses to SINK a player outright, as opposed to the
    weekly-zero designations (IR/PUP/NFI/suspension) which are merely worth less.
    """
    state = resolve_roster_state(status, abbr)
    return state is not None and state in SEASON_LONG_ZERO_STATES


def depth_rank_p(rank: object) -> float | None:
    """Depth rank → empirical P(plays). ``None`` when the rank is missing/nonsensical."""
    if rank is None:
        return None
    try:
        r = int(rank)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if r < 1:
        return None
    return DEPTH_RANK_P.get(r, DEPTH_RANK_TAIL_P)


def snap_share_p(share: object) -> float | None:
    """Trailing snap share → empirical P(plays). ``None`` when missing/unparseable.

    Accepts either a fraction (0.62) or a percentage (62.0) — feeds disagree.
    """
    if share is None:
        return None
    try:
        x = float(share)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if np.isnan(x) or x < 0:
        return None
    if x > 1.0:
        x = x / 100.0
    band = min(int(x * 10), len(SNAP_SHARE_P) - 1)
    return SNAP_SHARE_P[band]


def usage_p(depth_rank: object = None, snap_share: object = None) -> float:
    """Combine depth rank + snap share into ONE "will he be on the field" probability.

    Both are noisy estimates of the same latent quantity (next-week playing time), so the
    two available estimates are AVERAGED rather than multiplied — multiplying would double-
    count one fact and drive a genuine starter to 0.9². Either signal alone is used as-is;
    neither → `DEFAULT_USAGE_P` (1.0, a no-op), which is the degrade-safe default.
    """
    parts = [p for p in (depth_rank_p(depth_rank), snap_share_p(snap_share)) if p is not None]
    return float(np.mean(parts)) if parts else DEFAULT_USAGE_P


def is_effectively_unavailable(p: float) -> bool:
    """**The predicate e8 asserts on**: this player must never be drafted.

    True iff `p_startable` < `ZERO_AVAILABILITY_EPS` (0.01). Retired players, unsigned free
    agents, IR/PUP/NFI/suspended players and camp bodies all land here; a healthy RB3
    (~0.65) and even a deep RB6 (~0.24) do not — they are bad picks, not impossible ones.
    """
    return float(p) < ZERO_AVAILABILITY_EPS


def unavailable_ids(p_by_player: Mapping[str, float] | pd.Series) -> list[str]:
    """Every player id whose availability is effectively zero, in input order."""
    return [str(k) for k, v in p_by_player.items() if is_effectively_unavailable(v)]


def gsis_to_pfr(crosswalk: pd.DataFrame) -> dict[str, str]:
    """`player_ids` crosswalk → {gsis_id: pfr_player_id}. **The only sanctioned bridge.**

    The status feeds (`weekly_rosters`, `depth_charts`, `injuries`) key on `gsis_id`;
    `snap_counts` keys on `pfr_player_id`. e9b MEASURED the two candidate bridges: this one
    reaches 80.8% of snap_counts' distinct pfr ids, `weekly_rosters.pfr_id` only 55.0% — so
    never bridge through the roster column. `player_ids.gsis_id` is NULL on 4,480/12,480
    rows (non-NFL players) and must be dropped, or the map keys on the string "nan".
    """
    if not {"gsis_id", "pfr_id"} <= set(crosswalk.columns):
        log.warning("gsis_to_pfr: crosswalk lacks gsis_id/pfr_id — no bridge, statuses unjoined")
        return {}
    cw = crosswalk.dropna(subset=["gsis_id", "pfr_id"])
    return dict(zip(cw["gsis_id"].astype(str), cw["pfr_id"].astype(str), strict=True))


def normalize_depth_charts(depth: pd.DataFrame) -> pd.DataFrame:
    """`depth_charts` (EITHER of its two schemas) → season, week, team, gsis_id, position, rank.

    e9b's table holds two different feeds stacked in one file: 2014-2024 nflverse rows
    (season/week/club_code/formation/depth_position/`depth_team`, ranks 1-3) and 2025 ESPN
    snapshot rows (`dt` timestamp, no season/week, team/pos_grp/`pos_abb`/`pos_rank`). Split
    on `season IS NULL`, not on the year. The 2025 half yields NaN week — usable for "his
    current depth rank", not joinable to a game week, which is why the fit ignores it.
    """
    if depth.empty:
        return pd.DataFrame(columns=["season", "week", "team", "gsis_id", "position", "depth_rank"])
    has = set(depth.columns)
    old_mask = depth["season"].notna() if "season" in has else pd.Series(False, index=depth.index)
    parts = []
    if old_mask.any():
        o = depth.loc[old_mask]
        parts.append(pd.DataFrame({
            "season": pd.to_numeric(o["season"], errors="coerce"),
            "week": pd.to_numeric(o["week"], errors="coerce"),
            "team": o["club_code"] if "club_code" in has else o.get("team"),
            "gsis_id": o["gsis_id"].astype(str),
            "position": o["depth_position"] if "depth_position" in has else o.get("position"),
            "depth_rank": pd.to_numeric(o["depth_team"], errors="coerce"),
            "game_type": o["game_type"] if "game_type" in has else "REG",
        }))
    new_mask = depth["dt"].notna() if "dt" in has else pd.Series(False, index=depth.index)
    new_mask &= ~old_mask
    if new_mask.any():
        n = depth.loc[new_mask]
        parts.append(pd.DataFrame({
            "season": np.nan, "week": np.nan,
            "team": n.get("team"),
            "gsis_id": n["gsis_id"].astype(str),
            "position": n["pos_abb"] if "pos_abb" in has else n.get("position"),
            "depth_rank": pd.to_numeric(n["pos_rank"], errors="coerce"),
            "game_type": "REG",
        }))
    if not parts:
        return pd.DataFrame(columns=["season", "week", "team", "gsis_id", "position", "depth_rank"])
    return pd.concat(parts, ignore_index=True)


def collapse_roster_weeks(rosters: pd.DataFrame) -> pd.DataFrame:
    """One row per (season, week, team, player) — the MOST ACTIVE state that week wins.

    `weekly_rosters` puts `status` IN its key (e9b), so a player who was traded or
    activated mid-week appears two to four times (ACT + TRC + TRD…). Counting all of them
    would credit an active player's snaps to the transaction row's state as well.
    """
    keys = [c for c in ("season", "week", "team", "player_id") if c in rosters.columns]
    if not keys or "state" not in rosters.columns:
        return rosters
    order = {s: i for i, s in enumerate(ROSTER_ACTIVITY_ORDER)}
    df = rosters.assign(_rank=[order.get(s, len(order)) for s in rosters["state"]])
    ranked = df.sort_values("_rank", kind="stable")
    return ranked.drop_duplicates(keys, keep="first").drop(columns="_rank")


def _snap_share_index(
    snaps: pd.DataFrame, *, game_type: str
) -> tuple[dict[tuple[int, int, str], float], set[tuple[int, int, str]]]:
    """`snap_counts` → ({(season, week, pfr_id): offensive snap share}, team-weeks played).

    The team-week set is the "given his team plays that week" conditioner in the definition
    of `p_startable`: without it, byes and season-end read as "did not play".
    """
    s = snaps
    if "game_type" in s.columns:
        s = s.loc[s["game_type"] == game_type]
    season = pd.to_numeric(s["season"], errors="coerce").astype("Int64")
    week = pd.to_numeric(s["week"], errors="coerce").astype("Int64")
    pct = pd.to_numeric(s["offense_pct"], errors="coerce").fillna(0.0)
    played = set(zip(season, week, s["team"].astype(str), strict=True))
    share: dict[tuple[int, int, str], float] = {}
    for key, v in zip(
        zip(season, week, s["pfr_player_id"].astype(str), strict=True), pct, strict=True
    ):
        share[key] = max(share.get(key, 0.0), float(v))
    return share, played


def _attach_startable(
    frame: pd.DataFrame,
    snaps: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    gsis_col: str,
    threshold: float,
    game_type: str,
) -> pd.DataFrame:
    """Restrict `frame` to played team-weeks, bridge gsis→pfr, add a `startable` flag.

    Rows with no bridge are DROPPED, not scored 0 — e9b measured that ~19% of snap_counts
    players have no crosswalk row, and treating "no bridge" as "took no snaps" would smear
    a fake zero across every state.
    """
    share, played = _snap_share_index(snaps, game_type=game_type)
    bridge = gsis_to_pfr(crosswalk)
    f = frame
    if "game_type" in f.columns:
        f = f.loc[f["game_type"].fillna(game_type) == game_type]
    f = f.assign(
        season=pd.to_numeric(f["season"], errors="coerce").astype("Int64"),
        week=pd.to_numeric(f["week"], errors="coerce").astype("Int64"),
        team=f["team"].astype(str),
        _pfr=f[gsis_col].astype(str).map(bridge),
    )
    f = f.loc[f["_pfr"].notna()]
    keys = list(zip(f["season"], f["week"], f["team"], strict=True))
    f = f.loc[[k in played for k in keys]]
    f["startable"] = [
        1.0 if share.get((s, w, p), 0.0) >= threshold else 0.0
        for s, w, p in zip(f["season"], f["week"], f["_pfr"], strict=True)
    ]
    return f


def fit_roster_state_priors(
    rosters: pd.DataFrame,
    snaps: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    threshold: float = 0.10,
    game_type: str = "REG",
    positions: tuple[str, ...] = ("QB", "RB", "WR", "TE"),
    min_n: int = 25,
) -> dict[str, object]:
    """Re-derive `ROSTER_STATE_P` from `weekly_rosters` × `snap_counts` × `player_ids`.

    The estimator behind the baked ceilings. For each `RosterState` it measures the raw
    rate P(≥`threshold` of his team's offensive snaps that week | his team plays), then
    divides by the ROSTERED rate so the result is a multiplicative ceiling with ROSTERED=1.

    Reproduce (this is exactly how the baked values were produced)::

        from blitz_engine.store import ParquetStore
        s = ParquetStore.open("~/.blitz_engine")
        fit_roster_state_priors(s.table("weekly_rosters").df(), s.table("snap_counts").df(),
                                s.table("player_ids").df())

    Measured 2014-2025 (raw rate, n): ROSTERED .7305/87,611 · INACTIVE .0008/9,555 ·
    PRACTICE_SQUAD .0031/19,907 · IR .0009/13,228 · PUP .0000/321 · SUSPENDED .0066/301 ·
    CAMP_BODY .0095/9,468 · RETIRED .0000/528 · FREE_AGENT .0000/52. States under `min_n`
    (and NFI/HOLDOUT, which have no feed code at all) keep their baked value.
    """
    need = {"season", "week", "team", "player_id", "status"}
    if snaps.empty or not need <= set(rosters.columns):
        log.warning(
            "fit_roster_state_priors: unusable frames (missing %s) — keeping baked ceilings",
            sorted(need - set(rosters.columns)),
        )
        return {"roster_state_p": dict(ROSTER_STATE_P), "raw": {}, "n": {}}

    df = rosters
    if "position" in df.columns and positions:
        df = df.loc[df["position"].isin(positions)]
    abbr = (
        df["status_description_abbr"]
        if "status_description_abbr" in df.columns
        else pd.Series(None, index=df.index, dtype=object)
    )
    df = df.assign(state=[
        resolve_roster_state(s, a) for s, a in zip(df["status"], abbr, strict=True)
    ])
    df = collapse_roster_weeks(df.loc[df["state"].notna()])
    df = _attach_startable(
        df, snaps, crosswalk, gsis_col="player_id", threshold=threshold, game_type=game_type
    )

    by_state = df.groupby(df["state"].astype(str))["startable"]
    raw = {k: float(v) for k, v in by_state.mean().items()}
    n = {k: int(v) for k, v in by_state.size().items()}
    ref = raw.get(str(RosterState.ROSTERED), 0.0)
    fitted = dict(ROSTER_STATE_P)
    if ref > 0:
        for state in RosterState:
            key = str(state)
            if n.get(key, 0) >= min_n:
                fitted[state] = round(min(raw[key] / ref, 1.0), 4)
        fitted[RosterState.ROSTERED] = 1.0
    else:
        log.warning("fit_roster_state_priors: no ROSTERED reference rate — keeping baked ceilings")
    return {"roster_state_p": fitted, "raw": raw, "n": n}


def fit_depth_rank_priors(
    depth: pd.DataFrame,
    snaps: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    threshold: float = 0.10,
    game_type: str = "REG",
    positions: tuple[str, ...] = ("QB", "RB", "WR", "TE"),
    min_n: int = 100,
) -> dict[str, object]:
    """Re-derive `DEPTH_RANK_P` from the real `depth_charts` feed (ranks 1-3).

    Same shape as `fit_roster_state_priors`. Reproduce::

        fit_depth_rank_priors(s.table("depth_charts").df(), s.table("snap_counts").df(),
                              s.table("player_ids").df())

    Measured 2014-2024 REG, QB/RB/WR/TE (rate, n): rank 1 .896/31,298 · 2 .625/29,392 ·
    3 .416/17,751. The published nflverse depth chart only ever carries `depth_team` 1-3,
    and its 2025 successor schema has no game week to join on (`normalize_depth_charts`),
    so ranks ≥4 are NOT fitted here — they come from `fit_usage_priors`' snap-rank ladder,
    floored to stay monotone under rank 3.
    """
    if depth.empty or snaps.empty:
        log.warning("fit_depth_rank_priors: empty frame — keeping baked priors")
        return {"depth_rank_p": dict(DEPTH_RANK_P), "n": {}}
    d = normalize_depth_charts(depth)
    d = d.loc[d["week"].notna() & d["season"].notna() & d["depth_rank"].notna()]
    if positions:
        d = d.loc[d["position"].isin(positions)]
    d = d.drop_duplicates(["season", "week", "team", "gsis_id"])
    d = _attach_startable(
        d, snaps, crosswalk, gsis_col="gsis_id", threshold=threshold, game_type=game_type
    )
    by_rank = d.groupby(d["depth_rank"].astype(int))["startable"]
    rates = {int(k): round(float(v), 3) for k, v in by_rank.mean().items()}
    n = {int(k): int(v) for k, v in by_rank.size().items()}
    fitted = {r: p for r, p in rates.items() if n.get(r, 0) >= min_n}
    if not fitted:
        log.warning("fit_depth_rank_priors: no rank cleared min_n=%d — keeping baked", min_n)
        return {"depth_rank_p": dict(DEPTH_RANK_P), "tail_p": DEPTH_RANK_TAIL_P, "raw": rates,
                "n": n}
    deepest = max(fitted)
    anchor = fitted[deepest] / SNAP_RANK_P[min(deepest, max(SNAP_RANK_P))]
    extend = {r: round(anchor * p, 3) for r, p in SNAP_RANK_P.items() if r > deepest}
    return {
        "depth_rank_p": fitted | extend,
        "tail_p": round(anchor * SNAP_RANK_TAIL_P, 3),
        "raw": rates,
        "n": n,
    }


def fit_usage_priors(
    snaps: pd.DataFrame,
    *,
    threshold: float = 0.10,
    max_rank: int = 6,
    positions: tuple[str, ...] = ("QB", "RB", "WR", "TE"),
) -> dict[str, object]:
    """Re-derive `DEPTH_RANK_P` / `SNAP_SHARE_P` from an ingested `snap_counts` frame.

    The estimator behind the baked constants (module docstring shows the invocation).
    Needs columns `season, week, team, position, player_id, snap_share`; ranks players
    within (season, week, team, position) by snap share, keeps only rows whose team also
    plays the FOLLOWING week (byes and season-end would otherwise read as "did not play"),
    and reports the share of those players who clear `threshold` snaps that next week.
    """
    need = {"season", "week", "team", "position", "player_id", "snap_share"}
    missing = need - set(snaps.columns)
    if missing or snaps.empty:
        log.warning(
            "fit_usage_priors: unusable snap frame (missing %s) — keeping baked priors",
            sorted(missing),
        )
        return {"depth_rank_p": dict(DEPTH_RANK_P), "snap_share_p": list(SNAP_SHARE_P), "n": 0}

    df = snaps.loc[snaps["position"].isin(positions)].copy()
    df["snap_share"] = pd.to_numeric(df["snap_share"], errors="coerce").fillna(0.0)
    df["depth"] = (
        df.groupby(["season", "week", "team", "position"])["snap_share"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    trio = list(zip(df["season"], df["week"], df["team"], strict=True))
    team_weeks = set(trio)
    nxt = dict(zip(list(zip(df["season"], df["week"], df["player_id"], strict=True)),
                   df["snap_share"], strict=True))
    df = df.loc[[(s, w + 1, t) in team_weeks for s, w, t in trio]]
    df["played_next"] = [
        1.0 if nxt.get((s, w + 1, p), 0.0) >= threshold else 0.0
        for s, w, p in zip(df["season"], df["week"], df["player_id"], strict=True)
    ]
    by_rank = df.groupby(df["depth"].clip(upper=max_rank + 1))["played_next"].mean()
    by_band = df.groupby((df["snap_share"].clip(0, 0.999) * 10).astype(int))["played_next"].mean()
    return {
        "depth_rank_p": {int(k): round(float(v), 3) for k, v in by_rank.items() if k <= max_rank},
        "tail_p": round(float(by_rank.get(max_rank + 1, DEPTH_RANK_TAIL_P)), 3),
        "snap_share_p": [round(float(by_band.get(i, np.nan)), 3) for i in range(10)],
        "n": int(len(df)),
    }


@dataclass
class AvailabilityModel:
    """Player-week `p_startable`, degrade-safe throughout. See the module docstring.

    ``fit(history)`` trains the underlying `DiscreteTimeHazard`; ``p_startable(frame)``
    (alias: ``p_available``) returns a `player_id → p` Series folding the hazard together
    with whichever of `status` / `suspended` / `roster_status` / `depth_rank` / `snap_share`
    columns the frame happens to carry. Every absent column is a logged no-op, so with no
    signals at all the layer collapses to `neutral_p` (1.0) — the projection passes through.
    """

    neutral_p: float = 1.0
    status_table: Mapping[str, float] = field(default_factory=lambda: dict(STATUS_P))
    hazard: DiscreteTimeHazard = field(default_factory=DiscreteTimeHazard)
    _warned: set[str] = field(default_factory=set, repr=False, compare=False)

    def fit(self, history: pd.DataFrame, **kw: object) -> AvailabilityModel:
        """Fit the base hazard on injury history (person-period `out` events)."""
        self.hazard.fit(history, **kw)
        return self

    def _base(self, frame: pd.DataFrame) -> np.ndarray:
        """Hazard-derived P(available) per row, or the neutral value when unfitted."""
        if self.hazard.fitted:
            return np.clip(self.hazard.predict_available(frame), 0.0, 1.0)
        return np.full(len(frame), self.neutral_p, dtype=float)

    def _column(self, frame: pd.DataFrame, col: str, default: object = None) -> np.ndarray:
        """Column values, or a `default`-filled array + ONE warning when the source is gone."""
        if col in frame.columns:
            return frame[col].to_numpy()
        if col not in self._warned:
            self._warned.add(col)
            log.warning(
                "availability: source column %r absent — defaulting to %r (degrade-neutral)",
                col, default,
            )
        return np.full(len(frame), default, dtype=object)

    def p_available(
        self,
        frame: pd.DataFrame,
        *,
        status_col: str = "status",
        suspended_col: str = "suspended",
        player_col: str = "player_id",
        roster_col: str = "roster_status",
        depth_col: str = "depth_rank",
        snap_col: str = "snap_share",
    ) -> pd.Series:
        """`player_id → p_startable` for the given current player-week frame.

        Base hazard, then the report-status override, then the usage and roster-state
        factors multiply in, then suspension zeroes. Each stage is a no-op if its column
        is missing, so this is safe to call on a frame carrying any subset of signals.
        """
        p = self._base(frame)
        statuses = self._column(frame, status_col)
        rosters = self._column(frame, roster_col)
        depths = self._column(frame, depth_col)
        shares = self._column(frame, snap_col)
        for i in range(len(frame)):
            override = resolve_status_p(statuses[i], self.status_table)
            if override is not None:
                p[i] = override
            p[i] *= usage_p(depths[i], shares[i]) * roster_state_p(rosters[i])
        if suspended_col in frame.columns:
            susp = frame[suspended_col].fillna(False).astype(bool).to_numpy()
            p = np.where(susp, 0.0, p)
        else:
            self._column(frame, suspended_col, False)  # warn-once; no effect on p
        return pd.Series(
            np.clip(p, 0.0, 1.0),
            index=frame[player_col].astype(str).to_numpy(),
            name="p_available",
        )

    #: Canonical name for the number defined at the top of this module. `p_available` is
    #: the legacy alias kept because `survival/__init__` and the E7 harnesses import it.
    p_startable = p_available
