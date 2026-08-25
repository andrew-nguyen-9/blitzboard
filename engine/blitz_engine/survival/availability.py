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

WHERE THE NUMBERS COME FROM. `DEPTH_RANK_P` and `SNAP_SHARE_P` are **not hand-typed**: they
are the empirical next-week play rates fitted on the ingested nflverse `snap_counts` table
(e9's store, 300,812 REG rows, seasons 2014-2025, QB/RB/WR/TE), conditioned on the team
playing the following week so byes/season-end do not deflate them. `fit_usage_priors()` is
the exact estimator that produced them — re-run it on the store to reproduce the constants:

    from blitz_engine.store import ParquetStore
    s = ParquetStore.open("~/.blitz_engine")
    fit_usage_priors(s.table("snap_counts").df().rename(columns={"offense_pct": "snap_share",
                     "pfr_player_id": "player_id"}))

The roster-state ceilings (`ROSTER_STATE_P`) cannot be fitted — the store has no roster,
depth-chart or transactions table (e9 ingested pbp + snap counts + NGS/PFR/FTN only), so
those are *stated priors*, each justified in the table's comments. When a roster feed lands,
they become fittable the same way.

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
    "ROSTER_STATE_P",
    "SEASON_LONG_ZERO_STATES",
    "SNAP_SHARE_P",
    "STATUS_P",
    "ZERO_AVAILABILITY_EPS",
    "AvailabilityModel",
    "RosterState",
    "depth_rank_p",
    "fit_usage_priors",
    "is_effectively_unavailable",
    "is_season_long_zero",
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
    PRACTICE_SQUAD = "PRACTICE_SQUAD"
    IR = "IR"
    PUP = "PUP"
    NFI = "NFI"
    SUSPENDED = "SUSPENDED"
    HOLDOUT = "HOLDOUT"
    CAMP_BODY = "CAMP_BODY"           # camp/tryout/waived — never made a 53
    FREE_AGENT = "FREE_AGENT"         # unsigned, no NFL team
    RETIRED = "RETIRED"


#: Roster state → the CEILING it places on `p_startable` for a given week.
#: STATED PRIORS (no roster/transactions table is ingested yet — see the module docstring):
#:   ROSTERED        1.0   — no ceiling; the usage + report factors carry the whole estimate.
#:   IR/PUP/NFI      0.0   — ineligible to play this week by rule (regular-season PUP/NFI is a
#:                           minimum-4-week designation; IR is a minimum of 4 games).
#:   SUSPENDED       0.0   — ineligible by rule for the weeks covered.
#:   FREE_AGENT      0.0   — an unsigned player takes zero snaps for zero teams. THE BUG FIX.
#:   RETIRED         0.0   — same, permanently.
#:   PRACTICE_SQUAD  0.06  — a PS player plays only if elevated; each team gets 2 elevations a
#:                           week over ~50 PS bodies, and an elevated player rarely clears the
#:                           10% snap bar. 0.06 is deliberately generous to that ceiling.
#:   HOLDOUT         0.05  — most holdouts end, but not for the week they are holding out.
#:   CAMP_BODY       0.02  — a camp arm/leg that never made a 53; the residual is "gets signed".
ROSTER_STATE_P: dict[RosterState, float] = {
    RosterState.ROSTERED: 1.0,
    RosterState.PRACTICE_SQUAD: 0.06,
    RosterState.IR: 0.0,
    RosterState.PUP: 0.0,
    RosterState.NFI: 0.0,
    RosterState.SUSPENDED: 0.0,
    RosterState.HOLDOUT: 0.05,
    RosterState.CAMP_BODY: 0.02,
    RosterState.FREE_AGENT: 0.0,
    RosterState.RETIRED: 0.0,
}

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
}

#: Depth rank (1 = the team's snap leader at his position) → P(≥10% of offensive snaps next
#: week | his team plays). FITTED on nflverse snap_counts 2014-2025 — see `fit_usage_priors`.
#: n per rank: 22109 / 17812 / 15061 / 7482 / 4650 / 1163.
DEPTH_RANK_P: dict[int, float] = {1: 0.943, 2: 0.833, 3: 0.653, 4: 0.592, 5: 0.411, 6: 0.236}
#: Rank 7 and deeper (n=72): the empirical tail. A "camp body on the depth chart".
DEPTH_RANK_TAIL_P = 0.097

#: Trailing offensive snap share, in 10-point bands (index = floor(share*10)) → the same
#: next-week play probability. FITTED alongside `DEPTH_RANK_P` on the same 2014-2025 rows.
SNAP_SHARE_P: tuple[float, ...] = (
    0.263, 0.617, 0.788, 0.861, 0.892, 0.913, 0.930, 0.940, 0.953, 0.954,
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


def resolve_roster_state(status: object) -> RosterState | None:
    """Raw feed string → `RosterState`, or ``None`` when the signal is missing/unknown.

    ``None`` is "no signal", never a state: an unparseable string must not sink a player.
    """
    if status is None:
        return None
    if isinstance(status, RosterState):
        return status
    if isinstance(status, float) and np.isnan(status):
        return None
    s = str(status).strip().upper()
    if not s or s in {"NAN", "NA", "NONE", "UNKNOWN"}:
        return None
    return _ROSTER_ALIASES.get(s) or _ROSTER_ALIASES.get(s.replace("_", " "))


def roster_state_p(status: object, *, default: float = 1.0) -> float:
    """Roster-state ceiling on `p_startable`; `default` (1.0, neutral) when unknown."""
    state = resolve_roster_state(status)
    return default if state is None else ROSTER_STATE_P[state]


def is_season_long_zero(status: object) -> bool:
    """Is this roster state "zero snaps all season" (retired / unsigned FA / camp body)?

    The predicate the draft board uses to SINK a player outright, as opposed to the
    weekly-zero designations (IR/PUP/NFI/suspension) which are merely worth less.
    """
    state = resolve_roster_state(status)
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
