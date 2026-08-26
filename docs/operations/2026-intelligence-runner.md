# 2026 intelligence seasonal runner

`run_seasonal_cycle` is the one idempotent primitive for manual and unattended operation. Tasks
declare `daily`, `practice`, or `gameday`; the runner applies the NFL-cycle defaults, prevents
overlap with an exclusive lock, and records source/task results in
`<data-root>/intelligence/runs.jsonl`. A successful task is not repeated on the same UTC date. A
failed task remains retryable and is never disguised as success or stale data.

The optional notifier is a caller-supplied function. Tests use an in-memory collector; the runner
does not execute arbitrary shell strings or send notifications by itself. The later baseline entry
point may connect it to a user-owned notifier without storing credentials.

## launchd template

`com.blitzboard.intelligence.plist.template` is deliberately uninstalled. Copy it outside the
repository, replace `__WORKTREE__`, `__PYTHON__`, and `__DATA_ROOT__` with explicit paths, validate
with `plutil -lint`, then install it manually only after reviewing the commands. The schedule runs
one low-priority daily check plus Wed/Thu/Fri and Sunday opportunities; the runner itself decides
which tasks are due and deduplicates repeated invocations.

The template contains no secrets. The no-key core must work without environment credentials;
optional free-key adapters refer only to documented environment-variable names in their own source
cards. Logs and the structured ledger live under the local data root, not Git.

## Operational QC

- Alert on task failure and source-specific freshness rather than serving stale data as current.
- Keep request budgets in the response cache and record 429/schema errors verbatim in the ledger.
- Report compressed cache and snapshot sizes against the 10 GB seasonal budget.
- Preserve detailed raw data for the current season; after the season, retain normalized snapshots,
  manifests, aggregates, and research findings under the documented retention policy.
- Never install the template, rotate credentials, publish, or merge as part of an unattended run.
