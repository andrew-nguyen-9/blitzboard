# NFL status/news point-in-time schema

This contract covers the 2025 NFL season only. All tables are append-only Parquet files under
`~/.blitz_engine`. `as_of_utc` means when the fact became publicly knowable. When a source does
not publish that timestamp, it is fetch time and `as_of_is_fetch_time=true`.

Every table uses `source_record_id` as its idempotency key. A source ID is preferred; otherwise
the ingest hashes the source payload excluding ingest-only metadata. An already-seen observation
is preserved, not updated. A changed status has a different payload and becomes a new row.

## `status_injury_reports.parquet`

Source: nflverse `injuries_2025.parquet` (official weekly report vocabulary). Expected refresh:
Wed/Thu/Fri after reports publish. Known gap: nflverse may not expose a publication timestamp;
those rows are explicitly fetch-time observations.

| Column | Type |
|---|---|
| season, week | int64 |
| team, gsis_id, source_player_id, player_name | string (gsis_id nullable) |
| report_date | date/string supplied by source |
| practice_status, game_status, injury | string |
| source_url, as_of_utc, resolution_failed, source_record_id | string |
| as_of_is_fetch_time | bool |

Key: `(source_record_id)`. `game_status` retains nflverse's existing vocabulary; no inferred
status is produced.

## `status_inactives.parquet`

Intended source: official NFL 90-minute inactive list. Expected refresh: once per game near lock.
Known gap: no stable, documented, free official machine feed was verified for this unit, so the
default command does not fabricate this table from roster snapshots. The persistence API accepts
an explicit `Feed` adapter with the pinned schema below and fails loud/write-nothing on drift.

| Column | Type |
|---|---|
| season, week | int64 |
| game_id, team, gsis_id, source_player_id, player_name | string |
| inactive | bool |
| source_url, as_of_utc, resolution_failed, source_record_id | string |
| as_of_is_fetch_time | bool |

Key: `(source_record_id)`.

## `status_roster_events.parquet`

Sources: nflverse weekly rosters and depth charts. Expected refresh: daily and after transaction
windows. Weekly roster states cover reserve/IR/PUP-style status changes; depth rows are published
snapshots. Known gaps: they are snapshots, not signing/cut prose, and the current depth-chart feed
may omit player names and publication timestamps.

| Column | Type |
|---|---|
| season | int64 |
| team, gsis_id, source_player_id, player_name | string |
| event_type, roster_status, depth_position, depth_rank | string |
| effective_date, source_url, as_of_utc, resolution_failed, source_record_id | string |
| as_of_is_fetch_time | bool |

Key: `(source_record_id)`.

## `status_news.parquet`

Source: ESPN's free public NFL news response. Expected refresh: daily/ad hoc. `raw_text` is the
verbatim description (or headline when description is absent); no NLP, sentiment, entity
extraction, or inference is performed. Known gaps: article metadata generally lacks player IDs,
so rows are retained with null `gsis_id` and a resolution reason; article bodies are not copied.

| Column | Type |
|---|---|
| season | int64 |
| gsis_id, source_player_id, player_name | string (nullable) |
| raw_text, source_name, source_url, as_of_utc | string |
| as_of_is_fetch_time | bool |
| resolution_failed, source_record_id | string |

Key: `(source_record_id)`.

## Identity and failure contract

All adapters must emit `gsis_id` or a typed `source_player_id`. Resolution uses only
`player_ids.parquet`; unresolved rows remain present with `resolution_failed`. Each run reports
resolved/unresolved counts and the measured rate. Fetching and validation finish before the table
write; source errors or unrecognized shapes leave that table untouched and return non-zero.

