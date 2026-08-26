# C02 remote reproduction — independent evidence

Date: 2026-08-26

Production commit: `edbcc4d743b447ebcbbfe84a0e1210380c6250d1`

Reviewer branch: `v6/c02-reproduction`

This is reviewer evidence, not the official C02 verdict.

## Blind findings (recorded before reading `C02-claude.md`)

The bundle SHA-256 matched `a8f7654fbb7f132725a956f05d42b31e8ca0ac4f57ae7a4524207073fe265e5f`, and `v6/bench-portfolio` resolved to the required production commit.

The focused remote adversarial suite produced three failures and three passes:

- **Contradicted:** proactive replacement is restricted to the same position. A legal roster improvement requiring a different-position bench drop is skipped.
- **Contradicted:** `waiver_cost` is subtracted only during season aggregation. It never participates in the claim decision, so a negative-net transaction is still made.
- **Contradicted:** `waiver_moves_per_week=1` and `proactive_moves_per_week=1` permit one emergency plus one upside claim in the same week. There is no combined weekly hard bound.
- **Proven:** the exact 15% upgrade boundary deterministically does not transact.
- **Proven:** a low-preseason-projection free agent with observed breakout production is eventually acquired using prior-week information.
- **Proven:** a dropped player returns to the shared pool and can be claimed later in the same priority pass.

Code inspection independently confirmed that `started_points` remains the primary metric, reverse standings use `(season_wins, seat)` ordering, the pool is shared and finite, emergency/upside counters are distinct, season caps decrement on both claim types, decision frames reject injected current-week rows, and paired sample arrays are stored by season and seat.

## Calibration blind reproduction

All committed frozen-input content hashes match `promotion-v3.json`:

| Input | SHA-256 |
|---|---|
| snapshot content | `386b7afdb1b8549a99cd78a73ed6abd7c1533a9e0a0438e271848c82f4a3f8dc` |
| benchmarks content | `9607dedab67cce3b6463a6363f84c3a0249c9c94619aa4ad33e0ea3f30c0bf28` |
| v5 boards content | `5898efdd6e483548bb893a18edbb1060b8b2f901edb6cc608e4053b2333642e3` |
| v6 boards content | `0590fd2cdc5fafe9d74ef5f782b3478c962d84229023474faf9cc52896a6eff4` |

The v5 boards reproduced from git archive `01f01d3c5f9c00a046edd43707db75ce1426c0e8`; the v6 boards reproduced from the C02 tree. Both gzip files were byte-identical to the committed artifacts. The offline report was identical after removing only `generated_utc`.

The player-calibration manifest and amendment are byte-identical between their reviewer freeze commit and `v6/bench-portfolio-review`. `promotion-v1.json` and `promotion-v2.json` are byte-identical to their introduction commits. No snapshot/network command was run.

The calibration thresholds fail for 1QB ECR, 1QB ADP, and 2QB superflex-ECR comparisons and pass only the superflex comparison. No coefficient promotion is recorded. Missing `team_change` and `low_availability` cohorts are explicitly reported as non-computable.

## Producer-claim reconciliation

`C02-claude.md` accurately discloses same-position-only proactive swaps and post-hoc transaction-cost accounting, but presents both as sufficient. They contradict the stricter remote audit requirements. It does not disclose that the two per-kind weekly limits can combine into two transactions in one week.

The producer's test counts reproduce when reviewer-owned failures are excluded. Its calibration content hashes, arm provenance, benchmark failures, explicit retrieval deviations, non-computable cohort note, immutable-manifest claims, and no-coefficient-promotion disposition also reproduce.

## Requirement matrix

### Evaluator

| Requirement | Result | Evidence |
|---|---|---|
| Proactive waivers use decision-time information only | proven | projections use preseason plus observations from completed weeks; active leakage check runs before each lock |
| Healthy lineup can replace stale low-ceiling bench player | proven | production and remote focused tests |
| Low-preseason genuine breakout can be acquired | proven | remote breakout test passes using completed-week production |
| Feasible improvement may drop a different-position nonstarter | contradicted | remote test fails; `_best_upgrade` only compares same-position bodies |
| Transaction cost controls transact/no-transact decision | contradicted | remote high-cost test still records a claim; cost is subtracted only after the season |
| Exact-boundary behavior deterministic | proven | exact 15% edge does not transact |
| Reverse-standings priority controls contests | proven | code order `(season_wins, seat)` and production contested-pool test |
| Free-agent pool shared and finite | proven | one mutable league pool; claimed player is removed |
| Dropped players return correctly | proven | remote two-team priority-pass test |
| Weekly and season caps are hard bounds | contradicted | season bound is proven; weekly emergency + upside limits permit two moves when the stated weekly cap is one |
| Emergency and upside classified distinctly | proven | separate counters and focused tests |
| K/DST streaming uses point-in-time forecasts | proven | production streaming test and shared point-in-time upgrade path |
| Skill-player churn excludes future information | proven | projection data flow and active decision-frame guard |
| Identical runs are array deterministic | proven | production repeat-run equality across result arrays |
| Seed change changes stochastic outcomes | proven | production reseed test |
| Injected leakage trips active detector | proven | production injected-current-week test |
| `started_points` remains primary | proven | `metric` is the mean of `started_points`; transaction cost is expressed in points |
| Paired H2H/playoff/champ samples and ties | incomplete | shapes, accounting, and deterministic seat-order ties are proven; result objects do not retain seed identity and `paired_ci` cannot verify that arms actually share seeds |
| Cost/proxy units documented and internally consistent | contradicted | point cost is documented, but it does not influence the decision it prices; H2H/playoff proxies remain gross while primary points are net |

### Calibration

| Requirement | Result | Evidence |
|---|---|---|
| All frozen-input hashes verify | proven | independent decompressed-content SHA-256 matches `promotion-v3.json` |
| Boards and report reproduce offline | proven | v5/v6 board content and gzip bytes match; normalized report matches |
| No fresh fetch or snapshot overwrite | proven | only `boards`/`report` cores ran with redirected temporary output |
| v5 immutable baseline and v6 candidate provenance | proven | v5 git archive at `01f01d3c`; v6 at `edbcc4d`; recorded hashes match |
| Player matching, unmatched rates, formats, cohorts, decomposition | proven | all three manifest formats; top-100 unmatched rate 0; required computable cohorts and component rows present |
| Every manifest threshold calculated | incomplete | report calculates unmatched, Spearman, and weighted-error thresholds; it omits `position_or_cohort_material_regression` and `season_evaluator_no_regression_tolerance` (deterministic failures are asserted, not independently enumerated in the report) |
| Retrieval deviations explicit; no silent format substitution | proven | URL/API and 2QB-vs-superflex deviations are explicit in report and promotion record |
| Missing/non-computable cohorts reported | proven | `team_change` and `low_availability` are named as non-computable rather than omitted silently |
| Failed/inconclusive thresholds do not become promotion | proven | three comparisons fail; coefficient promotion is `NONE_ATTEMPTED` |
| No coefficient changed or promoted | proven | no shaping-constant diff from baseline; executed record states no promotion |
| v1/v2, reviewer manifest, and amendment immutable | proven | independent hashes match their introduction/freeze commits |
| Calibration-only evidence non-authoritative for C05 | proven | executed record defers promotion authority to C05 |

## Recommended disposition

Recommend that the original C02 remain blocked for C02A correction. The three deterministic evaluator contradictions require production changes; the missing calibration threshold calculations should be completed or explicitly removed by an authorized manifest amendment. The primary reviewer owns the official verdict.
