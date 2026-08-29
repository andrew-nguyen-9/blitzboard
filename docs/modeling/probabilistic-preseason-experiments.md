# Probabilistic preseason forecast experiments

Status: exploratory C09 extension, frozen before outcome analysis on 2026-08-29.

These experiments ask whether BlitzBoard can make its preseason player forecasts more honest
and more useful without changing shipped v5 behavior. They are not C05 fit, confirmation, or
promotion evidence. The 2018, 2021, and 2024 outcomes have already been inspected elsewhere, so
all results are synthetic development evidence. A future promotion still requires a genuinely
untouched, point-in-time season.

## Decision ledger

### Where to implement

Options considered:

1. build a new forecasting stack;
2. extend the existing hierarchical projector and ensemble immediately;
3. add a small rolling-origin evaluator around the existing corpus, calibration metrics, and
   blind-market harness.

Selected: option 3. It is reversible, introduces no dependency, cannot alter production, and
tests the information and scoring contract before any model integration. Supported methods can
later become members of `blitz_engine.ensemble`; unsupported methods remain experiment results.

### What is knowable from the current archive

Options considered:

1. treat the fixture's `boom` and `bust` values as archived preseason quantiles;
2. reconstruct vendor forecasts from realized outcomes;
3. forecast from prior-only weekly data, calibrate against later seasons, and identify missing
   point-in-time inputs explicitly.

Selected: option 3. The fixture documentation says `boom` and `bust` are derived stand-ins, not
vendor forecasts. They cannot validate real preseason uncertainty. Archived historical ADP is a
causal market rank at its snapshot date, but it is not a points distribution.

### Evaluation design

Options considered:

1. random row-level cross-validation;
2. a single recent-season holdout;
3. expanding rolling-origin evaluation with every training season strictly earlier than the
   target season, plus position and availability subgroups.

Selected: option 3. Player seasons are serially dependent and the model must not learn from a
future season. The final 2024 fold is reported separately because aggregate performance can hide
recent-era drift.

## Evidence hierarchy

| Grade | Source | What it supports | What it does not support |
| --- | --- | --- | --- |
| A | Gneiting, Balabdaoui, and Raftery (2007), *JRSS B*, DOI 10.1111/j.1467-9868.2007.00587.x | Evaluate distributions by calibration, sharpness, PIT diagnostics, and proper scores | A particular NFL likelihood |
| A | Bracher, Ray, Gneiting, and Reich (2021), *PLOS Computational Biology*, DOI 10.1371/journal.pcbi.1008618 | Weighted interval score for quantile forecasts; decomposition into width and miss penalties | Direct fantasy-football validation |
| A | Angelopoulos and Bates (2023), *Foundations and Trends in ML*, DOI 10.1561/2200000101 | Distribution-free conformal coverage under its exchangeability assumptions | Automatic validity under season drift or tiny subgroups |
| A | Yao, Vehtari, Simpson, and Gelman (2018), *Bayesian Analysis*, DOI 10.1214/17-BA1091 | Combine predictive distributions using out-of-sample predictive utility | That the repository's current pseudo-BMA weights are already optimal |
| A | Gneiting and Ranjan (2013), *JRSS B*, DOI 10.1111/j.1467-9868.2012.01035.x | A linear pool of distributions generally needs recalibration | Permission to average `boom`/`bust` stand-ins |
| A | Lee and Liu (2022), *Judgment and Decision Making*, DOI 10.1017/S1930297500008901 | Direct evidence from 1,350 Sleeper leagues that human drafting is sequential, relatively narrow, and influenced by preceding picks | A universal optimal draft policy or modern platform parity |
| A | Becker and Sun (2016), *Journal of Quantitative Analysis in Sports*, DOI 10.1515/jqas-2013-0009 | Fantasy roster decisions should consider uncertainty and constraints, not only expected points | Accuracy of current player distributions |
| B | Frozen Fantasy Football Calculator preseason ADP snapshots already used by C09 | Blind historical market ordering and bounded human-like opponent picks | Proprietary ESPN, Sleeper, or FantasyPros recommendation logic |
| C | Vendor methodology pages | Candidate feature inventory and product behavior | Reproducible algorithms, calibrated distributions, or independent accuracy |

