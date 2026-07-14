"""Engine data layer: ingest (fill the store) + validation (gate the model) + sources.

`ingest/`     — 2014+ play-by-play + nflverse advanced stats into the ParquetStore
                (chunked, float32, idempotent upsert). E0-ingest.
`validation/` — a gate that runs BEFORE any model: schema + row-counts + freshness +
                provenance. An anomaly BLOCKS (raises `ValidationError`), never silent.
`sources/`    — the NEW free-source adapters that feed the engine store (E0-sources).
                They REUSE the pipeline degrade-safe contract (present-or-neutral,
                missing key/source → neutral, never crash) but write through the
                engine `ParquetStore` instead of Supabase. The existing cron adapters
                stay in `pipeline/adapters/` and are imported, never moved
                (see `blitz_engine.pipeline_bridge`).
"""
from __future__ import annotations
