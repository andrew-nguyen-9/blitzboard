"""Betting-odds adapter (E5) — free-tier NFL markets via the F2 Adapter shape.

Ingests game-level betting lines (moneyline / spread / total) for the upcoming
NFL slate from **The Odds API** free tier and upserts a consensus row per event.
It is the ingest half of E5; the model half is the BOUNDED, ablatable
``BettingFactor`` (``models/factors/betting.py``), and the read half is the
``/betting`` page. Betting is a LIGHT, separately-logged signal — never folded
silently into value.

FREE-TIER LIMITS (inline provenance):
    * The Odds API free tier: ~500 requests/month, user-provisioned key.
    * Key env var: ``ODDS_API_KEY``. ABSENT → this adapter degrades to a no-op
      (``run()`` returns ``[]``, no fetch, no write, no raise — F2 degrade
      contract). No paid/metered tier is ever used.
    * One request pulls the whole NFL slate (h2h+spreads+totals, US books), so a
      per-run pull stays comfortably inside the monthly quota with margin.
    * No "popularity" field exists on the free tier — see DATA_SOURCES.md; the
      ``/betting`` page proxies "biggest / most-backed" by line strength
      (implied probability), documented on the page.

``normalize`` is pure (fixture-testable, no network): it collapses every
bookmaker into a single CONSENSUS row per event (median spread/total, mean
implied moneyline) so the table is small and idempotent.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone

import requests

from adapters.base import Adapter
from common import retry_api

_SPORT = "americanfootball_nfl"
_URL = f"https://api.the-odds-api.com/v4/sports/{_SPORT}/odds"


def _median(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


class OddsAdapter(Adapter):
    name = "odds"
    table = "betting_odds"
    on_conflict = "event_id"        # one consensus row per game → idempotent re-runs
    requires_key = "ODDS_API_KEY"   # absent → degrade to no-op (F2 contract)
    free_tier = "the-odds-api free tier ~500 req/mo; user-provisioned key; no popularity field"

    @retry_api
    def fetch(self) -> list[dict]:
        import os

        r = requests.get(
            _URL,
            params={
                "apiKey": os.getenv(self.requires_key),
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def normalize(self, raw: object) -> list[dict]:
        """Raw event list → one consensus row per event. Pure + degrade-safe:
        empty/malformed payload → ``[]``; a game missing every market is skipped."""
        if not isinstance(raw, list):
            return []
        rows: list[dict] = []
        for ev in raw:
            if not isinstance(ev, dict) or not ev.get("id"):
                continue
            home, away = ev.get("home_team"), ev.get("away_team")
            home_ml, away_ml, spreads, totals = [], [], [], []
            for bk in ev.get("bookmakers") or []:
                for mkt in bk.get("markets") or []:
                    outs = mkt.get("outcomes") or []
                    if mkt.get("key") == "h2h":
                        for o in outs:
                            if o.get("name") == home and o.get("price") is not None:
                                home_ml.append(o["price"])
                            elif o.get("name") == away and o.get("price") is not None:
                                away_ml.append(o["price"])
                    elif mkt.get("key") == "spreads":
                        for o in outs:
                            if o.get("name") == home and o.get("point") is not None:
                                spreads.append(o["point"])  # home line (neg = favored)
                    elif mkt.get("key") == "totals":
                        for o in outs:
                            if o.get("name") == "Over" and o.get("point") is not None:
                                totals.append(o["point"])
            home_spread = _median(spreads)
            total = _median(totals)
            hml = round(statistics.mean(home_ml)) if home_ml else None
            aml = round(statistics.mean(away_ml)) if away_ml else None
            if home_spread is None and total is None and hml is None:
                continue  # no usable market → skip (still degrade-safe)
            rows.append({
                "event_id": ev["id"],
                "sport": _SPORT,
                "commence_time": ev.get("commence_time"),
                "home_team": home,
                "away_team": away,
                "home_ml": hml,
                "away_ml": aml,
                "home_spread": home_spread,
                "total": total,
                "book_count": len(ev.get("bookmakers") or []),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        return rows