Grade A means peer-reviewed primary research or direct primary data analysis with an inspectable
method. Grade B means a reproducible primary market artifact whose sampling process is only partly
observable. Grade C is descriptive and hypothesis-generating only.

## Frozen hypotheses

All comparisons are paired on identical player-season rows. Confidence intervals use a
season-cluster bootstrap, because individual players in one NFL season share injuries, rules,
and environment.

1. **Partial pooling:** shrinking a one-season player rate toward the position rate will reduce
   rolling-origin MAE and CRPS versus the raw prior-season-rate baseline.
2. **Recency ensemble:** a causal two-season weighted rate will improve at least one proper score
   without making recent-season MAE materially worse (non-inferiority margin: 1% of baseline
   recent-season MAE).
3. **Residual uncertainty:** position-specific rolling residual scales will improve CRPS versus a
   single global residual scale while 50%, 80%, and 90% interval coverage remains within 10
   percentage points of nominal overall. Subgroups are diagnostic, not individually gated when
   fewer than 30 observations exist.
4. **Split conformal intervals:** prior-only absolute residual quantiles will improve coverage
   error versus Gaussian intervals. Width is reported; wider coverage is not called better unless
   WIS also improves.
5. **Market information:** archived ADP rank will be evaluated as a benchmark and, where at least
   one earlier market season exists, as an ensemble member. It must add out-of-sample forecast or
   downstream draft utility; agreement with the crowd is not itself success.
6. **Decision value:** only a forecast candidate that passes the forecast screen may enter a
   synthetic blind-draft shadow. It must preserve legal, duplicate-free rosters and improve or be
   non-inferior on paired starter strength and H2H evidence. No shadow can promote v6.

## Metrics

- Point: MAE, RMSE, Spearman rank correlation, and top-N hit rate.
- Distribution: Gaussian CRPS; WIS from p10/p25/p50/p75/p90; PIT KS error; 50%, 80%, and
  90% empirical coverage and mean interval width.
- Binary events: Brier score only for predeclared top-12-at-position and missed-season events.
- Cohorts: season, position, prior games (1-4, 5-11, 12+), returning player, and market coverage.
- Draft: legality, duplicates, starter strength versus league median, paired H2H, playoff proxy,
  classification, and forecast-authority label.

## Information contract

For target season `t`, a forecast may use only regular-season rows with `season < t`, plus a
preseason market snapshot timestamped before `t`. Realized target-season games, target-season
games played, target-season team totals, end-of-season player universe selection, or a future
market board are forbidden features. The evaluator records the earliest and latest training
season for every fold and raises on boundary violations.

The current weekly archive covers 2014-2024. It lacks historical depth-chart vintages, camp
injury snapshots, betting player props, vendor point projections, rookies with no NFL history,
and explicit ages/experience at each preseason date. Experiments therefore measure the marginal
value of causal production history and archived ADP, not a complete modern preseason model.

## Staged run

1. Unit-test leakage guards, shrinkage, residual fitting, exact replay, interval ordering, WIS,
   and honest handling of unseen players.
2. Pilot 2014-2019 to measure runtime and identify degenerate cohorts.
3. Run expanding-origin 2014-2024 across standard and PPR points, with half-PPR as primary.
4. Compare global Gaussian, position Gaussian, and split-conformal uncertainty.
5. Join the frozen 2018/2021/2024 ADP snapshots without using outcomes to resolve identities.
6. Pass only predeclared supported candidates into the existing blind-market shadow harness.
7. Record artifacts as compact JSON summaries with seed, folds, hashes, metrics, and limitations;
   do not commit raw caches or large draw-level files.

## Promotion interpretation

- **Promising:** better proper score with honest coverage and no recent-era regression; eligible
  for a future candidate member and untouched-season test.
- **Diagnostic only:** improvement is narrow, intervals are too wide, subgroup support is small,
  or 2024 reverses the aggregate result.
- **Rejected:** leakage, worse proper scores, unreliable coverage, deterministic draft defects,
  or improvement that depends on outcome-derived fields.

