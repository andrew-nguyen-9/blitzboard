"""Championship-equity draft value — the DEEP objective under the interim board (E4-deep).

The draft objective is **not** raw projected points, nor even static VORP: it is
**Δ P(win league)** — how much a player raises your championship probability. That quantity is
defined by E3's full-league Monte-Carlo (`simulation.simulate_league`, which exposes
``p_champion``). This module supplies two layers over it:

* **Offline, equity-optimal** — `championship_equity` re-sims the league with a candidate added
  to your roster and reports the exact ΔP(champion). Correct but sim-priced; used to *calibrate*
  and to grade the live policy, never on the clock.
* **Live, fast proxy** — `live_draft_value` never re-sims. It converts each player's
  demand-derived VORP (`replacement.py`, scarcity via `opponent.py`/`vona.py`) into an equity
  delta through a single scalar sensitivity ``dP(champion)/d(points·week⁻¹)`` that
  `calibrate_equity_sensitivity` fits once from the sim. This is the board the live draft room
  ranks by — it *swaps under* the W2 interim value surface without touching its draft contract.

`ponytail:` the offline path reuses `simulate_league` wholesale (no bespoke sim); the live path
is arithmetic over the other three value modules. One first-order sensitivity links them — the
sim is queried O(1) times offline, zero times live.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from blitz_engine.simulation.league import (
    LeagueConfig,
    LeagueResult,
    Roster,
    simulate_league,
)
from blitz_engine.value.opponent import OpponentField, TeamState
from blitz_engine.value.replacement import (
    demand_replacement_levels,
    vorp_board,
)
from blitz_engine.value.vona import VonaResult, vona_board


def _sim(
    marginals: pd.DataFrame,
    players: pd.DataFrame,
    rosters: Sequence[Roster],
    schedule: Sequence[Sequence[tuple[str, str]]],
    config: LeagueConfig | None,
    **kw: object,
) -> LeagueResult:
    """Thin `simulate_league` call — default config unless one is supplied."""
    if config is None:
        return simulate_league(marginals, players, rosters, schedule, **kw)  # type: ignore[arg-type]
    return simulate_league(marginals, players, rosters, schedule, config=config, **kw)  # type: ignore[arg-type]


def _with_candidate(
    rosters: Sequence[Roster], target_roster: str, candidate: str, replace: str | None
) -> list[Roster]:
    """Return ``rosters`` with ``candidate`` added to ``target_roster`` (or swapped for replace)."""
    out: list[Roster] = []
    for r in rosters:
        if r.id != target_roster:
            out.append(r)
            continue
        starters = tuple(s for s in r.starters if s != replace) if replace else r.starters
        out.append(Roster(id=r.id, starters=(*starters, candidate)))
    return out


def championship_equity(
    marginals: pd.DataFrame,
    players: pd.DataFrame,
    rosters: Sequence[Roster],
    schedule: Sequence[Sequence[tuple[str, str]]],
    *,
    target_roster: str,
    candidates: Sequence[str],
    replace: str | None = None,
    config: LeagueConfig | None = None,
    **sim_kwargs: object,
) -> pd.Series:
    """Exact ΔP(win league) for adding each candidate to ``target_roster`` (offline, re-sims).

    Runs one baseline league sim, then one sim per candidate with that player added to the
    target roster's starters (or swapped in for ``replace``). Returns a Series ``candidate_id
    -> Δ p_champion`` sorted best-first — the equity-optimal draft ranking. ``candidates`` must
    already be present in ``marginals`` and ``players``.
    """
    base = _sim(marginals, players, rosters, schedule, config, **sim_kwargs)
    base_champ = float(base.p_champion().get(target_roster, 0.0))
    deltas: dict[str, float] = {}
    for cand in candidates:
        alt = _with_candidate(rosters, target_roster, cand, replace)
        res = _sim(marginals, players, alt, schedule, config, **sim_kwargs)
        deltas[cand] = float(res.p_champion().get(target_roster, 0.0)) - base_champ
    return pd.Series(deltas, name="equity_delta").sort_values(ascending=False)


def calibrate_equity_sensitivity(
    marginals: pd.DataFrame,
    players: pd.DataFrame,
    rosters: Sequence[Roster],
    schedule: Sequence[Sequence[tuple[str, str]]],
    *,
    target_roster: str,
    delta_pts: float = 3.0,
    config: LeagueConfig | None = None,
    **sim_kwargs: object,
) -> float:
    """Fit ``dP(champion)/d(points·week⁻¹)`` for ``target_roster`` by finite-differencing the sim.

    Bumps one of the target roster's starters' weekly mean by ``delta_pts`` and measures the
    resulting rise in championship probability. The slope is the scalar the live proxy multiplies
    a player's VORP by. Non-negative (more points never lowers equity); returns 0 if the target
    roster or its starters aren't in the universe (degrade-neutral).
    """
    target = next((r for r in rosters if r.id == target_roster), None)
    if target is None or not target.starters:
        return 0.0
    ids = set(marginals["player_id"].astype(str))
    bump_id = next((s for s in target.starters if str(s) in ids), None)
    if bump_id is None:
        return 0.0

    base = _sim(marginals, players, rosters, schedule, config, **sim_kwargs)
    p0 = float(base.p_champion().get(target_roster, 0.0))

    bumped = marginals.copy()
    mask = bumped["player_id"].astype(str) == str(bump_id)
    bumped.loc[mask, "mean"] = bumped.loc[mask, "mean"] + float(delta_pts)
    hi = _sim(bumped, players, rosters, schedule, config, **sim_kwargs)
    p1 = float(hi.p_champion().get(target_roster, 0.0))

    return max(0.0, (p1 - p0) / delta_pts) if delta_pts else 0.0


def equity_proxy(value_delta: float, sensitivity: float) -> float:
    """Live equity estimate: a VORP (points·week⁻¹) edge scaled by the calibrated sensitivity."""
    return max(0.0, float(sensitivity) * float(value_delta))


@dataclass(frozen=True)
class LiveBoard:
    """The per-pick live value board — the whole E4 live surface in one object.

    ``ranked`` is ``(player_id, equity_value)`` best-first; ``equity_value`` is the scarcity-
    aware VORP mapped through the equity sensitivity. The other fields expose the intermediate
    scarcity signals the draft room shows (replacement levels, VONA, opponent pick beliefs).
    """

    ranked: list[tuple[str, float]]
    equity_value: dict[str, float]
    vorp: dict[str, float]
    replacement: dict[str, float]
    vona: dict[str, VonaResult]
    pick_sequence: list[dict[str, float]]

    def best(self) -> str | None:
        """The id of the top pick under the live equity objective (None if the board is empty)."""
        return self.ranked[0][0] if self.ranked else None


def live_draft_value(
    players_by_position: Mapping[str, Sequence[tuple[str, float]]],
    opponent_field: OpponentField,
    *,
    opponent_counts: Sequence[TeamState] | None = None,
    sensitivity: float = 1.0,
) -> LiveBoard:
    """Compose opponent model → replacement → VONA → equity into the live value board (no sim).

    ``players_by_position``: per-position ``(player_id, value)`` for every *available* player.
    ``opponent_field``: the GMs picking before your next turn (`opponent.py`).
    ``sensitivity``: from `calibrate_equity_sensitivity`; default 1.0 leaves the board in raw
    scarcity-adjusted-VORP units. Recompute every pick — availability and opponent beliefs move.
    """
    # Sort each position descending and read the frontier the opponent model reacts to.
    by_pos: dict[str, list[tuple[str, float]]] = {
        pos: sorted(players, key=lambda pv: pv[1], reverse=True)
        for pos, players in players_by_position.items()
    }
    values_by_position = {pos: [v for _, v in players] for pos, players in by_pos.items()}
    top_value_by_pos = {pos: vals[0] for pos, vals in values_by_position.items() if vals}

    pick_seq = opponent_field.pick_position_sequence(top_value_by_pos, opponent_counts)
    replacement = demand_replacement_levels(values_by_position, pick_seq)
    vorp = vorp_board(by_pos, replacement)
    vona = vona_board(values_by_position, pick_seq)

    equity_value = {pid: equity_proxy(v, sensitivity) for pid, v in vorp.items()}
    ranked = sorted(equity_value.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    return LiveBoard(
        ranked=ranked,
        equity_value=equity_value,
        vorp=vorp,
        replacement=replacement,
        vona=vona,
        pick_sequence=pick_seq,
    )
