# 2026 in-person draft runbook

The ESPN draft is `OFFLINE`; there is no live pick feed. Draft day uses the manual board at
`/draft`. Never run the draft from `next dev`: build once, serve the production bundle, and keep
the browser on the local production server.

## Current risks

- On 2026-08-26, `player_value` was last computed 2026-06-30; `news_articles` and `trending`
  were last updated 2026-06-11.
- The daily GitHub Actions ETL is firing, but fails in `history_ingest.py` before news and value
  steps. It requests nflverse seasonal data for 2025, which currently returns HTTP 404.
- Comments and `DATA_SOURCES.md` claim a separate 30-minute news workflow. No such workflow is
  present; news is only a step in the blocked daily ETL. For this draft, refresh locally using the
  commands below. Repairing the scheduled workflow is post-draft work.

## T-24h: refresh from the main checkout

The pre-draft refresh intentionally runs the engine and pipeline on local `main`, not a v7
worktree. It writes through the service-role credentials in the main checkout's `pipeline/.env`.
Stop if `git status` shows unexpected overlapping edits; do not switch or clean the checkout.

```bash
BLITZ_MAIN="$HOME/Documents/GitHub/blitzboard"
BLITZ_RELEASE="$HOME/Documents/GitHub/blitzboard/.worktrees/v7-integration"
cd "$BLITZ_MAIN"
git status --short --branch
git rev-parse --short HEAD

cd "$BLITZ_MAIN/pipeline"
"$BLITZ_MAIN/pipeline/.venv/bin/python" player_ingest.py --trending
"$BLITZ_MAIN/pipeline/.venv/bin/python" news_sentiment.py
"$BLITZ_MAIN/pipeline/.venv/bin/python" value_engine_run.py --engine vorp --season 2026
"$BLITZ_MAIN/pipeline/.venv/bin/python" value_engine_run.py --engine monte_carlo --season 2026
"$BLITZ_MAIN/pipeline/.venv/bin/python" publish_snapshot.py --engines vorp monte_carlo
set -a
source "$BLITZ_MAIN/pipeline/.env"
set +a
"$BLITZ_MAIN/pipeline/.venv/bin/python" "$BLITZ_RELEASE/pipeline/draft_freshness.py" --value-max-hours 36 --news-max-hours 12
```

The final command must print `PASS`. If news fails but values succeed, rerun `news_sentiment.py`
once. If it still fails, keep the fresh values, record that news is stale, and do not represent the
trending signal as current. If either value engine is stale, the refresh is blocked: do not proceed
on June rankings.

## Draft morning: production serve

Use the release checkout containing approved U2 and U4. Its `frontend/.env.local` must contain only
the normal public frontend variables; the service-role key stays in `pipeline/.env` and must never
enter the Next.js environment. The expected frozen lane is shown below; adjust `BLITZ_RELEASE` if
the release lane path differs at freeze.

```bash
BLITZ_RELEASE="$HOME/Documents/GitHub/blitzboard/.worktrees/v7-integration"
cd "$BLITZ_RELEASE/frontend"
npm run build
npx next start -p 3100
```

Leave that terminal running. In a second terminal:

```bash
BLITZ_RELEASE="$HOME/Documents/GitHub/blitzboard/.worktrees/v7-integration"
"$BLITZ_RELEASE/scripts/prod-route-smoke.sh" http://127.0.0.1:3100
```

All three route markers must pass. Open `http://127.0.0.1:3100/draft`, confirm the correct league,
12 teams, roster/scoring rules, draft slot, keeper list, and player search. Enter two disposable
picks, reload, choose **Restore draft**, and confirm both return; then use **Start fresh** and confirm
the discard before entering real keepers.

## At the table

1. Connect the laptop to power and disable automatic sleep for the evening.
2. Keep the production-server terminal open. Do not restart into `next dev`.
3. Enter all keepers before pick 1; keepers lock once drafting begins.
4. Record each announced pick immediately. Use **Edit** beside any past pick to correct it in place.
5. After every round, glance at the recent-picks list and confirm pick count and team on the clock.
6. If the tab closes, reopen `/draft`, choose **Restore draft**, and verify the last pick before continuing.

## Failure recovery

- **Browser crash/tab close:** reopen `/draft` and restore today's league/date save.
- **Wrong past pick:** select **Edit** on that pick, search the correct player, then **Replace**.
- **Next server exits:** rerun `npx next start -p 3100` from the already-built `frontend` directory;
  do not rebuild during the draft unless `.next` is missing.
- **Laptop dies:** switch to the standalone Excel war room at
  `artifacts/Smores_2026_Live_Draft_Backup_12-Team.xlsx` (11-team variant beside it) on any
  machine with a spreadsheet app; it carries the same August 26 expert board, pick log, and
  suggested-picks formulas, fully offline.
- **Port 3100 busy:** find and stop only the stale BlitzBoard process, then restart on 3100. Do not
  change the bookmarked URL under pressure.
- **Network loss:** the local server and manual pick persistence continue to work. Avoid refreshing
  data-dependent pages; keep using the already-loaded draft tab.

After the final pick, leave the tab open until the pick count is confirmed. The browser save is
keyed by league and local date; preserve it through the end-of-night review.