No result here supplies the missing C05 calibration or auxiliary evidence. Shipped v5 remains
production authority throughout this work.

## Initiation results

Run window: Saturday, 2026-08-29 00:30-00:48 CDT. Hardware: 11 logical CPUs and 18 GiB RAM.
Forecast runs used at most three workers; draft/roster-solver runs used one worker because the
interactive browser workload was already elevated. No dependency, network-controlled test, or
production data was added.

### Forecast screen

The primary half-PPR rolling-origin panel contains 3,280 returning player-seasons from report
seasons 2017-2024. Every fold's residual calibration includes forecasts from earlier seasons only.

| Forecast | MAE | Spearman | Gaussian CRPS | split-conformal WIS | 50% coverage | 80% coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| prior games-played rate × full schedule (current fixture proxy) | 55.738 | 0.639 | 40.094 | 39.481 | 0.499 | 0.808 |
| availability-preserving prior total | 43.434 | 0.684 | 32.828 | 32.426 | 0.530 | 0.816 |
| prior total shrunk to position median | 42.467 | 0.656 | **30.926** | **30.487** | 0.525 | 0.810 |
| 70/30 two-season total | **41.692** | **0.699** | 31.307 | 30.891 | 0.528 | 0.812 |

The season-clustered 95% intervals for candidate-minus-current MAE and CRPS are wholly below
zero for all three total-points candidates. The same ordering survives standard, half-PPR, and
PPR scoring. In 2024 alone, pooled total improves MAE from 58.314 to 43.527 and WIS from 41.199
to 31.322; the recency total reaches MAE 42.982 and WIS 31.278. This supports hypotheses 1-4 as
forecast diagnostics, with one qualification: position shrinkage best predicts a distribution,
while recency best predicts the point/rank. Neither result says it is the correct draft value.

Split-conformal intervals are preferred for the next experiment artifact: their half-PPR pooled
50%/80% coverage is 0.525/0.810, versus 0.609/0.834 for position-Gaussian intervals, and their
WIS is lower (30.487 versus 30.681). Gaussian CRPS is retained only as the Gaussian-summary
diagnostic; WIS is the proper primary score for the conformal quantiles.

Compact artifacts and SHA-256:

- `artifacts/probabilistic-preseason/c09-half-split_conformal.json` —
  `14ba48c203a6f4701d76d06efce85ab94170e1c0a328742cdcd0db22907feb2a`
- `artifacts/probabilistic-preseason/c09-std-split_conformal.json` —
  `922505107b2a7008f45176e99798aea78b62e0e558d3f831e07b037e6b98e1c6`
- `artifacts/probabilistic-preseason/c09-ppr-split_conformal.json` —
  `338e62d5e32ec7157de219c5bd1dcd9e3d554bff05e57841bc50dff4e92d4d06`

### Blind-market screen

Frozen Fantasy Football Calculator half-PPR ADP matched 186, 186, and 159 active identities in
2018, 2021, and 2024. A fixed percentile blend was evaluated without converting ADP into a fake
points distribution. For the two-season model, Spearman by model share was:

| Season | market only | 25% model | 50% model | 75% model | model only |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | 0.364 | 0.445 | 0.510 | **0.528** | 0.499 |
| 2021 | 0.468 | 0.532 | 0.575 | **0.587** | 0.570 |
| 2024 | 0.425 | 0.479 | 0.506 | **0.517** | 0.495 |

The direction is consistent, but the sample has only three inspected market seasons. Treat a
50-75% model rank blend as a preregistered future candidate, not a selected production weight.
ADP standard deviation and relative dispersion did **not** consistently predict held-out rank
error, so market disagreement is rejected as an uncertainty estimator in this data.

- rank artifact: `8f81a928a236f4d223cae419334ea9695e0b17ae54921d251bd9da5478c9b232`
- dispersion artifact: `5597582798863631ff20f45b5fc659448167973339ff2118435117edd6636d74`

### Draft decision screen

