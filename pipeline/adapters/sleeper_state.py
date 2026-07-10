"""Reference adapter (F2) — Sleeper NFL "state".

Proves the Adapter shape end-to-end against a GENUINELY FREE, NO-KEY endpoint:
    GET https://api.sleeper.app/v1/state/nfl
returns the current NFL season/week context (tiny JSON, no auth).

FREE-TIER LIMITS (inline provenance):
    * No API key, no account. Public read-only.
    * No published hard quota; Sleeper asks callers to stay under ~1000 req/min
      and cache responses. This adapter is called at most a few times per pipeline
      run, so it lives comfortably inside the free tier with margin.
    * Banned-tier check: N/A — there is no paid tier to accidentally opt into.

Because it is keyless, `requires_key=None`: it is always "enabled", but still
degrades safely — `persist()` dry-runs when Supabase is unconfigured, so a run
with no backend writes nothing and never errors (see the degrade contract in
`base.py`).
"""
from __future__ import annotations

import requests

from adapters.base import Adapter
from common import retry_api

_URL = "https://api.sleeper.app/v1/state/nfl"


class SleeperStateAdapter(Adapter):
    name = "sleeper_state"
    table = "nfl_state"          # illustrative single-row context table
    on_conflict = "season"
    requires_key = None          # keyless public endpoint
    free_tier = "no key; ~1000 req/min courtesy cap, cache responses"

    @retry_api
    def fetch(self) -> dict:
        r = requests.get(_URL, timeout=15)
        r.raise_for_status()
        return r.json()

    def normalize(self, raw: dict) -> list[dict]:
        """One row of season context. Empty payload → no rows (still degrade-safe)."""
        if not raw or not raw.get("season"):
            return []
        return [{
            "season": str(raw["season"]),
            "season_type": raw.get("season_type"),
            "week": raw.get("week"),
            "display_week": raw.get("display_week"),
            "previous_season": raw.get("previous_season"),
        }]
