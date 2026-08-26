# 2026 intelligence QC handoff

Cutoff: 2026-08-25 (evidence timestamp 2026-08-26T00:00:00Z). The immutable baseline is
`docs/data/baselines/2026-08-25`; verify it with
`python -m blitz_engine.intelligence.baseline --verify-manifest` from an environment where
`blitz_engine` is importable.

## Acceptance result

- The manifest and both content files are content-hashed and independently verified. The checked-in
  snapshot is 16 KiB; detailed live inputs remain outside Git.
- Live retrieval found two available no-key sources: nflverse weekly rosters (2,930 rows in the
  window) and depth charts (469,064 rows). The three failed or unavailable sources are retained as
  gaps, not converted to empty successful feeds.
- Both the existing and independent models remain shadow-only. There are zero forecast rows and no
  promotion decision because completed 2026 regular-season outcomes did not exist at the cutoff.
- Forecast contracts keep availability probability separate from conditional point distributions.
  Promotion requires shared point-in-time walk-forward folds and no regression for every position
  and league configuration across error, ranking, calibration, and decision-utility metrics.
- Focused handoff verification passed: 15 tests covering the model and seasonal runner. The combined
  engine gate also passed: 4,120 passed and 2 skipped in 371.34 seconds.

## Process and failure behavior

Ingest validates a complete response before append-only persistence. Source or schema failures leave
the affected table untouched and return non-zero. Rows preserve publication time when available and
otherwise mark fetch time explicitly. Unresolved identities stay in the data with a resolution
reason; they are not silently discarded or guessed.

The seasonal runner is idempotent by task and UTC date, uses an exclusive lock, records structured
results, and leaves failures retryable. Its launchd file is an uninstalled template. Installing a
scheduler, supplying credentials, merging, or publishing are deliberately outside this handoff.

## Storage and performance

- The signal registry estimates 1,880 MB for all implemented, candidate, blocked, and excluded
  cards, within the 10 GB seasonal budget. This is a planning estimate, not measured production use.
- HTTP bodies are compressed and content-addressed; their ledger records source, timestamp, sizes,
  validators, and request-budget usage. Snapshots are atomic and immutable, with manifest and file
  hashes checked on replay.
- Daily modeling is capped at 10 minutes, 8 GB RAM, and 12 trials. Deep modeling is capped at eight
  hours, 12 GB RAM, and 200 trials. These are enforceable configuration budgets, not observed
  benchmark claims.
- Production monitoring should alert on task failure, per-source freshness, cache/snapshot size, rate
  limits, and schema drift. Missing data must degrade to explicit coverage or neutral behavior.

## Reverification

From the worktree root:

```sh
PYTHONPATH="$PWD/engine" "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  -m pytest engine/tests/test_intelligence_model.py engine/tests/test_intelligence_runner.py -q
```

For the combined engine gate, run the same Python executable from `engine/` with `-m pytest`. The
brief's `../pipeline/.venv/bin/python` path is not present inside this isolated worktree.