The forecast screen and draft screen answer different questions. Three 2024 half-PPR formats
(12-team 1QB, 12-team 2QB, 14-team 1QB), all slot bands, 20 repetitions per cell, and 16 season
evaluations per draft produced 180 paired drafts / 2,880 season evaluations per arm. All 720
drafts across the baseline and three shadows were legal and duplicate-free.

| Shadow minus v5 fixture input | paired H2H delta | 98.33% interval | starter-strength delta | playoff delta | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| position-pooled unconditional total | -0.0539 | [-0.0745, -0.0327] | -0.0481 | -0.1608 | reject |
| two-season unconditional total | -0.0470 | [-0.0685, -0.0272] | -0.0458 | -0.1483 | reject |
| conditional mean retained, conformal `boom`/`bust` only | -0.0261 | [-0.0444, -0.0074] | -0.0204 | -0.0837 | reject |

This falsifies direct integration despite the strong forecast scores. The evaluator defines
weekly points as production **conditional on playing** and separately samples availability. An
unconditional total already contains missed games; feeding it into that system discounts
availability twice. The uncertainty-only arm also hurts, showing that a central season-total
interval is not interchangeable with the policy's current “ceiling weeks” `boom`/`bust`
semantics.

The correct integration target already exists in `blitz_engine.intelligence.model`:
`availability_p`, `conditional_mean`, `conditional_stdev`, and p10/p50/p90 stay separate, with
unconditional expected points derived only at the decision boundary. Do not replace fixture
projection or `boom`/`bust` fields with these experiment totals.

Draft evidence hashes (timing excluded by the C09 evidence hash):

- baseline: `84d52e9892adabb2e89d5fc7d259fb53e489440c5fa9862c838e51786e6d272e`
- pooled: `c3e64bee64e6d6441f26dc2736500b43ce0e64d2fa8c8d9b8fbc79c3a4df6302`
- recency: `bf6dba0b629eca7d5deac0ac0045dc1f936c24ed4d9bc8641fdee3d6fc5d6816`
- uncertainty-only: `52b4f9b605d52db55fa0386b756e4b113ccc0317f03b0c8625e946c59eb3d152`

### Updated next bounded experiments

1. Score `conditional_mean` against points per active game and `availability_p` against starts
   separately; never tune their product as if it were either component.
2. Reuse the fitted `AvailabilityModel` and point-in-time injury/depth inputs. A prior-games ratio
   is only a baseline, not a new production availability model.
3. Calibrate conditional p10/p50/p90 with WIS/conformal residuals. Keep draft “ceiling weeks” as a
   different, explicitly named decision feature until an ablation proves a mapping.
4. Add the 50% and 75% model/market rank blends as fixed future shadows. ADP can inform likely
   availability-at-next-pick and rank consensus; it cannot supply a points variance.
5. Archive 2026 preseason vintages before games begin: model distribution, ESPN/FantasyPros/
   Sleeper ranks where lawfully available, ADP sample size/spread, injuries, depth chart, and
   as-of timestamp. Freeze 2026 as development and reserve a later untouched season for promotion.

Current verdict: the research and harness integration are promising, but v6 promotion is **not**
reopened. Direct forecast integration is rejected; component-wise probabilistic integration is
the next candidate phase.

## Component phase results (C10)

Run window: Saturday, 2026-08-29 02:34-02:53 CDT. The selected design reused the existing
`conditional_mean` / `availability_p` contract and derived expected value only as their product.
Two alternatives were rejected before implementation: unconditional totals had already produced
double-discounted draft values, while a new joint model was not identifiable from an archive that
lacks point-in-time injuries, depth charts, roster state, and rookie priors. The implementation is
an experiment seam only; shipped v5 and `AvailabilityModel.p_startable` are unchanged.

The expanding-origin component panel contains 3,280 returning player-seasons for 2017-2024.
`conditional_mean` is a full-schedule equivalent from stat-bearing games; `availability_p` is a
historical appearance-fraction proxy. A stat-bearing row is not a healthy/startable label, so the
availability result is a baseline diagnostic rather than a replacement for the fitted weekly model.

