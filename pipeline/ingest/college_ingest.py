"""
college_ingest.py (E2) — college production for incoming rookies / new players.

Source: CollegeFootballData (CFBD), the free public college-football API. It needs
a FREE user key (``CFBD_API_KEY``); with no key the whole step DEGRADES to a no-op
(the F2 contract), so the pipeline runs fine with "no college context" — the
``CollegeProspectFactor`` then stays identity for every rookie.

Shape (F2 ``adapters.Adapter``): ``fetch`` → ``normalize`` → ``persist``, wrapped by
``run()``:

  * ``fetch`` pulls CFBD season *player* stats (long-format: one row per
    player×category×statType) for the requested year, ``@retry_api`` wrapped.
  * ``normalize`` is PURE: it pivots the long rows into one dict per player and
    condenses production into a single ``prospect_score`` ∈ [0, 1] (0.5 neutral).
    Unit-testable on a fixture with no network.
  * ``persist`` upserts the per-player rows into ``college_stats`` (idempotent on
    ``cfbd_player_id, season``); dry-runs when Supabase is unset.

``enrich_players()`` is the identity-join step: it reads existing ``players`` rows,
merges each matched prospect's ``college_production`` summary INTO that player's
``metadata`` jsonb (non-destructively), and upserts. That summary is exactly what
``CollegeProspectFactor`` reads: ``metadata["college_production"]["prospect_score"]``.
The join keys on normalized full name (F3 fixed roster identity is the NFL side;
CFBD carries no NFL id, so name is the only free crosswalk — documented limitation
in ANALYTICS_SURVEY.md §College data & its limits).

FREE-TIER LIMITS (inline provenance):
  * collegefootballdata.com: free API key (self-serve). Rate-limited on the free
    tier; this step is called at most once per season backfill + weekly, so it
    lives inside the free tier. Cache/backfill by year to stay well under quota.

Usage:
    python -m ingest.college_ingest --year 2024            # ingest one class
    python -m ingest.college_ingest --year 2024 --enrich   # + merge into players
"""
from __future__ import annotations

import argparse
import os
from collections import defaultdict

import requests

from adapters.base import Adapter
from common import console, fetch_all, retry_api, upsert

_BASE = "https://api.collegefootballdata.com"

# CFBD statType names (long-format) → our compact stat keys. Only the production
# signals a fantasy prospect model cares about; everything else is ignored.
_STAT_MAP = {
    "YDS": "yards",           # category-scoped (rushing/receiving/passing) — see _key
    "TD": "tds",
    "REC": "receptions",
    "CAR": "carries",
    "ATT": "attempts",
}

# Rough production ceilings per category for a single dominant college season, used
# to normalize a raw scrimmage-production number into [0, 1]. Deliberately simple
# and documented as a heuristic (ANALYTICS_SURVEY.md) — CFBD's free tier gives us
# counting stats, not the snap/route data a real prospect model would use.
_SCRIMMAGE_YDS_CEIL = 1800.0
_SCRIMMAGE_TD_CEIL = 22.0


def _key(category: str, stat_type: str) -> str | None:
    """Map (category, statType) → a namespaced stat key, e.g. rushing YDS → rush_yards."""
    base = _STAT_MAP.get((stat_type or "").upper())
    if not base:
        return None
    cat = (category or "").lower()
    prefix = {"rushing": "rush", "receiving": "rec", "passing": "pass"}.get(cat)
    if prefix is None:
        return None
    return f"{prefix}_{base}"


def prospect_score(stats: dict) -> float:
    """Condense pivoted college counting stats → a bounded prospect score ∈ [0, 1].

    Pure + deterministic. Scrimmage yards + TDs (rushing + receiving) normalized
    against a strong-season ceiling and blended 70/30. Passing yards contribute at
    a discount (QB rushing already counts). 0.5 is the neutral anchor the factor
    treats as "no signal"; an empty blob returns exactly 0.5.
    """
    if not stats:
        return 0.5
    scrimmage_yds = (stats.get("rush_yards") or 0) + (stats.get("rec_yards") or 0)
    scrimmage_yds += 0.25 * (stats.get("pass_yards") or 0)
    scrimmage_td = (stats.get("rush_tds") or 0) + (stats.get("rec_tds") or 0)
    scrimmage_td += 0.25 * (stats.get("pass_tds") or 0)
    yd_n = min(scrimmage_yds / _SCRIMMAGE_YDS_CEIL, 1.0)
    td_n = min(scrimmage_td / _SCRIMMAGE_TD_CEIL, 1.0)
    return round(0.7 * yd_n + 0.3 * td_n, 4)


