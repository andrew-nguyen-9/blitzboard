"""Source-specific ingest scripts (E2+).

Standalone, runnable pipeline steps that pull one external dataset each. They reuse
the F2 ``adapters.Adapter`` shape (fetch → normalize → persist, key-gated degrade)
but live here rather than in ``adapters/`` because they are invoked directly by the
cron (like ``player_ingest.py``), not by ``adapters.run_all()``.

Context/environmental ingest (E3): free-data ingestion that hydrates the
``metadata`` escape-hatch the E3 projection factors
(``models/factors/environment.py`` + ``scheme.py``) read. See ``context_ingest``
for the F2-style adapter + the artifact E9b (Articles) consumes.
"""