| Half-PPR component | Conditional MAE | Conditional rho | Availability Brier | Calibration gap | Expected MAE | Expected rho |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| prior season | 46.663 | 0.662 | 0.234 | 0.128 | 43.431 | 0.684 |
| position pooled | **44.316** | 0.647 | **0.215** | **0.038** | 43.126 | 0.660 |
| 70/30 two-season | 44.588 | **0.678** | 0.224 | 0.103 | **41.777** | **0.696** |

The component conclusions reproduce in standard, half-PPR, and PPR scoring: pooling has the best
conditional MAE and availability Brier/calibration, while recency has the best conditional rank
and derived expected-total MAE/rank. These improvements validate the decomposition as an
evaluation method, not the appearance proxy as a decision input.

The Node evaluation bridge now accepts a validated availability map scoped to a named v5 candidate
arm. Probabilities must be finite and in `[0, 1]`; a single map cannot be reused across target
seasons. Human-market arms ignore the map byte-for-byte and continue to see only provider ADP and
position. Boundary tests prove candidate causality, invalid-map rejection, exact seeded replay,
and market-arm isolation.

### Draft shadow rejection

A fresh same-seed control and three availability-only shadows used 2024, three league formats,
front/middle/back slots, 20 repetitions per cell, and 16 season evaluations per draft: 180 drafts
and 2,880 season evaluations per arm, 720 drafts / 11,520 evaluations total. All arms completed
180/180 legal and duplicate-free drafts. Multiplicity-adjusted intervals are 98.33%.

| Appearance map minus v5 | Starter-strength delta | Paired H2H delta | Playoff delta | Finish-rank delta | Decision |
| --- | ---: | ---: | ---: | ---: | ---: |
| prior season | -0.0694 `[-0.0883,-0.0508]` | -0.0802 `[-0.1009,-0.0586]` | -0.2271 `[-0.2858,-0.1672]` | +3.02 `[+2.25,+3.81]` | reject |
| position pooled | -0.0715 `[-0.0904,-0.0531]` | -0.0823 `[-0.1017,-0.0628]` | -0.2410 `[-0.2976,-0.1803]` | +2.87 `[+2.09,+3.68]` | reject |
| 70/30 two-season | -0.0672 `[-0.0864,-0.0474]` | -0.0761 `[-0.0972,-0.0553]` | -0.2236 `[-0.2803,-0.1665]` | +2.82 `[+2.03,+3.64]` | reject |

The v5 control was competitive (`mean H2H 0.5410`, starter strength `1.0378`, playoff delta
`+0.1072`). Every appearance shadow was classified UNDERPERFORMS. Historical games played blend
injury, role, roster status, zero-stat appearances, and regression to health; treating that fraction
as current weekly startability is a semantic mismatch even when its aggregate Brier score improves.

A combined pooled-conditional shadow was not run. Of 230 matching 2024 fixture players, 17 pooled
means fall outside the fixture's existing bust/boom ordering. Clamping them or widening those fields
would silently reinterpret the draft policy's ceiling-week semantics, an intervention the earlier
ablation already rejected.

Compact artifacts and SHA-256:

- `artifacts/probabilistic-preseason/c10-std-components.json` —
  `f3de5fe49719debe850a53fb40f9f91047a9d4d85564f97e020b91dba93d1a63`
- `artifacts/probabilistic-preseason/c10-half-components.json` —
  `3fcd810a25c5cf1d9dd2bd9f2be8ce12ca00e939503674fa240a3df7fdf2988b`
- `artifacts/probabilistic-preseason/c10-ppr-components.json` —
  `f9e8d63135ed573e5740ed2effef639eb9d1053d38808319435c5555b87240fb`
- `artifacts/probabilistic-preseason/c10-availability-draft-shadows.json` —
  `9316f1ee10a62e65f176ebe0f98952c723834a22eb1ed485c21758f5bb303cb3`

Current C10 verdict: **accept the component-wise evaluation and arm-isolated test seam; reject all
historical appearance maps as draft inputs.** The next evidence-bearing availability experiment
requires archived preseason roster/injury/depth snapshots and must use the fitted weekly
`AvailabilityModel`; no production behavior or v6 promotion status changes from this phase.
