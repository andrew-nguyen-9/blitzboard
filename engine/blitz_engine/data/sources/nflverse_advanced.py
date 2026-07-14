"""nflverse *advanced* source (keyless) — NGS, snap counts, depth charts, routes.

Pulls the advanced player-week signals nflverse publishes as free release CSVs and
folds them into ONE wide `nflverse_advanced` table keyed by player-season-week:
Next Gen Stats (separation / cushion / YAC-over-expected), snap share, routes run +
air-yards / target share, and depth-chart role. Every field is optional — a player
missing NGS still gets a row with those columns neutral (``None``).

FREE-TIER (inline provenance): nflverse GitHub release CSVs — no key, no account,
public. This source is KEYLESS: always enabled, but degrades to zero rows when the
release is unreachable or empty (best-effort `fetch`).
"""
from __future__ import annotations

from typing import Any

from blitz_engine.data.sources.base import EngineSource

_RELEASE = "https://github.com/nflverse/nflverse-data/releases/download"


class NflverseAdvancedSource(EngineSource):
    name = "nflverse_advanced"
    table = "nflverse_advanced"
    requires_key = None  # keyless public release CSVs
    provenance = "nflverse-data releases: nextgen_stats + snap_counts + depth_charts"
    free_tier = "nflverse release CSVs; no key; public"
    key_cols = ("player_id", "season", "week")
    columns = (
        "player_id", "player_name", "position", "team", "season", "week",
        "snap_pct", "routes_run", "air_yards", "target_share",
        "ngs_avg_separation", "ngs_avg_cushion", "ngs_yac_above_expected",
        "depth_chart_pos", "depth_chart_order",
    )

    def fetch(self) -> object:
        """Download + outer-merge the advanced release CSVs on player-season-week.

        Best-effort: any failure (offline, 404, schema drift) degrades to ``[]`` so
        the source is neutral, never fatal. Live-only — tests drive `normalize`.
        """
        try:
            import pandas as pd

            season = _current_season()
            frames = []
            for stat_type, url in (
                ("ngs", f"{_RELEASE}/nextgen_stats/ngs_{season}_receiving.csv.gz"),
                ("snaps", f"{_RELEASE}/snap_counts/snap_counts_{season}.csv.gz"),
                ("depth", f"{_RELEASE}/depth_charts/depth_charts_{season}.csv.gz"),
            ):
                try:
                    frames.append((stat_type, pd.read_csv(url, compression="gzip")))
                except Exception:  # noqa: BLE001 — one missing release must not sink the rest
                    continue
            if not frames:
                return []
            merged = _merge_advanced(frames)
            return merged.to_dict("records")
        except Exception:  # noqa: BLE001 — keyless source is best-effort → neutral
            return []

    def normalize(self, raw: object) -> list[dict]:
        """Raw merged records → the wide advanced table (present-or-neutral)."""
        return self._project(raw)


def _current_season() -> int:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    # NFL season is labeled by its September kickoff year.
    return now.year if now.month >= 9 else now.year - 1


def _merge_advanced(frames: list) -> Any:  # pragma: no cover - live merge, exercised only online
    import functools

    import pandas as pd

    keys = ["player_id", "season", "week"]
    prepared = [df for _, df in frames if all(k in df.columns for k in keys)]
    if not prepared:
        return pd.DataFrame()
    return functools.reduce(
        lambda a, b: a.merge(b, on=keys, how="outer", suffixes=("", "_dup")), prepared
    )
