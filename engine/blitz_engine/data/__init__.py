"""Engine data layer: ingest (fill the store) + validation (gate the model).

`ingest/`     — 2014+ play-by-play + nflverse advanced stats into the ParquetStore
                (chunked, float32, idempotent upsert). E0-ingest.
`validation/` — a gate that runs BEFORE any model: schema + row-counts + freshness +
                provenance. An anomaly BLOCKS (raises `ValidationError`), never silent.
`sources/`    — the 4 new free source adapters (E0-sources; not owned here).
"""
from __future__ import annotations