class CollegeStatsAdapter(Adapter):
    """CFBD season player stats → ``college_stats`` (one row per player×season)."""

    name = "college_stats"
    table = "college_stats"
    on_conflict = "cfbd_player_id,season"
    requires_key = "CFBD_API_KEY"
    free_tier = "collegefootballdata.com free key; rate-limited, backfill by season"

    def __init__(self, year: int | None = None):
        self.year = year

    @retry_api
    def fetch(self) -> list[dict]:
        """CFBD long-format season player stats for ``self.year``."""
        headers = {"Authorization": f"Bearer {os.getenv(self.requires_key)}"}
        r = requests.get(
            f"{_BASE}/stats/player/season",
            params={"year": self.year},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def normalize(self, raw: list[dict]) -> list[dict]:
        """Pivot CFBD long rows → one production row per (player, season). Pure."""
        if not raw:
            return []
        # (playerId) → {"player","team","conf","season","stats":{...}}
        agg: dict[str, dict] = {}
        for r in raw:
            pid = str(r.get("playerId") or r.get("player") or "")
            if not pid:
                continue
            key = _key(r.get("category", ""), r.get("statType", ""))
            bucket = agg.setdefault(pid, {
                "cfbd_player_id": pid,
                "player_name": r.get("player"),
                "college": r.get("team"),
                "conference": r.get("conference"),
                "season": int(r.get("season") or self.year or 0),
                "stats": defaultdict(float),
            })
            if key is not None:
                try:
                    bucket["stats"][key] += float(r.get("stat") or 0)
                except (TypeError, ValueError):
                    pass
        rows: list[dict] = []
        for b in agg.values():
            stats = {k: round(v, 1) for k, v in b["stats"].items()}
            rows.append({
                "cfbd_player_id": b["cfbd_player_id"],
                "player_name": b["player_name"],
                "search_name": (b["player_name"] or "").lower().strip(),
                "college": b["college"],
                "conference": b["conference"],
                "season": b["season"],
                "stats": stats,
                "prospect_score": prospect_score(stats),
            })
        return rows

    def enrich_players(self, rows: list[dict]) -> int:
        """Merge each prospect's ``college_production`` summary into the matching
        ``players.metadata`` (join on normalized full name). Non-destructive: reads
        existing metadata and merges, so nothing else in the jsonb is lost. No-op
        (dry-run) offline — ``fetch_all`` returns [] with no Supabase. Idempotent."""
        if not rows:
            return 0
        players = fetch_all("players", "id,full_name,search_name,metadata")
        if not players:
            console.print("[dim]college enrich: no players loaded (offline) — skipping.[/dim]")
            return 0
        by_name: dict[str, dict] = {}
        for r in rows:
            n = r.get("search_name")
            if n:
                by_name[n] = r
        patched: list[dict] = []
        for p in players:
            name = (p.get("search_name") or (p.get("full_name") or "").lower().strip())
            src = by_name.get(name)
            if not src:
                continue
            meta = dict(p.get("metadata") or {})
            meta["college_production"] = {
                "prospect_score": src["prospect_score"],
                "college": src.get("college"),
                "season": src.get("season"),
            }
            patched.append({"id": p["id"], "metadata": meta})
        return upsert("players", patched, on_conflict="id")

    def run_year(self, *, enrich: bool = False) -> list[dict]:
        """Full step for one season: run() (fetch→normalize→persist), then optionally
        merge into players. Degrade-safe end to end."""
        rows = self.run()
        if enrich:
            self.enrich_players(rows)
        return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest CFBD college production for a season.")
    ap.add_argument("--year", type=int, required=True, help="college season year")
    ap.add_argument("--enrich", action="store_true", help="also merge into players.metadata")
    args = ap.parse_args()
    rows = CollegeStatsAdapter(args.year).run_year(enrich=args.enrich)
    console.print(f"[cyan]college_stats: {len(rows)} prospects for {args.year}[/cyan]")


if __name__ == "__main__":
    main()
