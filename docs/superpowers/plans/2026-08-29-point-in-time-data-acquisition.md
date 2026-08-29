# Point-in-Time 2026+ Data Acquisition and Archive Plan

**Status:** operational research plan only. No collector, schema, credential, vendor access, or
production ingestion is authorized by this document.

**Authority:** shipped v5 remains production authority. Historical fixtures remain development
evidence. The first untouched 2026+ window is confirmation evidence only if it is frozen before
outcomes and preserved with lawful provenance.

## 1. Decision this plan enables

Create the minimum lawful, immutable evidence base needed to answer four separate questions:

1. what public/player information BlitzBoard actually knew at a draft decision time;
2. what kind of market object was available then—ADP, rank, projection, consensus, or recommendation;
3. whether a displayed player survived until the user's next scheduled pick;
4. whether later realized fantasy outcomes support or refute the preseason forecast.

The archive must keep those questions separate. A later rank list cannot backfill a missing draft-
day rank; realized games cannot fill a preseason projection; and a platform draft history does not
grant permission to redistribute that platform's market data.

## 2. Non-negotiable point-in-time rules

- Record `source_as_of_utc` and `retrieved_utc` separately.
- Raw receipts are append-only. Corrections create a new revision linked to the prior receipt.
- Every normalized row identifies its raw receipt, normalizer version, identity-map version, and
  league/scoring format.
- A missing field stays missing. Do not forward-fill across a transaction, injury, team change, or
  source-product change without an explicit documented rule.
- Training, validation, and untouched confirmation windows are assigned before outcomes are read.
- The archive records permission and retention scope alongside data; technical access alone is not
  authorization.
- No credential, cookie, recovered partner key, private league identifier, or proprietary raw body
  enters a shared artifact or client bundle.

## 3. Snapshot families

### A. Player identity and roster state

Required normalized fields:

```text
snapshot_id, source_player_id, canonical_player_id, full_name,
position, nfl_team, roster_status, experience_years, rookie_flag,
depth_role_raw, source_as_of_utc, retrieved_utc, raw_receipt_id,
identity_map_version, normalization_state
```

`rookie_flag` must come from a declared identity/roster source, not from absence in last season's
weekly outcomes. `normalization_state` distinguishes matched, ambiguous, source-missing, retired/
inactive, and unresolved-ID cases.

### B. Health and depth evidence

Required fields:

```text
snapshot_id, canonical_player_id, evidence_kind, status_raw,
practice_status, depth_role_raw, effective_utc, source_as_of_utc,
retrieved_utc, source_receipt_id, correction_of, degradation_reason
```

This family informs health/startability only. It must never be called next-pick availability.

### C. Market/source products

Required fields:

```text
snapshot_id, source_id, source_product_id, product_kind,
season, scoring, teams, qb_format, roster_preset, expert_set,
canonical_player_id, ordinal_rank, adp, projection,
source_as_of_utc, retrieved_utc, raw_receipt_id,
license_receipt_id, redistribution_allowed, display_allowed
```

`product_kind` is one of `adp`, `rank`, `projection`, `expert_consensus`, or `recommendation`; a row
cannot silently change kinds. Store only fields actually supplied by that product. A normalized
consensus rank is not a vendor recommendation.

### D. BlitzBoard preseason forecast

Required snapshot-header fields:

```text
forecast_snapshot_id, canonical_player_id, league_config_key,
engine_version, code_commit, input_snapshot_ids,
generated_utc, evidence_state, degradation_reasons
```

Required production component:

```text
conditional_projection, projection_horizon,
distribution_version, production_as_of_utc
```

Required startability component when emitted:

```text
p_startable, effective_season, effective_week,
p_startable_definition_version, startability_as_of_utc
```

These are logical receipt components, not a requirement to create separate database tables. Keep
conditional projection, weekly startability probability, and any eventual next-pick survival
forecast as distinct named fields, horizons, versions, and calibration reports. A weekly
`p_startable` must not silently discount a season projection; see the
[startability handoff experiment](2026-08-29-startability-snapshot-handoff-experiment.md).

### E. Draft decision history

Required fields:

