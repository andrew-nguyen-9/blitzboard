"""Coaching staff + contracts / roles source (keyless) — degrade-safe.

One `coaching_roles` table keyed by player-team-season: the player's on-field role
and contract shape (APY, guaranteed %, years left) denormalized alongside the team's
coaching context (head coach, offensive coordinator, play-caller). Drives E1 context
factors like "new OC / scheme change" and "contract-year usage bump".

FREE-TIER (inline provenance): nflverse coaches release + OverTheCap free contract
CSVs — no key, public. This source is KEYLESS: always enabled, degrades to zero rows
when a source is unreachable/empty (best-effort `fetch`).
"""
from __future__ import annotations

from blitz_engine.data.sources.base import EngineSource


class CoachingRolesSource(EngineSource):
    name = "coaching_roles"
    table = "coaching_roles"
    requires_key = None  # keyless nflverse + OverTheCap free CSVs
    provenance = "nflverse coaches + OverTheCap contracts (free)"
    free_tier = "nflverse/OverTheCap public CSVs; no key"
    key_cols = ("player_id", "season")
    columns = (
        "player_id", "player_name", "position", "team", "season", "role",
        "contract_years_left", "contract_apy", "contract_guaranteed_pct",
        "head_coach", "offensive_coordinator", "play_caller",
    )

    def fetch(self) -> object:
        """Merge nflverse coaching staff with OverTheCap contracts by team-season.

        Best-effort → ``[]`` on any error. Live-only; tests drive `normalize`.
        """
        try:
            import pandas as pd

            otc = pd.read_csv(
                "https://github.com/nflverse/nflverse-data/releases/download/"
                "contracts/historical_contracts.csv.gz",
                compression="gzip",
            )
            return otc.to_dict("records")
        except Exception:  # noqa: BLE001 — keyless best-effort → neutral
            return []

    def normalize(self, raw: object) -> list[dict]:
        """Raw staff/contract records → the coaching-roles table (present-or-neutral)."""
        return self._project(raw)
