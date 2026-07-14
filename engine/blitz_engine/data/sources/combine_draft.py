"""Combine athleticism + draft-capital source — CFBD-keyed, degrade-safe.

Joins pre-NFL athletic testing (40, bench, vertical, broad, 3-cone, shuttle → a RAS
-style athleticism score) with draft capital (year / round / overall pick) into one
`combine_draft` table keyed by player. Prospect testing comes from the College
Football Data API, which requires a free key.

FREE-TIER (inline provenance): collegefootballdata.com — free key, generous quota.
    * Key env var: ``CFBD_API_KEY``. ABSENT → this source is *unavailable*: `run()`
      returns a neutral result (0 rows, no fetch, no write, no raise). Draft-capital
      features simply degrade neutral downstream.
"""
from __future__ import annotations

import os

from blitz_engine.data.sources.base import EngineSource

_CFBD_URL = "https://api.collegefootballdata.com/draft/picks"


class CombineDraftSource(EngineSource):
    name = "combine_draft"
    table = "combine_draft"
    requires_key = "CFBD_API_KEY"  # absent → degrade to neutral (F2 contract)
    provenance = "collegefootballdata.com draft/picks + combine athleticism"
    free_tier = "collegefootballdata.com free key; generous monthly quota"
    key_cols = ("player_id",)
    columns = (
        "player_id", "player_name", "position", "college",
        "forty", "bench", "vertical", "broad_jump", "cone", "shuttle", "ras",
        "draft_year", "draft_round", "draft_pick", "draft_overall", "draft_capital",
    )

    def fetch(self) -> object:
        """Pull draft picks + combine testing for the latest class (CFBD).

        Best-effort → ``[]`` on any error. Only called when ``CFBD_API_KEY`` is set.
        """
        try:
            import requests

            r = requests.get(
                _CFBD_URL,
                headers={"Authorization": f"Bearer {os.getenv(self.requires_key)}"},
                timeout=20,
            )
            r.raise_for_status()
            payload = r.json()
            return payload if isinstance(payload, list) else []
        except Exception:  # noqa: BLE001 — degrade to neutral, never fatal
            return []

    def normalize(self, raw: object) -> list[dict]:
        """Raw prospect records → the combine/draft table (present-or-neutral)."""
        return self._project(raw)