```text
draft_id, consent_scope, source_platform, league_format,
teams, slot, roster_rules, scoring_rules, pick_number,
seat, canonical_player_id, pick_timestamp_utc,
pick_clock_limit_seconds, remaining_seconds_at_submission,
autopick_state, market_snapshot_id, observed_utc,
anonymized_seat_id, raw_receipt_id
```

When timestamps, remaining clock, or autopick flags are unavailable, store null plus a reason; do
not infer elapsed/remaining time from pick order, network receipt time, or the next event. A draft
decision record must preserve the exact ordered prefix visible at each user turn. Clock fields are
optional research inputs, not a requirement that justifies expanding collection permissions.

### F. Realized weekly outcomes

Required fields:

```text
outcome_snapshot_id, season, week, canonical_player_id,
fantasy_points_by_scoring, appeared, eligible_status,
source_as_of_utc, retrieved_utc, correction_of, raw_receipt_id
```

Weekly revisions remain available; a final-season freeze is a new snapshot, not an overwrite.

## 4. Source approval boundary

Before any acquisition code exists, create a source approval receipt answering:

1. exact endpoint/export and product kind;
2. documented, contracted, first-party, or user-supplied access basis;
3. commercial-use, derived-feature, display, caching, archival, deletion, and redistribution rights;
4. rate limits and required attribution;
5. raw-data retention window and whether hashes/aggregates may remain after deletion;
6. approving person/date and terms/version archived;
7. allowed environments and credential owner;
8. incident contact and disable switch.

Priority order:

1. documented first-party or licensed public datasets with per-dataset terms;
2. documented platform APIs within their stated use and rate limits;
3. contracted vendor APIs whose agreement explicitly covers the intended product behavior;
4. private user-supplied exports stored only for that user and declared study scope;
5. unresolved/publicly reachable endpoints remain disabled.

