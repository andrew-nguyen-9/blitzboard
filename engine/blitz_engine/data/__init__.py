"""Engine-side data ingestion (v4).

`sources/` holds the NEW free-source adapters that feed the engine store. They REUSE
the pipeline degrade-safe contract (present-or-neutral, missing key/source → neutral,
never crash) but write through the engine `ParquetStore` instead of Supabase. The
existing cron adapters stay in `pipeline/adapters/` and are imported, never moved
(see `blitz_engine.pipeline_bridge`).
"""
from __future__ import annotations
