# Current-season NFL status/news ingest

Run the standalone module from the repository root (it is intentionally not wired into the main
CLI, pipeline, Supabase, or a scheduler):

```sh
PYTHONPATH="$PWD/engine" pipeline/.venv/bin/python -m blitz_engine.data.ingest.status_news \
  --season 2025 --start 2025-09-03T00:00:00Z --end 2025-09-04T00:00:00Z \
  --data-root ~/.blitz_engine
```

The explicit interval is `[start, end)`. Re-running it is safe: identical source observations do
not duplicate and prior observations are never overwritten. A malformed/down/rate-limited source
causes a non-zero exit and no write for that table. GitHub release and ESPN endpoints currently
publish no documented numeric rate limit; this tool makes one request per selected source and does
not retry, so 429 responses fail loud.

Sources are nflverse injuries, weekly rosters, and depth charts, plus raw ESPN news metadata. The
default adapters do not claim official 90-minute inactives: no stable, documented, free official
machine feed was verified. Add that source only through a schema-pinned `Feed`; never approximate
it from a Sunday roster snapshot.

Resolution rates are emitted per run because they depend on the exact window and current
`player_ids.parquet`. Fixture verification resolves 1/2 rows (50%); no live rate is claimed until
the command is run against a populated store. Unresolved rows are retained with a reason.

This is a current-season-only feed. It cannot enter a model fit, ablation, or backtest: there is no
history to score against, and BlitzBoard does not ship unproven weights. Legitimate near-term uses
are live draft-day/start-sit inference and display.

Tests:

```sh
cd engine
PYTHONPATH="$PWD" ../pipeline/.venv/bin/python -m pytest tests/test_status_news_ingest.py
```

In a linked worktree, point `PYTHONPATH` at that worktree's `engine/` while using the main
checkout's Python 3.12 venv.
