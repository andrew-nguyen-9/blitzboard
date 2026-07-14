"""Vegas odds source — ODDS_API_KEY-gated, REUSES the pipeline odds adapter.

The-odds-api free tier is already implemented, degrade-safe, in
`pipeline/adapters/odds.py` (`OddsAdapter`). Rather than reimplement fetch/normalize
(and drift its consensus math), this engine source DELEGATES to that adapter and only
redirects the write from Supabase to the engine `ParquetStore` — reuse over rewrite.

FREE-TIER (inline provenance): the-odds-api free tier ~500 req/mo, user-provisioned
key. Key env var: ``ODDS_API_KEY``. ABSENT → source *unavailable*: `run()` returns a
neutral result (0 rows, no fetch, no write, no raise); betting features degrade
neutral downstream. Pending activation on the user provisioning ``ODDS_API_KEY``.
"""
from __future__ import annotations

from typing import Any

from blitz_engine.data.sources.base import EngineSource


class VegasOddsSource(EngineSource):
    name = "vegas_odds"
    table = "vegas_odds"
    requires_key = "ODDS_API_KEY"  # absent → degrade to neutral (F2 contract)
    provenance = "the-odds-api v4 NFL h2h/spreads/totals (via pipeline OddsAdapter)"
    free_tier = "the-odds-api free tier ~500 req/mo; user-provisioned key"

    def _pipeline_adapter(self) -> Any:
        """The existing, tested pipeline OddsAdapter (imported via the bridge)."""
        from blitz_engine.pipeline_bridge import load_adapters

        load_adapters()  # ensures pipeline/ is on sys.path
        from adapters.odds import OddsAdapter

        return OddsAdapter()

    def fetch(self) -> object:
        return self._pipeline_adapter().fetch()

    def normalize(self, raw: object) -> list[dict]:
        """Delegate the consensus-row math to the pipeline adapter (pure)."""
        return self._pipeline_adapter().normalize(raw)
