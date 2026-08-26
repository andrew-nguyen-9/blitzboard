"""Publish the availability surface (E2b) to Supabase — degrade-safe, service-role only.

Companion to `Snapshot` (this package): where `Snapshot` hands the frontend the value board,
this hands it `blitz_engine.survival.availability.AvailabilityModel.p_startable` per player, so
`draftAI.ts` can drop the `faPenalty` / `injuryDiscount` hacks for a real number
(docs/design/v5-architecture.md §4). Two independent degrade paths, neither ever raises:

  * `build_availability_rows` calls `p_startable` on whatever columns `players` happens to
    carry (today: just `player_id`/`position`/`team` from the CLI's store — everything else is
    a no-op inside the model per e2a). The row set is never empty just because a signal is
    missing.
  * `publish_availability` upserts to Supabase using `NEXT_PUBLIC_SUPABASE_URL` /
    `SUPABASE_SERVICE_ROLE_KEY` (the same pair `pipeline/common.py` reads). Either absent ->
    no-op, `uploaded: False`, no raise — the caller still has the local rows/snapshot. The key
    VALUE is never logged, only whether the two env vars are present.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from blitz_engine.survival.availability import AvailabilityModel

TABLE = "player_availability"
_URL_VAR = "NEXT_PUBLIC_SUPABASE_URL"
_KEY_VAR = "SUPABASE_SERVICE_ROLE_KEY"  # noqa: S105 — this is an env VAR NAME, never a secret value


def build_availability_rows(
    players: pd.DataFrame, season: int, week: int, model: AvailabilityModel | None = None,
) -> pd.DataFrame:
    """`players` (needs `player_id`; anything else is optional) -> upsert-ready rows.

    Publishes the FUNCTION's current output, not a baked number — as `players` gains real
    `roster_status`/`depth_rank`/`snap_share` columns (e9b), the same call yields sharper rows
    with no code change here.
    """
    from blitz_engine.survival.availability import AvailabilityModel

    m = model or AvailabilityModel()
    p = m.p_startable(players)
    roster_status = (
        players.set_index(players["player_id"].astype(str))["roster_status"]
        if "roster_status" in players.columns
        else pd.Series(dtype=object)
    )
    return pd.DataFrame({
        "player_id": p.index,
        "season": season,
        "week": week,
        "p_startable": p.to_numpy(dtype=float),
        "roster_status": [roster_status.get(pid) for pid in p.index],
        "source": "engine",
    })


def publish_availability(rows: pd.DataFrame, *, table: str = TABLE) -> dict:
    """Upsert `rows` into Supabase `table`. No service-role key -> a documented no-op.

    Never raises on a missing/misconfigured client — publish must still exit 0 and hand the
    caller the local rows so nothing downstream is blocked on live credentials.
    """
    url = os.environ.get(_URL_VAR)
    key = os.environ.get(_KEY_VAR)
    if not url or not key:
        return {
            "uploaded": False,
            "reason": f"{_URL_VAR}/{_KEY_VAR} not set — wrote local rows only",
            "rows": len(rows),
        }
    from supabase import create_client

    sb = create_client(url, key)
    payload = rows.assign(updated_at=pd.Timestamp.now(tz="UTC").isoformat()).to_dict("records")
    sb.table(table).upsert(payload, on_conflict="player_id,season,week").execute()
    return {"uploaded": True, "reason": None, "rows": len(rows)}
