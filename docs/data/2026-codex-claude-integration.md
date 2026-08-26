# Additive Codex–Claude integration contract

This intelligence work is additive. It defines artifacts that another workflow may consume; it does
not edit, replace, or install any Claude configuration, commands, agents, hooks, or status lines.

## Stable handoff surfaces

| Producer artifact | Consumer contract |
|---|---|
| `fixtures/intelligence_signals.json` | Read schema version 1 and preserve card state, privacy, model eligibility, timestamp, identity, missingness, and leakage fields |
| `docs/data/baselines/<date>/manifest.json` | Verify `manifest.sha256` and every listed file hash before reading content; reject schema drift or mutation |
| `data/source-evidence.json` inside a baseline | Treat `gap` as unknown/unavailable coverage, surface its reason, and never coerce it to zero events |
| `data/model-status.json` inside a baseline | Surface shadow/promotion state exactly; do not infer promotion from artifact presence |
| local `intelligence/runs.jsonl` | Read structured task/source outcomes and freshness; do not expose local paths, credentials, or raw cached bodies |

Consumers may summarize verified artifacts, create review checklists, or display coverage and model
status. They must not mutate immutable snapshots, bypass identity resolution, invent missing feeds,
promote a model, install the launchd template, or execute notifier text.

## Recommended additive workflow

1. Run the producer pipeline and snapshot verification with the repository Python environment.
2. Pass only the verified manifest plus normalized reports to the consumer. Large raw/cache data stays
   under the user-owned data root and outside Git.
3. Require the consumer to cite snapshot ID, cutoff, code version, and explicit source gaps in any
   recommendation derived from the handoff.
4. Keep proposed interpretations separate from machine facts. Any new feature or source returns to
   the signal-card and walk-forward gates before affecting forecasts.
5. Review and apply any future Claude-side integration as a separate change owned by that surface.

## Compatibility boundary

No Claude-owned files were found or changed in this worktree. If such a surface is added later, it
should call the stable producer interfaces or read verified artifacts rather than duplicate ingest,
model, or snapshot logic. Paths committed to configuration must use `$HOME` or `~`, never a
machine-specific home directory. Git artifacts must contain no assistant or vendor attribution.