FantasyPros recovered-key discovery in `pipeline/calibration_run.py` is historical research code, not
an approved acquisition method. ESPN private sync is user-authorized interoperability, not authority
to build a redistributable corpus. Sleeper's API page permits non-commercial read-only access, but its
general terms separately require Sleeper authorization for third-party retrieval and say user
authorization is insufficient; therefore no commercial third-party production use is approved by
technical API availability. Sleeper/FantasyPros commercial, display, and retention boundaries require
written resolution before collection for that use. See the official/public boundaries checked on
2026-08-29 in
[Sleeper API docs](https://docs.sleeper.com/), [Sleeper terms](https://support.sleeper.com/en/articles/5486620-general-terms-of-use),
[FantasyPros API terms](https://api.fantasypros.com/public/v2/terms-of-use),
[FantasyPros access guidance](https://support.fantasypros.com/hc/en-us/articles/49749297704475-How-do-I-request-access-to-the-FantasyPros-API),
and [Disney/ESPN terms](https://disneytermsofuse.com/english/). Terms can change; archive the
controlling version and obtain project-specific approval. This plan does not manufacture permission.

## 5. Receipt and manifest contract

Each acquisition run emits one manifest:

```text
receipt_id
schema_version
source_id / source_product_id / product_kind
source_url_or_endpoint
request_parameters_redacted
source_as_of_utc / retrieved_utc
permission_basis / license_receipt_id
raw_sha256 / normalized_sha256
raw_row_count / normalized_row_count
duplicate_count / unmatched_identity_count / ambiguous_identity_count
missingness_by_required_field
normalizer_version / identity_map_version / code_commit
runtime_environment
raw_retention_deadline / redistribution_allowed / display_allowed
supersedes_receipt_id
```

Secrets and request authorization headers are excluded before hashing the shareable manifest. If a
raw receipt cannot lawfully be retained, retain only the permitted manifest/hash/aggregate and record
that byte replay is unavailable.

## 6. Identity normalization

Match in this order:

1. stable source-to-canonical ID mapping already verified for the season;
2. exact normalized name + position + team within the same as-of snapshot;
3. alias table with a recorded human-reviewed decision;
4. unresolved/ambiguous state.

Never silently choose between same-name players or use future team knowledge to resolve a past
snapshot. Mapping corrections version the identity table and re-normalize into a new derived receipt;
they do not mutate the raw input.

Quality slices must report rookies, team changes, free agents, ambiguous IDs, K/DST aliases, and
players missing prior-season history separately.

## 7. Proposed 2026 cadence

### 7.1 Current-date constraint

The official NFL calendar lists preseason Week 3 as August 27–29 and the 2026 opening game on
September 9. Because this plan is being prepared on August 29, the desired four-to-eight-week 2026
preseason collection window has already passed. It cannot be recreated from current pages or later
revisions ([official 2026 schedule](https://www.nfl.com/schedules/2026/by-week/reg-1);
[official Week 1 release](https://www.nfl.com/news/2026-nfl-schedule-release-complete-slate-of-week-1-games)).

Therefore:

- inventory any already-existing lawful, timestamped 2026 receipts before proposing collection;
- never label a newly retrieved current rank as an earlier-August snapshot;
- begin prospective collection only after the source-approval gate, even if that leaves few 2026
  observations;
- label a late-August/early-September 2026 sample as a partial-window pilot, not a full preseason
  confirmation set;
- reserve 2027 as the first full-window confirmation season if no compliant earlier 2026 archive
  exists.

That inventory found one checked-in receipt:
`docs/data/baselines/2026-08-25`. Its content-hashed manifest verifies as
`intelligence-2026-08-25` with an as-of time of 2026-08-26T00:00:00Z. It records source-level
evidence for 2,930 nflverse weekly-roster rows and 469,064 depth-chart rows, plus explicit gaps for
injuries, ESPN news, and official inactives. It contains zero forecast rows, no market rank/ADP,
no ordered draft histories, and no next-pick survival labels; detailed live input rows are not in
Git. Its general “public no-key” policy string is not a per-dataset license receipt. Treat it as a
useful identity/roster/depth provenance pilot only after per-dataset license and retention review.
It cannot rescue the missing market/draft window or authorize a production view.

The relative cadence below is the target for the remaining authorized 2026 window and for a complete
2027+ cycle. Exact dates must continue to come from the official NFL and approved platform calendars,
not guessed constants:

| Window | Player/roster | Health/depth | Market board | Draft histories | Forecast |
|---|---|---|---|---|---|
| four to eight weeks before Week 1 | daily | daily | daily per approved format/source | lawful connected/export events | daily after inputs |
| final two preseason weeks | daily + transaction event | daily + material event | up to 4× daily only if licensed/rate-safe | every consented completed room | every accepted input batch |
| final 72 hours before Week 1 | every accepted roster event | material event + scheduled freeze | declared freeze cadence | every consented room | immutable release candidates |
| regular season | weekly correction snapshots | weekly/event for evaluation | no preseason backfill | no collection beyond consent | weekly outcome evaluation |

At least one daily/final window remains untouched confirmation. Do not repeatedly tune against every
2026 room and later call 2026 confirmation. If the late 2026 sample is too small or narrow, use it
only for pipeline/data-quality rehearsal and preserve 2027 for confirmation.

## 8. Draft-history privacy and consent

- Maintain a data-processing inventory for every collection path: element, purpose, source, owner,
  recipient, storage location, retention, deletion behavior, and permitted downstream use. NIST's
  voluntary Privacy Framework treats collection through disposal as one lifecycle and explicitly
  calls for inventorying elements, purposes, actions, processors, and environments
  ([NIST Privacy Framework](https://www.nist.gov/privacy-framework);
  [Framework Core](https://www.nist.gov/document/nist-privacy-frameworkv10pdf)).
- Default research derivative replaces account, league, and seat identifiers with scoped random IDs.
- Exact timestamps and remaining-clock traces may still fingerprint a room after direct identifiers
  are removed. Keep exact seconds in the restricted raw layer only when the approved clock analysis
  needs them; publish coarse preregistered bands and suppress small cells in ordinary derivatives.
- Store the re-identification link separately with narrower access and a deletion path.
- Consent names whether the data support sync only, local evaluation, aggregate research, or model
  fitting; no broad consent inference.
- Do not collect chat, team names, manager names, prize amount, or unrelated league metadata.
- User deletion removes credentials, raw imports, re-identification links, and any derivative that
  remains identifiable under the declared policy.
- Small subgroup reporting is suppressed or aggregated to avoid singling out a participant.
- Learned opponent profiles require separate explicit authorization; live descriptive room features
  do not imply permission to train across users.

## 9. Pre-ingestion quality gate

Reject/quarantine a batch when any hard gate fails:

- missing permission/license receipt;
- missing source product kind or league/scoring format;
- source-as-of later than the decision time it is supposed to represent;
- duplicate canonical player rows without a declared aggregation rule;
- identity ambiguity above the frozen tolerance;
- impossible rank/ADP values or wrong-format payload;
- raw/normalized hash mismatch;
- secret/credential scanner finds sensitive material;
- retention/display flag conflicts with the intended use.

Soft degradation does not disappear. Record missing rank coverage, unmatched players, stale age,
format mismatch, and partial-source coverage so UI/model tests can exercise honest fallback.

## 10. Freeze and split protocol

Before model fitting:

1. enumerate all available rooms/snapshots without outcome inspection;
2. group by draft room and source snapshot to prevent pick-level leakage;
3. allocate chronological training, tuning, and final confirmation windows;
4. hash the allocation file and record sample counts by format/team/slot/round;
5. freeze feature definitions, missingness handling, metrics, and major-slice gates;
6. unlock confirmation only once per preregistered model family.

If the final window lacks enough 10/14-team, superflex, deep-bench, rookie, or degraded-source cases,
report those slices as underpowered. Do not move cases across the boundary after outcomes.

## 11. Next-pick survival label generation

For each user decision at pick `t` and each candidate available at `t`:

```text
label = 1 if candidate remains undrafted immediately before the user's next scheduled pick
label = 0 if candidate is selected by an intervening seat
label = censored if the room ends, disconnects, or the next turn cannot be reconstructed
```

Archive the horizon, snake direction, current/next pick numbers, candidate market gap, league format,
visible roster state, and intervening ordered picks. Generate labels from ordered draft history, not
from a later final-roster snapshot. Player and tier survival labels need separate definitions.

## 12. Monitoring and incident response

Every run reports:

- expected versus received rows;
- stale-age distribution;
- source/format coverage;
- identity-match state;
- duplicate and schema errors;
- permission/retention status;
- hash and append-only checks;
- whether downstream forecast publication was allowed or blocked.

On source drift, permission change, suspected credential exposure, or silent field-semantic change:

1. stop that source's ingestion and publication;
2. preserve permitted evidence and logs;
3. mark affected normalized snapshots revoked/degraded without deleting audit links;
4. hide source-specific UI claims and fall back to unknown/missing;
5. reapprove terms/schema and create a new source-product version before resuming.

## 13. Exact likely repository seams after approval

No speculative files should be created now. After a source and storage design are approved, likely
changes are:

- one timestamped migration in `db/migrations/` for additive snapshot/receipt/provenance tables;
- `db/schema.sql` mirror;
- `frontend/lib/types.ts` and `frontend/lib/queries.ts` for null-safe provenance reads;
- one source-specific pipeline collector in an approved location, not a generic scraping framework;
- an identity normalizer reusing existing player ID maps;
- artifact-manifest/hash helpers already used by current experiments;
- focused migration, normalization, provenance, missingness, and secret-boundary tests;
- a dated modeling preregistration for survival calibration.

Do not add a provider abstraction until two approved sources prove a common interface. Do not create
a production next-pick field until real labels and out-of-time calibration pass.

## 14. Acceptance and rollback

The archive program can begin only when:

- source permission and retention/display rights are explicit;
- source/as-of/retrieved/product-kind fields are mandatory;
- immutable receipt and correction behavior is tested;
- identity ambiguity and missingness are reported, not silently filled;
- consent, deletion, access control, and incident owner are documented;
- temporal split and confirmation window are frozen;
- no production view or score depends on an unvalidated snapshot.

Rollback disables the affected collector and publication path. Keep permitted manifests and audit
links; do not destructively roll back additive tables or rewrite historical receipts. UI readers fall
back to “source/date unavailable,” and v5 scoring continues unchanged.

## 15. First bounded action

Complete one no-code source-approval and sample audit for a single candidate 2026 market product:
obtain terms/permission, capture the exact schema and format variants, define raw retention/display
rights, and count identity/missingness on a non-production sample. If any permission question is
unresolved, stop there. This action is independently reviewable and does not require a collector,
database migration, or vendor claim.
