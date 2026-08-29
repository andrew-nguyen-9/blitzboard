# Future BlitzBoard v6 Draft-Assistance Research and Product Plan

**Prepared:** 2026-08-29 04:09:19 CDT (UTC-05:00)

**Repository authority inspected:** `$HOME/Documents/GitHub/blitzboard` and all linked worktrees

**Continuation authority:** `/private/tmp/blitzboard-v6-c09-blind-market-benchmark`, branch `v6/c09-blind-market-benchmark`, HEAD `e5eb357361f33e26c03b1ea2ae1c9dece63a2b74`

**Product authority:** shipped v5 remains production authority; C05 promotion remains closed

**Scope:** research and planning only; no production behavior, deployment, database, or promotion change

**Deep-experiment addendum:** the subsequent preregistered campaign is recorded in
[draft-assistance deep experiments](../../modeling/draft-assistance-deep-experiments.md). It confirms
the executive ordering and sharpens the boundaries: draft-only false-quantile suppression is the
first repair, followed by reason fidelity, native semantics/reflow, and compact presentation;
compare remains presentation-only; `(4,8,12)` is an offline stress profile rather than a calibrated
population; missing market metadata invalidates favorable outcome interpretation; and the current
proxy cannot honestly evaluate offensive rookie/incomplete-history recommendations. Detailed
follow-on plans are in [expansion](2026-08-29-draft-assistance-expansion.md),
[draft uncertainty semantics](2026-08-29-draft-uncertainty-semantics.md),
[reason fidelity](2026-08-29-reason-fidelity-unit.md),
[compact recommendations](2026-08-29-compact-recommendations-unit.md),
[player compare](2026-08-29-player-compare-unit.md),
[native draft-board semantics](2026-08-29-draft-board-native-semantics.md),
[point-in-time acquisition](2026-08-29-point-in-time-data-acquisition.md),
[startability snapshot handoff](2026-08-29-startability-snapshot-handoff-experiment.md),
[market-opponent strict isolation](2026-08-29-market-opponent-isolation-unit.md),
[next-turn availability](2026-08-29-next-turn-availability-experiment.md),
[heterogeneous opponents](2026-08-29-heterogeneous-opponent-experiment.md),
[draft-clock experiments](2026-08-29-draft-clock-experiments.md), and
[usability study](2026-08-29-draft-assistance-usability-study.md).

## Executive decision

BlitzBoard should become a stronger **human decision-support board**, not an autodrafting agent. The smallest credible path is:

1. suppress the draft-only false P10/median/P90 projected-points strip without changing candidates,
   score, order, or pick actions;
2. repair the current VONA/run/market-gap reason semantics without changing ranking;
3. restore populated-board native semantics, narrow-screen reflow, recommendation-first source order,
   and consequential action sizing;
4. simplify the live recommendation surface into one primary candidate, three alternatives, one
   faithful reason each, one consequential tradeoff, and an explicit data-state signal;
5. add a presentation-only comparison mode using the recommendation and explanation payloads that already exist;
6. harden the existing human-ADP experiment bridge so market opponents receive a narrow lawful row,
   then prove pick parity with the current behaviorally isolated seam;
7. separately validate a next-turn survival forecast on lawful real labels, using that seeded picker
   and draft harness first for replay/sensitivity and later as a calibrated comparator;
8. only then add bounded, source-isolated heterogeneous opponent mixtures and candidate-specific what-if rollouts;
9. defer learned opponents, POMDP/MCTS, regret solvers, and risk-sensitive roster optimization until simpler methods fail preregistered tests.

This ordering follows both the repository evidence and the external evidence. Real fantasy drafters show fairly homogeneous strategies with some local response to preceding picks, so a small policy mixture is a defensible first opponent model, not a neural agent population. Lee and Liu's dataset covered 1,350 Sleeper leagues, 12,590 teams, and 188,426 human selections, but only the 2017 season on one platform, so it establishes plausible factors rather than current effect sizes ([Lee & Liu, 2022](https://doi.org/10.1017/S1930297500008901)). Decision-support studies also warn that explanations can increase acceptance of a recommendation whether it is right or wrong, and that additional decision-aid information can introduce new errors; therefore the default board should be sparse, alternatives should remain visible, and deeper evidence should be progressive disclosure ([Bansal et al., 2021](https://arxiv.org/abs/2006.14779); [Williams et al., 2007](https://doi.org/10.1016/j.ejor.2005.06.064)).

No historical result in this plan is confirmation evidence for 2026. Model promotion requires
lawful point-in-time snapshots and real draft histories from a frozen future window; because the
full 2026 preseason window has already elapsed, that may mean a limited late-2026 pilot followed by
2027 confirmation rather than retroactive 2026 reconstruction.

## 1. Repository-state audit

### 1.1 Checkouts and authority

| Checkout/worktree | Branch | Inspected HEAD | State | Planning implication |
|---|---|---:|---|---|
| `$HOME/Documents/GitHub/blitzboard` | `main` | `9192163b5be…` | 126 commits behind `origin/main`; modified `.serena/project.yml`; untracked `.worktrees/`, `AGENTS.md`, and `tmp/` | Historical root checkout; do not reset, clean, or use as implementation authority. |
| `/private/tmp/blitzboard-v6-c09-blind-market-benchmark` | `v6/c09-blind-market-benchmark` | `e5eb357361f…` | Authoritative dirty research worktree | Continue documentation here and preserve every local experiment change/artifact. |
| `/private/tmp/blitzboard-active-player-hotfix` | `fix/draft-require-current-team` | `a99fe12…` | Clean | Landed/isolated corrective work; not a v6 planning authority. |
| `/private/tmp/blitzboard-v6-c06-independent-land-gate` | `v6/c06-independent-land-gate` | `39563c3…` | Clean | Historical gate evidence. |
| `/private/tmp/blitzboard-v6-c06a-roster-legality` | `v6/c06a-roster-legality` | `ea706a3…` | Clean | Roster-legality correction evidence. |
| `/private/tmp/blitzboard-v6-land` | `v6/bench-portfolio-land` | `61fa20f…` | Clean | Historical land worktree, not current authority. |
| `$HOME/Documents/GitHub/blitzboard-c02-reproduction` | `v6/c02-reproduction` | `0993a9c…` | Clean | Calibration reproduction evidence. |
| Root `.worktrees/` C05 and C05A–C05E/review worktrees | various | inspected individually | Clean | C05 remains parked; do not reopen promotion indirectly. |

The ref audit inspected 21 local branch refs and 27 remote refs (including the symbolic
`origin/HEAD` ref): current fix branches, every retained local v6 checkpoint branch, remote-only v6
interface/reproduction branches, and remote v7 integration/manual-resilience/schema/expert-overlay/
runbook branches. `fix/mc-snapshot-publish` has a gone upstream; local `main` is the only tracked
branch with recorded divergence (126 behind). No branch was switched, fetched, reset, deleted, or
assigned product authority from its name.

`origin/main` was inspected at `e5eb357…`, including the active-player and bench-portfolio lands. The local `.orchestrator-v6/state.md` still describes an earlier C02 state and is stale. Git commits, checkpoint records, ignored artifacts, and the live dirty tree supersede it.

### 1.2 Preserved dirty research state

The authoritative worktree already contained the following before this plan:

- modified: `docs/modeling/draft-eval.md`, `engine/blitz_engine/backtest/draft_realism.py`, `engine/tests/test_draft_realism.py`, `frontend/lib/draftAI.ts`, `frontend/scripts/draft-eval.mjs`;
- untracked research: `docs/modeling/blind-market-benchmark.md`, `docs/modeling/probabilistic-preseason-experiments.md`, `docs/modeling/recent-era-game-theory-experiments.md`, `docs/superpowers/plans/2026-08-29-component-probabilistic-preseason.md`;
- untracked experiment code/tests: `engine/blitz_engine/backtest/blind_market.py`, `engine/blitz_engine/backtest/probabilistic_preseason.py`, their engine tests, and `frontend/lib/blindDraft.test.ts`;
- ignored receipts under `artifacts/blind-market/` and `artifacts/probabilistic-preseason/`, plus caches and build outputs.

The current ignored inventory contains 33 paths under `artifacts/blind-market/`, 18 under
`artifacts/probabilistic-preseason/`, and 97 top-level artifacts plus 11 ignored bytecode-cache files
under `artifacts/draft-assistance-deep/` (108 files total). These counts are an audit receipt, not a request
to clean them. The deep set contains 82 hashed JSON artifacts under three documented hash contracts.

At initial preparation, this plan added only this document and the local orchestration wishlist.
Later checkpointed experiment artifacts and planning documents are listed in the addendum above.
Nothing in the inherited dirty research state was reset or discarded.

### 1.3 Checkpoint conclusions that remain binding

- C04A verified that the live war room calls the shared scorer once and decorates its result with structured explanations; it deliberately did **not** add browser simulation.
- C05E kept C05 parked, preserved v5 behavior, admitted no auxiliary authority, and made promotion mechanically unreachable.
- C06 found incomplete K/DST rosters in the independent land gate.
- C06A corrected roster completion; 100/100 and 500/500 sampled drafts were legal and duplicate-free, subject to independent review.
- The current historical draft-evaluation target is imperfect-information locked-lineup `SeasonEvalResult.started_points`, with health/startability availability modeled separately from production. See [draft evaluation](../../modeling/draft-eval.md).

### 1.4 Historical experiment receipts

The ignored JSON receipts, not prose alone, were checked. They support these bounded conclusions:

- The blind-market campaign ran 864 legal, duplicate-free drafts across 2018, 2021, and 2024. Aggregate v5 performance underperformed the league-average gates, while 2024 alone was competitive. The aggregate also exposed severe 1QB quarterback overcapitalization. See [blind-market benchmark](../../modeling/blind-market-benchmark.md).
- The corrected 2024 recent-era campaign covered 1,800 drafts and 28,800 season trajectories. A bounded recent-run term and a two-QB cap in 1QB formats were promising; handcuff amplification was inert; heterogeneous `topK` opponents were narrowly non-inferior, not superior. See [recent-era experiments](../../modeling/recent-era-game-theory-experiments.md).
- Probabilistic preseason work found that total-point forecasts improved retrospective prediction, but direct unconditional total-point draft integration double-discounted availability and was rejected. The uncertainty-only boom/bust arm was rejected. A 50–75% model/market rank blend was retrospectively promising over three inspected seasons but remains unconfirmed. ADP dispersion was not a reliable forecast-error estimator. See [probabilistic preseason experiments](../../modeling/probabilistic-preseason-experiments.md).
- Appearance-map availability shadows all underperformed and were rejected. Season-total conformal intervals do not inherit the existing ceiling-week boom/bust meaning. See the [component plan](2026-08-29-component-probabilistic-preseason.md).

These are closed findings, not questions for a new experiment matrix.

### 1.5 Existing 2026 point-in-time receipt

The repository already contains the immutable
`docs/data/baselines/2026-08-25` intelligence receipt. Its manifest reverified successfully as
`intelligence-2026-08-25`, as of 2026-08-26T00:00:00Z. The source-evidence file records 2,930
nflverse weekly-roster rows and 469,064 depth-chart rows, while injuries, ESPN news, and official
inactives remain explicit gaps. The model-status receipt has zero forecast rows and no promotion.

This is useful evidence for snapshot hashing, roster/depth provenance, and degraded-source behavior.
It is not a market board, rank/ADP archive, draft-history corpus, or next-pick-survival label set;
detailed source rows are outside Git, and per-dataset license/retention still needs approval before
reuse. It therefore narrows the 2026 acquisition gap but does not close it.

## 2. Existing-system capability map

### 2.1 Live draft path

| Capability | Existing implementation | What is reusable | Current limitation |
|---|---|---|---|
| Draft entry and sync | `frontend/app/draft/page.tsx`; `frontend/components/draft/DraftWarRoom.tsx`; Sleeper and ESPN sync hooks; manual fallback | Current state model, pick math, manual draft, source degradation | ESPN is an unofficial/fragile integration; sync state is not a market-ranking license. |
| Candidate scoring | `frontend/lib/draftAI.ts` | `candidatePool`, `scoreBoard`, `scoreBoardWithExplanations`, starter/bench marginal value, roster constraints, scarcity, runs | Coarse deterministic next-turn replacement, not a survival probability; O(pool²) scoring is acceptable only on the bounded candidate pool. |
| Live explanation | `frontend/lib/v6DraftLiveScoring.ts`; `frontend/lib/v6DraftExplanation.ts` | Structured components, provenance, degraded inputs, immediate-lineup/bye/contingent-role/bench-shape evidence | `LiveRecommendations.tsx` renders many details simultaneously; no compact compare relationship. |
| Alternatives | `DraftWarRoom.tsx` takes the top four scorer outputs | The desired primary plus three alternatives already exist | Alternatives are cards, not an explicit comparative decision surface. |
| Roster constraints and health | `frontend/lib/draft.ts`; `frontend/components/draft/rosterHealth.ts`; `RosterHealthPanel.tsx`; `BenchPanel.tsx` | Starter fill, bench, needs, bye stacks, drop priority | Coverage and fragility are distributed across panels rather than candidate-specific tradeoffs. |
| Draft-room context | `detectRuns`, `DraftPickLog.tsx`, `AllTeamsBoard.tsx`, `DraftAnalysis.tsx` | Recent runs, opponent rosters, reaches/steals, team summaries | No per-opponent probabilistic need model; some post-draft labels such as grades are too strong for prospective decision support. |
| Manual rival simulation | `DraftWarRoom.tsx` `pickForTeam` loop | Existing snake-pick transitions and state updates | Every rival currently uses effectively the same BlitzBoard policy; the UI passes jitter but no `rng`, so `Math.random` makes exact simulated player identities nonreplayable. It is a convenience, not a calibrated forecast or what-if engine. |
| Market fields | `PlayerWithValue`, `player_value.adp`, `player_value.rank`; snapshot columns | Rank and ADP can support honest disagreement displays | The live query has no source/as-of contract; rank, ADP, projection, and recommendation semantics can be confused. |
| Draft uncertainty display | `LiveRecommendations.tsx`; `components/uncertainty/fromValue.ts`; `UncertaintyStrip` | Reuse the visual primitive only after a typed quantile snapshot exists; preserve the honest missing state now | Active VORP floor VOR/shaped value/ceiling VOR are passed as P10/median/P90 `pts`. Suppress this draft caller; shared player surfaces need a separate engine/target/unit audit. |
| Health/startability availability | `frontend/lib/availability.ts`; `frontend/lib/queries.ts:getAvailabilityMap`; `engine/blitz_engine/survival/availability.py` | The engine and database define a factorized `p_startable` contract; the frontend scorer accepts an optional published map and otherwise degrades to local player-row status/team metadata. | The live draft route does **not** call `getAvailabilityMap` or pass the map into `DraftWarRoom`, and `candidatePool` has no published-map parameter. Therefore the live board currently uses only the local proxy. The flat query result also drops season, week, and source. This is **not** “available at my next pick”; retain a distinct type, label, provenance path, and experiment authority. |
| Lab what-if | `frontend/components/lab/whatif.ts` and `WhatIfPanel.tsx` | Interaction/accessibility patterns only | It is explicitly a toy injury redistribution model and must not be reused as a draft rollout engine. |

### 2.2 Offline evaluation path

| Capability | Existing implementation | Reuse decision |
|---|---|---|
| Seeded draft scenarios and seat specs | `engine/blitz_engine/backtest/draft_realism.py` | Reuse. Extend experiment-only seat policy descriptors; do not introduce a new agent framework. |
| Market-only picker seam | Dirty `pickHumanAdp` addition in `frontend/lib/draftAI.ts` plus TypeScript bridge | Reuse after strict-boundary hardening. It has bounded `topK`, seeded draws, roster-capacity logic, and poison tests proving behavioral insensitivity to model fields. The current bridge still passes full `PlayerWithValue` objects, so structural non-receipt is not yet satisfied. |
| Season evaluation | `engine/blitz_engine/simulation/season_eval.py` | Reuse for offline recommendation outcomes and regret proxies. Preserve its documented limitations: proxy playoffs, contested waivers, no trades/FAAB. |
| Blind-market campaigns | `engine/blitz_engine/backtest/blind_market.py` and ignored receipts | Reuse campaign, hashing, degradation, and paired-bootstrap patterns. |
| Roster legality | `engine/blitz_engine/value/roster_solver.py` and C06A evidence | Mandatory invariant in every future campaign. |
| League matrix | `fixtures/league_matrix.json` | Reuse the 432-format matrix for configuration generation; select preregistered cells rather than running all cells by default. |
| Historical realized seasons | compact 2018, 2021, 2024 fixtures | Development evidence only; survivorship and rookie identity gaps remain material. |
| Immutable source receipt | `engine/blitz_engine/intelligence/snapshot.py`; `docs/data/baselines/2026-08-25` | Reuse content hashing, atomic snapshot, and explicit-gap patterns. The verified receipt has roster/depth source counts but no retained row payload, market board, draft history, forecast, or license receipt, so it is not survival evidence. |

### 2.3 Data-contract gaps

The live draft page currently loads player/value rows, bye weeks, and league configuration, but does not load the richer availability or trend maps. Despite comments in `availability.ts`, `queries.ts`, and `draftAI.ts` describing the published map as the scoring truth, repository-wide call-site inspection found no live caller of `getAvailabilityMap`; `DraftWarRoom` supplies neither `availability` nor `trends` from the page. `getAvailabilityMap` orders by season/week but then returns only `player_id -> p_startable`, dropping the date and source needed for a truthful freshness display. `candidatePool` also orders its positional reserve using only the local proxy. These are capability gaps, not evidence that the engine model is active in production.

Do not repair that mismatch opportunistically in a UI unit. C05 promotion remains closed, and direct unconditional integration already failed. First define a provenance-bearing read contract, establish whether candidate prefilter and final scoring should consume the same snapshot, and run the existing availability-only shadow/paired guards. Until then, UI copy may describe only observed injury/team metadata, not a published startability probability. Before displaying “fresh,” “stale,” or a named vendor, the data contract must include:

```text
source_id, source_kind, source_method, scoring_format,
league_size, roster_format, as_of_utc, retrieved_utc,
effective_season, license_receipt_id, raw_sha256,
normalization_version, degraded_reason
```

Missing provenance must render as “source unavailable” or “date unknown,” never as a fabricated vendor recommendation.

Repository-wide search also found no typed remaining-clock/clock-limit field in frontend, engine,
pipeline, database, or fixtures. The current “clock” region is draft-turn status, not evidence of
seconds remaining. Do not infer time pressure from sync receipt gaps or pick timestamps. A future
clock experiment requires source-defined remaining time plus autopick/timeout semantics and the
separate privacy/accessibility contract in the
[draft-clock experiment plan](2026-08-29-draft-clock-experiments.md).

The experiment artifact vocabulary also needs a versioned correction: the bridge emits
`market_adp`, but `analyze_recommendations.py` labels its coverage metrics `market_rank`, and parts
of `blind_market.py` use `market_ranks` for ADP-valued maps. Existing receipts remain immutable and
their compatibility meaning is “ADP.” The next artifact schema should use `market_adp_by_player`
and ADP-named metrics, recording a compatibility map rather than silently relabeling old JSON.

## 3. Research bibliography and evidence-quality matrix

### 3.1 Evidence grading

- **A — directly applicable:** empirical snake-draft behavior, fantasy draft decision support, or methods directly evaluable with the current draft harness.
- **B — credible adjacent:** peer-reviewed methods from games, survival analysis, forecasting, portfolios, or human–AI decision support that require adaptation and BlitzBoard-specific validation.
- **C — speculative:** technically credible methods whose data, objective, scale, or interaction assumptions do not match the current product. They define escalation options, not roadmap commitments.

The matrix contains 4 direct, 22 adjacent, and 6 speculative rows. Every direct/adjacent row records
data/sample scope, assumptions, code/data availability, threats, a measurable BlitzBoard adaptation,
and affected product layer; unavailable or inapplicable sample counts are stated rather than inferred.
A 2026-08-29 reachability probe found all 51 unique research links either reachable (40) or blocked
by a publisher/access response (11), with no failed or timed-out URL. Link status is only an audit aid,
not peer-review, content, licensing, or reproducibility evidence.

### 3.2 Directly applicable evidence

| Citation / venue / review status | Data, assumptions, code/data | Threats to validity | BlitzBoard implication and measurable experiment | Layer |
|---|---|---|---|---|
| Michael D. Lee & Siqi Liu, “Drafting Strategies in Fantasy Football,” *Judgment and Decision Making* 17(4), 691–719 (2022), peer-reviewed ([article](https://doi.org/10.1017/S1930297500008901); [code/data](https://github.com/susie647/fantasy-football-drafting-strategies)) | 1,350 2017 Sleeper leagues; 12,590 teams; 11,932 human teams; 188,426 human selections, 27% auto-picks. Assumes filtered Sleeper leagues represent human drafting. Code and analyzed data are public. | One platform and old season; platform UI and player market changed; observational effects are not causal; auto-pick contamination remains. | Use only the supported factors—narrow strategy families and bounded recent-pick response—to define a small mixture. Re-estimate 2026 coefficients from lawful point-in-time draft logs; compare homogeneous vs mixture calibration and outcomes. | Opponent model; draft dynamics; explanation. |
| Michael J. Fry, Andrew W. Lundberg & Jeffrey W. Ohlmann, “A Player Selection Heuristic for a Sports League Draft,” *Journal of Quantitative Analysis in Sports* 3(2), article 5 (2007), peer-reviewed ([DOI](https://doi.org/10.2202/1559-0410.1050); [institutional record](https://iro.uiowa.edu/esploro/outputs/journalArticle/A-Player-Selection-Heuristic-for-a/9984380640402771)) | Stochastic-DP formulation reduced to a deterministic DP; simulated 2005 fantasy drafts. The primary comparison uses five randomly generated 10-team, 16-round opponent-strategy instances; appendices add four homogeneous-strategy instances and further information scenarios, plus a small exact-versus-restricted example. Assumes estimated player value, positional need, and opponent selections can be represented compactly. No maintained code/data found. | Old scoring/player environment; tiny hand-structured instance set; perfect-information cases; simulated opponents; single-franchise objective. | Prefer a shallow candidate rollout over a new full DP. Test whether one-turn rollouts improve paired regret/starter strength over the base scorer within a latency budget. | Ranking; what-if. |
| Adrian Becker & Xu Andy Sun, “An Analytical Approach for Fantasy Football Draft and Lineup Management,” *Journal of Quantitative Analysis in Sports* 12(1), 17–30 (2016), peer-reviewed ([article/PDF](https://doi.org/10.1515/jqas-2013-0009)) | Trains player/team prediction on 2004–2006, simulates 10-owner 2007 and 2008 seasons, and uses historical Yahoo/NFL statistics, expert preseason ranks, and public-draft summaries. The paper reports 300 final-model 2007 trials plus 300 uniform-weekly comparator trials; the accessible 2008 results section does not restate its trial count. Mixed-integer draft/weekly-lineup model with a robust uncertainty set for opponent picks. Assumes the forecast, opponent uncertainty set, and season simulator adequately represent draft/lineup utility. No maintained code or redistributable dataset found. | Old 1QB-style roster/scoring, limited source provenance, simulated opponents, and a full-season automated-manager objective unlike human decision support; favorable numerical tests are not a modern holdout. | Retain season-win/H2H evaluation and bounded opponent uncertainty, but do not build the MIP. Compare the existing scorer with one-turn candidate rollouts on frozen rooms; advance only on out-of-time regret/H2H plus latency and legality. | Evaluation; opponent uncertainty; what-if. |
| Dimitri P. Bertsekas & David A. Castañón, “Rollout Algorithms for Stochastic Scheduling Problems,” *Journal of Heuristics* 5(1), 89–108 (1999), peer-reviewed ([DOI](https://doi.org/10.1023/A:1009634810396); [author PDF](https://faculty.engineering.asu.edu/bertsekas/wp-content/uploads/sites/129/2020/03/rollout_algorithms_for_stochastic_scheduling_problems.pdf)) | 30 generated problems per condition, each policy evaluated with 10,000 Monte Carlo runs; one- and selective two-step rollout over base heuristics. Assumes a valid simulator and feasible base policy. No task-specific code/data. | Scheduling rather than drafting; improvement guarantees depend on assumptions and evaluator fidelity. | Use the existing legal v5 scorer as base policy and existing seeded harness as simulator. First experiment: primary plus three candidate actions, rollout only to the user's next pick. | Ranking; next-turn availability; what-if. |

### 3.3 Credible adjacent evidence requiring adaptation

| Citation / venue / review status | Data, assumptions, code/data | Threats to validity | BlitzBoard implication and measurable experiment | Layer |
|---|---|---|---|---|
| Martin B. Haugh & Raghav Singal, “How to Play Fantasy Sports Strategically (and Win),” *Management Science* 67(1), 72–92 (2021), peer-reviewed ([DOI](https://doi.org/10.1287/mnsc.2019.3528); [author manuscript](https://spiral.imperial.ac.uk/server/api/core/bitstreams/a1aef748-a483-485e-b81c-59f06cdfc50c/content)) | Seventeen weeks of 2017 FanDuel NFL contests, with three contest structures per week; each model submitted 50 top-heavy, 25 quintuple-up, and 10 double-up entries weekly against fields of roughly 200,000, 10,000, and 30,000 opponents. Dirichlet-multinomial opponent ownership model and multi-entry portfolio optimization. Supplemental material is listed by the publisher. Assumes contest payout and lineup ownership can be modeled. | DFS is simultaneous, repeated-entry, salary-constrained, and materially unlike a season-long snake draft; one NFL season has high realized-P&L variance, which the authors acknowledge. | Correlation and opponent selection matter, but import only the experiment idea: compare independent player values with roster-level correlated-upside summaries after calibrated joint outcomes exist. | Upside/risk; portfolio view. |
| Colin F. Camerer, Teck-Hua Ho & Juin-Kuan Chong, “A Cognitive Hierarchy Model of Games,” *Quarterly Journal of Economics* 119(3), 861–898 (2004), peer-reviewed ([DOI](https://doi.org/10.1162/0033553041502225)) | Fits many experimental games, including 24 beauty-contest datasets; a mean of roughly 1.5 reasoning steps fit the pooled evidence. Assumes Poisson-distributed reasoning levels and lower-level best responses. No maintained software artifact. | Mostly laboratory one-shot games, not time-pressured drafts; “level” is not directly identifiable from pick history. | Treat sophistication as a small, observable policy type—not a psychological diagnosis. Compare 2–4 bounded type mixtures; do not expose “level-k” labels to users. | Opponent model only. |
| Leonidas Spiliopoulos, Andreas Ortmann & Le Zhang, “Complexity, Attention, and Choice in Games Under Time Constraints: A Process Analysis,” *Journal of Experimental Psychology: Learning, Memory, and Cognition* 44(10), 1609–1640 (2018), peer-reviewed ([DOI](https://doi.org/10.1037/xlm0000535)) | Between-subjects laboratory experiment with 148 UNSW participants: 50 unconstrained, 48 with a 20-second maximum, and 50 with a 45-second minimum. Each participant played 29 normal-form games; the main analysis used 28 3×3 games and Mouselab information-search traces. A hierarchical Bayesian latent-class model estimated decision-rule mixtures. Assumes the lookup trace reflects acquired information and the chosen games distinguish candidate heuristics. No code/data package was identified. | One-shot two-player payoff matrices, student-pool recruitment, 2014 sessions, and an artificial Mouselab interface differ sharply from a multiplayer sequential draft. The time treatment is between subjects, and heuristic labels depend on the supplied model library. | Treat “less opponent-focused under pressure” as a testable clock-state hypothesis, not a default opponent trait. Only with lawful logs containing pick-clock state, compare a fixed mixture to a preregistered time-conditioned mixture on held-out pick/survival log loss. In the UI study, report lens/detail use by time remaining and whether a shorter default preserves tradeoff accuracy; never infer user sophistication from fast choices. | Opponent dynamics; information hierarchy; UI study only until adapted. |
| Richard D. McKelvey & Thomas R. Palfrey, “Quantal Response Equilibria for Normal Form Games,” *Games and Economic Behavior* 10(1), 6–38 (1995), peer-reviewed ([DOI](https://doi.org/10.1006/game.1995.1023)) | Maximum-likelihood fits to multiple experimental game datasets; this review did not recover a single pooled participant/trial count. Probabilistic choice rises with relative expected utility. Assumes equilibrium-consistent beliefs and specified error distribution. No current code/data package. | Drafts are sequential, large-action, non-zero-sum, and partially observed; utility is not known. | Borrow the bounded-rational-choice shape only if fixed `topK` mixtures miscalibrate. Fit a temperature to lawful pick logs and compare log loss/Brier score against the simpler picker. | Opponent model; next-turn availability. |
| R. L. Plackett, “The Analysis of Permutations,” *JRSS Series C (Applied Statistics)* 24(2), 193–202 (1975), peer-reviewed ([DOI](https://doi.org/10.2307/2346567)) | Develops a distribution over permutations; examples use election voting and bean-store data, but this review did not recover their row/voter counts. Assumes latent item worths and sequential selection without replacement. No code/data. | Static ranked-choice worths omit roster need, draft round, and interaction; independence assumptions may fail badly. | Candidate baseline for source-specific pick likelihood, not an automatic product model. Compare held-out pick log loss to ADP `topK`; add covariates only when they improve time-split calibration. | Opponent model; availability-at-next-pick. |
| Stefano V. Albrecht & Peter Stone, “Autonomous Agents Modelling Other Agents,” *Artificial Intelligence* 258, 66–95 (2018), peer-reviewed survey ([DOI](https://doi.org/10.1016/j.artint.2018.01.002); [manuscript](https://www.cs.utexas.edu/~pstone/Papers/bib2html-links/AIJ18-Albrecht.pdf)) | Comprehensive method survey rather than a new empirical sample; covers policy reconstruction, type-based reasoning, classification, plan recognition, and recursive reasoning. Assumes the surveyed taxonomy and stated observability/behavior assumptions are useful for comparing domains. No paper-specific replication dataset or code package applies to the survey. | Survey breadth does not validate any method for fantasy drafts; candidate-model posterior mass can be mistaken for model adequacy. | Maintain posterior weights over a preregistered, small policy set and report an “unmodeled/low-fit” state. Never treat a high posterior within a bad library as certainty. | Opponent model; uncertainty. |
| D. R. Cox, “Regression Models and Life-Tables,” *JRSS Series B* 34(2), 187–202 (1972), peer-reviewed ([DOI](https://doi.org/10.1111/j.2517-6161.1972.tb00899.x)) | Semiparametric hazard regression for censored event times; methodological paper with illustrative medical/reliability applications rather than one empirical validation sample. Assumes proportional covariate effects. No software artifact in the original paper. | Player selection is a discrete-pick process; proportional hazards may fail across rounds and roster formats, and the method adds no value before lawful draft labels exist. | Defer continuous-time Cox. If a direct next-turn model is inadequate and selection-time scenarios are needed, test a simpler discrete-pick hazard with time-varying round/roster covariates by pick horizon and format; do not conflate this hazard with health availability. | Availability-at-next-pick only. |
| Tilmann Gneiting, Fadoua Balabdaoui & Adrian E. Raftery, “Probabilistic Forecasts, Calibration and Sharpness,” *JRSS Series B* 69, 243–268 (2007), peer-reviewed ([author bibliography/PDF](https://sites.stat.washington.edu/tilmann/publications.html)) | Methodology and weather-forecast examples rather than one validation sample; forecasts should maximize sharpness subject to calibration. Assumes a well-defined forecast target, comparable realized outcomes, and an evaluation sample appropriate to that target. No single packaged replication repository. | Weather examples differ from draft selection and market drift. | A narrow survival forecast is useful only if calibrated. Report reliability, Brier/log score, and interval width; never reward narrowness without coverage. | Uncertainty; next-turn availability. |
| Tilmann Gneiting & Adrian E. Raftery, “Strictly Proper Scoring Rules, Prediction, and Estimation,” *Journal of the American Statistical Association* 102(477), 359–378 (2007), peer-reviewed review article ([DOI](https://doi.org/10.1198/016214506000001437); [author PDF](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf)) | General scoring-rule theory plus a five-member ensemble case study with 16,015 48-hour weather records. Assumes the scored forecast and realized event share a valid target/sample; no BlitzBoard code/data package. | Weather dependence and a methodological case study do not solve fantasy label selection, censoring, or market drift. An improper or post-selected metric can still mislead. | Predeclare Brier and clipped log loss for binary next-pick survival; use CRPS/WIS only for genuine distribution/quantile targets. Score out-of-time rooms and report calibration beside sharpness. | Forecast evaluation; uncertainty. |
| Christoph Bergmeir, Rob J. Hyndman & Bonsoo Koo, “A Note on the Validity of Cross-Validation for Evaluating Autoregressive Time Series Prediction,” *Computational Statistics & Data Analysis* 120, 70–83 (2018), peer-reviewed ([DOI/author page](https://robjhyndman.com/publications/cv-time-series/)) | Theoretical results, a simulation study, and one real-world time-series example; this review did not recover one aggregate simulation/observation count. Assumes the evaluated autoregressive models have uncorrelated errors for the ordinary K-fold result; no fantasy sample or packaged BlitzBoard data/code. | Draft rooms are clustered sequential choice processes with drift and shared snapshots; the uncorrelated-error condition is unlikely by default. | Split by room and time/provider. Never randomize picks from one room across folds; use ordinary K-fold only if its residual assumptions are demonstrated, not as a convenience. | Validation design only. |
| Johannes Bracher, Evan L. Ray, Tilmann Gneiting & Nicholas G. Reich, “Evaluating Epidemic Forecasts in an Interval Format,” *PLOS Computational Biology* 17(2), e1008618 (2021), peer-reviewed ([article](https://doi.org/10.1371/journal.pcbi.1008618)) | Applies proper interval scores to 1–4-week FluSight forecasts from 26 models and defines weighted interval score for quantile submissions. Assumes the submitted quantiles describe the declared forecast target and are scored against comparable observations. Open article/supplement. | Count forecasts and many quantiles differ from binary player survival. | Use Brier/log loss for binary next-turn survival; use WIS only for roster-outcome or pick-number quantiles. Separate calibration from sharpness in reports. | Uncertainty/evaluation. |
| Harry Markowitz, “Portfolio Selection,” *Journal of Finance* 7(1), 77–91 (1952), peer-reviewed ([DOI](https://doi.org/10.1111/j.1540-6261.1952.tb01525.x)) | Foundational mean–variance framework with theoretical examples, not an empirical participant/market sample; no modern code/data. Assumes means/covariances summarize relevant tradeoffs. | Fantasy player outcomes are skewed, role-contingent, censored by lineups, and nonstationary; covariance estimates will be sparse. | Use portfolio language only for transparent roster-level diversification summaries. Do not optimize mean–variance until joint outcome calibration is demonstrated. | Roster comparison; upside/risk. |
| R. Tyrrell Rockafellar & Stanislav Uryasev, “Optimization of Conditional Value-at-Risk,” *Journal of Risk* 2(3), 21–41 (2000), peer-reviewed ([author publication page](https://uryasev.github.io/publications/)) | Convex formulation and illustrative portfolio examples, not one empirical validation sample; assumes a meaningful loss distribution and tail level. Author PDF is available; no BlitzBoard data. | A miscalibrated fantasy tail model produces precise-looking nonsense; user risk preference may not map to CVaR. | Defer optimization. If future weekly joint simulations calibrate, show downside outcome quantiles first; test whether CVaR adds stable decisions beyond them. | Risk-sensitive ranking, later only. |
| James W. Boudreau & Nicholas Shunda, “Sequential Auctions with Budget Constraints: Evidence from Fantasy Basketball Auction Drafts,” *Journal of Behavioral and Experimental Economics* 62, 8–22 (2016), peer-reviewed ([DOI](https://doi.org/10.1016/j.socec.2016.03.002)) | Natural field data from 49 ESPN fantasy-basketball auction leagues and 6,370 player auctions; assumes suggested valuations are a relevant anchor and tracks budget/capacity-constrained bids. No public code/data repository was found. | Auction nomination, budget depletion, and bidding are different mechanisms from a snake draft; basketball categories and ESPN's interface further limit transfer. | Treat early overbid/late underbid patterns as evidence that room state and platform anchors can influence behavior, not as snake-draft coefficients. If BlitzBoard later supports auctions, run a separate budget-aware model; do not inject auction effects into current survival estimates. | Adjacent opponent behavior; defer for snake ranking. |
| Zana Buçinca, Maja B. Malaya & Krzysztof Z. Gajos, “To Trust or to Think,” *Proceedings of the ACM on Human-Computer Interaction* 5(CSCW1), 1–21 (2021), peer-reviewed ([DOI](https://doi.org/10.1145/3449287); [preprint](https://arxiv.org/abs/2102.09692)) | Online experiment N=199; three cognitive-forcing designs, two explainable-AI conditions, and no-AI baseline. Assumes the task's deliberately wrong suggestions and intervention behavior operationalize overreliance and analytic engagement. No study code/data package was identified from the paper or preprint record. | Generic decision tasks; forcing functions were less liked and effects varied with need for cognition; draft-clock costs may dominate. | Keep alternatives and tradeoffs visible; do not force a lengthy pre-answer step. Test a lightweight “compare two” action against current cards on decision time, recall, and overreliance. | UI; explanation. |
| Gagan Bansal, Tongshuang Wu, Joyce Zhou, Raymond Fok, Besmira Nushi, Ece Kamar, Marco Tulio Ribeiro & Daniel S. Weld, “Does the Whole Exceed its Parts? The Effect of AI Explanations on Complementary Team Performance,” CHI 2021, peer-reviewed ([DOI](https://doi.org/10.1145/3411764.3445717); [preprint](https://arxiv.org/abs/2006.14779); [code/data](https://github.com/uw-hai/Complementary-Performance)) | Mixed-method studies with 1,626 users on beer-review sentiment, book-review sentiment, and LSAT tasks; AI accuracy was selected to be comparable to human accuracy. Assumes these tasks and matched human/AI accuracy can reveal complementary performance and reliance. Explanations did not improve complementary team performance and increased acceptance regardless of correctness. Study examples and collected data are public. | Classification/reasoning tasks, not sequential drafts; sample selection deliberately matched AI/human accuracy; crowd-worker incentives differ from a live draft. | Explanations must be fidelity-tested and paired with alternatives/data state. Measure appropriate rejection of deliberately weak recommendations, not just satisfaction. | UI; explanation fidelity. |
| Yunfeng Zhang, Q. Vera Liao & Rachel K. E. Bellamy, “Effect of Confidence and Explanation on Accuracy and Trust Calibration in AI-Assisted Decision Making,” FAccT 2020, 295–305, peer-reviewed ([DOI](https://doi.org/10.1145/3351095.3372852); [author PDF](https://qveraliao.com/fat2020.pdf); [preprint](https://arxiv.org/abs/2001.02114)) | Experiment 1 recruited 72 MTurk participants into eight conditions for 40 income-prediction trials after training, using the 48,842-row UCI Adult dataset and deliberately stratified model-confidence bins; experiment 2 tested a local explanation with only nine participants. Assumes calibrated model confidence and the income task can operationalize user trust/reliance calibration. The paper reports no code/data package beyond the public base dataset. Confidence was expressed as an out-of-10 frequency and model probabilities were checked for calibration. | One binary census task, crowd workers, stratified rather than naturally prevalent confidence cases, and a severely underpowered explanation experiment. Trust calibration improved with confidence display but joint accuracy did not, so neither effect transfers directly to draft choices. | Show a next-turn percentage only after target-specific calibration; name horizon/model date and offer a frequency form. Compare percentage+frequency against the honest qualitative fallback on probability comprehension, appropriate reliance, and decision quality—never treat trust or acceptance as the success metric. | Calibrated uncertainty; UI/explanation. |
| Forough Poursabzi-Sangdeh, Daniel G. Goldstein, Jake M. Hofman, Jennifer Wortman Vaughan & Hanna Wallach, “Manipulating and Measuring Model Interpretability,” CHI 2021, 1–52, peer-reviewed ([DOI](https://doi.org/10.1145/3411764.3445315); [code/data](https://github.com/Foroughp/Manipulating-and-Measuring-Model-Interpretability)) | Four preregistered experiments, 3,800 total participants; reproducible R analyses and data. Assumes simplified model transparency manipulations can reveal decision effects. | Synthetic/model-estimation tasks rather than draft choices; interpretability is not one scalar property. | Evaluate the actual behavior of summary versus expanded evidence: decision time, error, mental demand, and tradeoff recall. Do not assume more detail is more understandable. | UI; explanation. |
| Michael L. Williams, Alan R. Dennis, Antonie Stam & Jay E. Aronson, “The Impact of DSS Use and Information Load on Errors and Decision Quality,” *European Journal of Operational Research* 176(1), 468–481 (2007), peer-reviewed ([DOI](https://doi.org/10.1016/j.ejor.2005.06.064)) | Laboratory study of Expert Choice/AHP under low and high information load. Assumes its AHP task and load manipulation capture consequential DSS decision quality. The abstract does not publish N; no code/data identified. | Different task and older interface; one DSS implementation. | Prune default metrics. A new metric earns permanent space only if it changes a decision, reduces an error, or improves calibrated understanding in a preregistered test. | UI/information hierarchy. |
| Tobias Rieger & Dietrich Manzey, “Human Performance Consequences of Automated Decision Aids: The Impact of Time Pressure,” *Human Factors* 64(4), 617–634 (2022), peer-reviewed ([DOI](https://doi.org/10.1177/0018720820965019); [accepted manuscript](https://d-nb.info/124209069X/34)) | Two laboratory experiments, each with a fresh 60-person sample (120 analyzed participants total), three between-subjects aid conditions (manual, 95%-reliable, 75%-reliable), and 4.5- versus 9-second within-subject deadlines over six 40-trial blocks using a 320-image luggage-screening set. Experiment 1 showed aid advice before inspection; experiment 2 showed it after an initial participant decision. Assumes binary visual detection and known aid reliability; no code/data package was identified. | Binary detection with trained fixed reliability is unlike a multi-option draft; the time limits are seconds rather than a fantasy pick clock; participant strategy and base rates may not transfer. Giving a second response may itself reduce pressure, and the authors report mixed reliance effects and joint performance generally below the aid alone. | Do not infer that more prominent advice is better under a clock. After A/B/C hierarchy testing, run a separate order pilot comparing immediate-primary display with a lightweight user-first shortlist/objective step before reveal; measure time, tradeoff accuracy, weak-candidate rejection, anchoring, and abandonment. Never force a pre-pick commitment or treat reliance as success. | UI/order and human–AI collaboration only. |
| Sandra G. Hart & Lowell E. Staveland, “Development of NASA-TLX,” in *Human Mental Workload*, 139–183 (1988), reviewed book chapter ([NASA record](https://ntrs.nasa.gov/api/citations/20020039536/downloads/20020039536.pdf)) | Multi-dimensional subjective workload instrument developed from empirical/theoretical workload research; NASA hosts the record. Assumes retrospective ratings on its component dimensions validly summarize perceived workload for the task. The chapter is not one validation experiment with a single participant N, and no paper-specific code/data package was identified. | Retrospective self-report, weighting burden, and non-draft context; small local studies cannot support broad causal claims. | Use raw TLX or a preregistered short mental/temporal-demand subset in a sufficiently powered study; for a small pilot, label results usability-only. | UI evaluation only. |
| W3C, *Web Content Accessibility Guidelines (WCAG) 2.2*, W3C Recommendation; WAI Authoring Practices Guide, informative guidance ([WCAG 2.2](https://www.w3.org/TR/WCAG22/); [APG names/timer](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/); [buttons](https://www.w3.org/WAI/ARIA/apg/patterns/button/); [tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/); [tables](https://www.w3.org/WAI/tutorials/tables/two-headers/); [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow); [target minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum); [timing adjustable](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable); [status technique](https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA22)) | Normative success criteria plus informative implementation patterns; no participant sample or code dataset. Assumes supported semantic HTML/ARIA and appropriate author implementation. | Conformance guidance does not establish usability in this live draft flow or uniform assistive-technology support. Automated checks can miss announcement order, verbosity, focus, timer authority, and comprehension failures. | Use native labels/buttons/table headers/pressed state; do not fake a partial tab widget; isolate table scrolling if needed. Test keyboard, screen reader, axe, 375 px/200% smoke states, the 320-CSS-pixel Reflow boundary, accurate 24×24 minimum versus 44×44 enhanced target claims, and the exact host/BlitzBoard/study timing authority before invoking any real-time exception. | UI semantics/accessibility only; no ranking effect. |

### 3.4 Speculative methods—research backlog, not build commitments

| Citation / venue / review status | Data and assumptions | Why it is deferred | Promotion experiment if the prerequisite appears | Layer |
|---|---|---|---|---|
| David Silver & Joel Veness, “Monte-Carlo Planning in Large POMDPs,” NeurIPS 2010, peer-reviewed ([paper](https://papers.nips.cc/paper_files/paper/2010/hash/edfbe1afcf9246bb0d40eb4d8027d90f-Abstract.html)) | Rocksample plus 10×10 Battleship (~10^18 states) and partially observable Pac-Man (~10^56 states); assumes a black-box generative model. No maintained replication repository was identified in this review. | BlitzBoard does not yet have a validated opponent transition model or browser latency budget. Full POMCP would amplify simulator error. | Only after one-turn rollouts are calibrated and demonstrably myopic: compare selective two-turn search on a frozen offline campaign. | What-if/ranking. |
| Martin Zinkevich, Michael Johanson, Michael Bowling & Carmelo Piccione, “Regret Minimization in Games with Incomplete Information,” *Advances in Neural Information Processing Systems* 20 (2007), peer-reviewed ([paper](https://papers.nips.cc/paper_files/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html)) | Counterfactual regret minimization demonstrated in large two-player zero-sum poker abstractions; no maintained original replication repository was identified. | A fantasy league draft is multiplayer, non-zero-sum, roster-constrained, and followed by stochastic season play. “Regret” is useful as an evaluation statistic, not yet as a solver. | Revisit only with a validated utility and opponent model; compare against rollout with identical compute. | Long-term ranking. |
| Neil C. Rabinowitz, Frank Perbet, H. Francis Song, Chiyuan Zhang, S. M. Ali Eslami & Matthew Botvinick, “Machine Theory of Mind,” *Proceedings of Machine Learning Research* 80, 4218–4227 (ICML 2018), peer-reviewed ([PMLR paper](https://proceedings.mlr.press/v80/rabinowitz18a.html)) | Neural meta-learning over simulated agent trajectories; code availability is linked by the paper ecosystem. Assumes many training agents and trajectories. | BlitzBoard lacks lawful, representative labeled histories for individual drafter behavior; learned agents would be opaque and easy to leak hidden fields into. | Require multi-season, point-in-time draft logs, strict time split, source-isolation audit, and clear held-out calibration gain over the small mixture. | Learned opponent model. |
| Jacob Coreno & Ivan Balbuzanov, “Axiomatic Characterizations of Draft Rules,” *Journal of Economic Theory* 234, 106169 (2026), peer-reviewed ([DOI](https://doi.org/10.1016/j.jet.2026.106169)) | Theoretical matching/assignment result; no empirical data or code. Assumes ordinal bundle preferences and studies priority respect, EF1, non-waste, resource monotonicity, and incentive properties of round-robin drafts. | It evaluates allocation mechanisms, not which player a fantasy user should pick; BlitzBoard cannot change the host league's mechanism. | Use as a boundary result: preserve the actual snake priority/order and do not claim strategy-proofness or global fairness from a recommendation tool. No product experiment is warranted unless BlitzBoard designs a league mechanism. | Matching-market boundary; no ranking effect. |
| Level-k/recursive reasoning beyond a small type mixture | Behavioral-game-theory literature above | The user's task is choosing among players, not finding an equilibrium; recursion is costly and unidentifiable from short partial histories. | Demonstrate consistent held-out gain from one extra recursive level without stability loss. | Opponent model. |
| Full mean–variance/CVaR roster optimization | Markowitz and Rockafellar–Uryasev above | Joint outcome distributions and preference mapping are not calibrated. | First validate weekly joint simulations and whether users understand the risk control. | Risk-sensitive ranking. |

### 3.5 Topic-to-evidence coverage audit

| Requested topic | Best current evidence | Grade / decision |
|---|---|---|
| heterogeneous sequential drafts and fantasy strategy | Lee & Liu; Fry et al.; Becker & Sun | A/B; small bounded policies and rollout, no learned population |
| bounded rationality, level-k, cognitive hierarchy, time pressure, quantal response | Camerer et al.; Spiliopoulos et al.; McKelvey & Palfrey | B; adapt only as rank-only types/random utility or a measured clock-conditioned mixture after real behavior data |
| Plackett–Luce / ranked choice | Plackett | B; smallest likelihood baseline against `topK` |
| partial-history opponent modeling and Bayesian type updates | Albrecht & Stone survey plus the fixed-profile likelihood contract | B; few fixed types and explicit poor-fit state, no psychological labels |
| POMDP, MCTS, rollout, approximate DP | Fry et al.; Bertsekas & Castañón; Silver & Veness | A/B/C; one-turn rollout first, deeper planning deferred |
| regret / opportunity cost | current top-four regret definition; Zinkevich et al. | evaluation now, solver C/deferred |
| next-turn survival / hazard | Cox as a defer boundary; Gneiting/Raftery forecast evaluation | B; empirical table then direct binary next-turn logistic if needed; per-pick discrete hazard only for a validated selection-time/scenario question; real labels required |
| portfolio, diversification, correlated upside, contingent roles | Haugh & Singal; Markowitz; current contingency payload | B; presentation/roster diagnostics first, optimization deferred |
| risk-sensitive optimization and calibrated uncertainty | Gneiting et al.; Gneiting & Raftery; Bracher et al.; Zhang et al.; Rockafellar & Uryasev | B/C; proper scores now, target/frequency comprehension before UI trust claims, CVaR only after joint calibration |
| information load, time pressure, explanations, human–AI collaboration | Spiliopoulos et al.; Buçinca et al.; Bansal et al.; Zhang et al.; Poursabzi-Sangdeh et al.; Williams et al.; Rieger & Manzey; NASA-TLX; WCAG 2.2/WAI APG | A standard for semantics + B behavioral evidence; progressive disclosure, native semantics, and separate consented hierarchy and advice-order studies |
| fantasy auction/market behavior and matching boundaries | Boudreau & Shunda; Coreno & Balbuzanov | adjacent/boundary; do not import auction coefficients or fairness claims into snake ranking |
| probabilistic preseason validation | Gneiting/Raftery; Bergmeir et al.; local probabilistic-preseason experiments | B + direct local negative evidence; temporal room split and no quantile-semantic substitution |

The matrix has no missing requested method family. “Covered” means a cited boundary and measurable
decision, not a commitment to build the method.

### 3.6 Negative evidence and uncertainty register

| Claim not permitted | Evidence/disposition |
|---|---|
| “Higher model complexity is more realistic.” | Unsupported. The current small policy seam already creates bounded variation; complexity must win held-out calibration or paired draft outcomes. |
| “ADP/rank disagreement is uncertainty.” | Rejected by local experiments; disagreement between BlitzBoard rank and a stored market ADP/rank remains an observable ordinal comparison only. |
| “Season-total p90 is the player's weekly boom ceiling.” | Semantically false without a validated transformation; keep season-total and ceiling-week features separate. |
| “Health availability and next-pick availability are the same.” | False. One is startability/absence risk; the other is a competing-selection event. Keep separate names, types, displays, tests, and storage. |
| “The historical blend is ready.” | False. The 50–75% rank blend is retrospective, three-season development evidence only. |
| “Opponent posterior confidence proves the opponent model is right.” | False. It only selects among the supplied types; include poor-fit/unknown state and calibration tests. |
| “Showing BlitzBoard's answer first must improve decisions under a clock.” | Unproven. [Rieger and Manzey](https://doi.org/10.1177/0018720820965019) found advice-order effects in two binary luggage-screening experiments, but the direction depended on the interaction design and joint performance still underperformed the aid alone. Keep the usable default hierarchy, then test a separate non-forcing user-first shortlist/objective order; do not use agreement or reliance as success. |
| “A vendor recommends this player.” | Prohibited unless a lawful, timestamped vendor recommendation product directly supports that exact statement. A rank list, ADP, projection, and recommendation are distinct. |

## 4. Product gap analysis

### 4.1 Highest-value gaps

1. **Comparison is implicit.** The scorer already produces four candidates and structured evidence, but the UI makes the user mentally join separate cards.
2. **Next-turn scarcity is not probabilistic.** `expectedReplacementAtNextTurn` is a coarse projection estimate. It cannot support “63% likely to survive” or any calibrated confidence claim.
3. **Freshness/provenance is incomplete.** The product cannot safely name a market source or show a freshness badge from the current live query contract.
4. **Draft-room dynamics are descriptive, not predictive.** Recent runs and opponent rosters exist, but there is no bounded per-seat policy forecast.
5. **What-if exists only as a lab injury toy.** Draft candidate rollouts must use the draft harness and roster evaluator, not `applyInjury`.
6. **Default information density is too high.** The live recommendation card exposes all explanation lines and uncertainty details even under clock pressure.
7. **User objectives are implicit score changes.** Conservative/upside, balance/value, and market/contrarian choices need transparent, reversible controls and an explanation of what changed.
8. **Visible reason tags are not all fidelity-clean.** The `VONA` tag is triggered by current-lineup
   equity rather than value over next-turn replacement; run copy is prescriptive without a calibrated
   continuation model; upside says median while testing the mean; ADP-gap copy has no source/as-of
   provenance; and `eq` is explained only by hover title. Compacting these tags unchanged would make
   small semantic/accessibility defects more prominent.
9. **Native control semantics are incomplete.** Search has no programmatic label; view/position
   filters lack selected-state attributes; repeated draft buttons do not name their player; player
   names are not table row headers. These are one-file native HTML fixes, not reasons for a UI kit.
10. **Autodraft is too prominent for the product principle.** `Auto-draft all` sits beside the live
    clock controls. Retain it for manual/test workflows if needed, but demote it from the default
    decision path; do not use it as the roadmap's success case.
11. **Market degradation is room-wide, not just a blank cell.** Removing opponent ADP changes
    intervening picks and the candidate pool; under 30% behaviorally isolated synthetic dropout, primary match falls to
    15.35% overall and remains poor in every QB/slot/stage slice. The UI needs per-candidate unknowns
    plus one group coverage signal, while evaluator reports must block favorable outcome readings
    from weakened fields.
12. **The available-player rank fallback manufactures meaning.** The `#` cell renders
    `PlayerValue.rank ?? i + 1`; after filtering/search, `i + 1` is view order, not global BlitzBoard
    rank. Label the column and render missing rank as unavailable without changing row order.
13. **The frozen usability stress catalog is intentionally unrepresentative.** N0 resolves all 54
    states but finds 53 primary changes, mean top-four Jaccard 0.129, no DST candidate, and only one
    no-ADP state. It is challenge material, not a standalone study sample; separately freeze
    representative controls and degraded-data states.
14. **Mobile source order hides the decision aid below the board.** `DraftWarRoom` renders the main
    column—including up to 60 available-player rows—before the recommendation sidebar. On a narrow
    screen, place one recommendation instance before the long table while preserving the desktop
    right rail and the single scorer call; do not duplicate responsive markup.
15. **Structured component numbers do not share one user-facing unit.** The field named
    `immediate_lineup` is projected lineup points over estimated next-turn replacement, while bye,
    breakout, and redundancy values are weighted score contributions. Repair the expanded immediate
    label in E0 and keep E2 from presenting every component as generic projected points.
16. **The populated board fails narrow-screen reflow before any v6 expansion.** A disposable,
    credential-free 96-player local route measured a 506 px document at both 320 and 375 CSS px,
    producing 186 and 131 px of page-level overflow. The table itself is about 484 px wide; contain
    necessary two-dimensional table scrolling inside a named region and allow every surrounding
    card/control to reflow. The no-key empty shell did not reveal this defect.
17. **The populated decision path has verified accessibility blockers.** At 375 px the recommendation
    begins about 3,409 px down the page; 155 tabbables, including 60 player links and 60 assign
    actions, precede its first control. Axe found four serious unsupported `aria-label` uses on
    status dots, plus an empty table header and heading-order defect. The recommendation action was
    about 56×18 CSS px, below the product's 44×44 consequential-action goal. These are automated
    synthetic-fixture findings, not screen-reader or conformance results, but they make native
    source-order/reflow/semantics repair a prerequisite to E1 compaction rather than optional polish.
18. **Expanded explanations expose internal reason codes.** The populated recommendation prints
    identifiers such as `accepted_c02_c03_have_no_candidate_transaction_evidence` and
    `missing_league_key`. Preserve them in the auditable payload, but E0 must map known codes to
    plain limitations and unknown codes to one honest generic fallback. Compaction cannot make raw
    implementation identifiers the user's evidence summary.
19. **The draft recommendation manufactures a quantile range from incompatible value fields.** The
    live draft uses the VORP engine, then maps `bust/value/boom` to P10/P50/P90 and labels the range
    points. On this path the outer fields are floor/ceiling VOR and the center is a shaped ranking
    value, not a median projection. Suppress the strip on the draft path and show one group-level
    `Calibrated projection range unavailable` limitation. Do not bury it in E1 details or substitute
    conformal totals/ceiling-week semantics. The shared player surfaces require a separate audit.
20. **Clock state is presentation language, not a data contract.** No typed clock-limit or remaining-
    seconds field exists in the inspected frontend, engine, pipeline, database, or fixtures. Do not
    infer it from polling or pick timestamps, and do not treat speed as sophistication. A later
    source-defined clock/autopick archive can support a separate opponent/UI experiment, but it is
    neither an E0q–E2 dependency nor permission to add a countdown.

### 4.2 Non-goals

- unattended autodrafting;
- claiming optimality, guaranteed wins, or vendor endorsement;
- a new production agent framework;
- live learned psychological profiling of opponents;
- scraped proprietary recommendations;
- using historical appearance maps as 2026 availability;
- reopening C05 or replacing v5 authority through a UI feature.

## 5. Draft-board views and interaction hierarchy

### 5.1 Default hierarchy under the clock

When the decision region itself is brought to the top, its compact primary/alternatives/data-state
summary should fit within one 375×812 viewport before deeper details. This does not claim that the
global navigation, page title, draft-source setup, status, and decision region all fit on one page
load viewport; the populated route does not support that stronger requirement today.

1. **Primary candidate:** name, position, one-line reason, current v5 score/rank.
2. **Three alternatives:** one-line differentiator each, not three more full explanations.
3. **Data state:** “current as of …” only with provenance, otherwise “partial,” “date unknown,” or
   “market source unavailable”; never a confidence adjective without a calibrated target.
4. **Consequential tradeoff:** one supported present-state sentence such as “Fills RB2 now; adds no
   measured bye coverage.” Do not mention likely tier depletion until next-turn survival calibrates.
5. **Actions:** `Compare`, `What if` (only after validation), and `Details` disclosures.

All deeper lenses should preserve the same candidate set unless the user explicitly changes an objective. A lens explains or reorders displayed evidence; an objective control may re-score and must show that it changed the recommendation.

The evidence supports caution, not a universal numeric density rule: cognitive-load work comes largely from education and generic DSS tasks, while human–AI studies show that explanations can increase reliance without improving joint performance ([Sweller, 1988](https://doi.org/10.1207/s15516709cog1202_4); [Bansal et al., 2021](https://doi.org/10.1145/3411764.3445717)). Therefore this hierarchy is a hypothesis to test locally, not a settled usability law.

### 5.2 View specifications

#### View 1 — Best available (default)

- **Question:** “Who are the strongest reasonable choices at this pick?”
- **Required data:** current available pool, v5 scores, roster, league rules, explanation payload, source/degradation state.
- **Reuse:** `candidatePool`, `scoreBoardWithExplanations`, `v6DraftLiveScoring`, `LiveRecommendations`.
- **Cost:** current bounded scorer; no additional simulation.
- **Uncertainty:** show data-state/freshness now; add calibrated recommendation stability only after repeated-state tests.
- **Fallback:** v5 list with “market/uncertainty data unavailable”; never suppress legal candidates.
- **Mobile/a11y:** one primary card plus compact alternatives; semantic buttons; no hover-only evidence; static layout respects reduced motion.
- **Authority:** presentation only in the first unit; v5 recommendation is unchanged.
- **Release test:** exact candidate/rank parity with current v5, keyboard/screen-reader flow, 320 px viewport, missing-data snapshots, and explanation-claim contract tests.

#### View 2 — Value versus market

- **Question:** “Where does BlitzBoard disagree with the market, and by how much in rank?”
- **Required data:** BlitzBoard rank, named source rank or ADP, source kind, format, and as-of time.
- **Reuse:** `player_value.rank`, `player_value.adp`, snapshot column/tooltip patterns, DraftAnalysis reach/steal formatting.
- **Cost:** O(candidates × sources) display transform.
- **Uncertainty:** rank delta only; do not convert it to probability, standard deviation, or confidence.
- **Fallback:** “No lawful timestamped market source” and retain BlitzBoard rank.
- **Mobile/a11y:** two labeled rank rows and signed disagreement text; color never carries direction alone.
- **Authority:** presentation only until a rank blend separately clears promotion gates.
- **Release test:** source-kind labeling fixtures (rank vs ADP vs projection), stale-source rendering, absent source, and no endorsement language.

#### View 3 — Roster needs

- **Question:** “What roster problem does each candidate solve or create?”
- **Required data:** league slots, current roster, starter vacancies, bench counts, positional redundancy, legal caps.
- **Reuse:** `fillRoster`, roster-health/bench logic, immediate-lineup and bench-shape explanation components.
- **Cost:** current O(roster × candidates) transforms.
- **Uncertainty:** deterministic rule facts are labeled as such; future production outcomes remain uncertain.
- **Fallback:** if roster/config is incomplete, show generic best available and “roster context unavailable.”
- **Mobile/a11y:** short phrases (“fills WR2,” “third bench QB”) with expandable slot detail.
- **Authority:** can be either presentation or an explicit “roster balance” objective; default v5 behavior remains unchanged.
- **Release test:** all fixture roster shapes, incomplete manual drafts, superflex/2QB, K/DST, duplicate-free legal picks.

#### View 4 — Scarcity / next-turn availability

- **Question:** “How likely is this player or tier to remain when I pick again?”
- **Required data:** full draft state, next user pick, lawful point-in-time market board, per-seat bounded policy/type weights, seed, and calibration metadata.
- **Reuse:** `picksUntilNext`, snake transitions, `pickHumanAdp`, `draft_realism` scenarios, blind-market source isolation.
- **Cost:** offline N-rollout estimate initially; production requires measured latency, precompute, or a worker. Do not block the current pick on a slow result.
- **Uncertainty:** calibrated survival percentage plus sample size/model date and interval; distinct label from startability.
- **Fallback:** present-state tier/replacement wording without a probability: “Current heuristic sees
  a thinner RB replacement tier; next-turn survival is not calibrated.”
- **Mobile/a11y:** text plus optional meter; exact percent in accessible name; no animated Monte Carlo display.
- **Authority:** experiment first; presentation only until calibration clears. Later it may inform an explicitly selected scarcity objective.
- **Release test:** time-split Brier/log loss, reliability by horizon/format/position, exact replay, bounded seed variation, missing market, and latency budget.

#### View 5 — Draft-room dynamics

- **Question:** “What are other teams likely to do before my next turn, and what changed recently?”
- **Required data:** pick log, rival rosters/needs, recent positions/reaches, seat-policy posterior and poor-fit state.
- **Reuse:** `detectRuns`, `DraftPickLog`, `AllTeamsBoard`, current roster filling, bounded opponent policies.
- **Cost:** cheap descriptive summaries; predictive intervening-pick rollouts share View 4 results.
- **Uncertainty:** distinguish observed facts (“3 RB in 5 picks”) from modeled forecasts (“RB-heavy interval under current mixture”).
- **Fallback:** observed run/roster facts only.
- **Mobile/a11y:** maximum two observed signals and one forecast; expanded team list on demand.
- **Authority:** observed layer is presentation; modeled layer experiment first.
- **Release test:** fact/prediction label tests, stale pick stream, opponent poor-fit, and no hidden-projection leakage.

#### View 6 — Upside and risk

- **Question:** “What does the upside case require, and what is the downside?”
- **Required data:** conditional projection distribution, calibrated production uncertainty, startability probability, contingent role/depth facts, dates/sources.
- **Reuse:** independent model schema, `UncertaintyStrip`, structured contingent-role and breakout components.
- **Cost:** precomputed snapshot values; no live optimization.
- **Uncertainty:** keep conditional production intervals, health/startability, and contingent role separate. Do not display season-total p90 as weekly boom/ceiling.
- **Fallback:** qualitative component evidence and “distribution unavailable.”
- **Mobile/a11y:** median/range text precedes graphics; every bar has textual endpoints; no motion required.
- **Authority:** presentation until independent model authority changes through its own gate.
- **Release test:** interval coverage/proper score, semantic contract tests, rookies/incomplete histories, and deliberately degraded depth/injury inputs.

#### View 7 — Bye and absence coverage

- **Question:** “If I draft this player, which weeks or positions become fragile?”
- **Required data:** bye weeks, current starters/bench, eligible slots, replacement quality, startability inputs.
- **Reuse:** `byeStacks`, roster health, bench coverage, `AvailabilityModel`, lineup/waiver evaluator.
- **Cost:** deterministic roster recomputation per candidate; optional offline season simulation.
- **Uncertainty:** bye is known schedule data; absence/startability and replacement performance remain probabilistic and separately sourced.
- **Fallback:** bye-stack facts only; “absence model unavailable.”
- **Mobile/a11y:** list at most the most fragile week and affected slots; expand for all weeks.
- **Authority:** presentation first; any score change requires a paired evaluation showing it does not double-discount availability.
- **Release test:** missing byes, shared bye stacks, IR/bench depths, startability degradation, and no duplicate availability penalty.

#### View 8 — Market/source comparison

- **Question:** “How do lawful, timestamped market sources differ?”
- **Required data:** licensed/user-supplied source snapshots with source kind, format, as-of time, and normalization receipt.
- **Reuse:** snapshot publishing/hashing, source-evidence schema, player identity reconciliation, value-vs-market UI.
- **Cost:** ingestion/normalization offline; small client table.
- **Uncertainty:** source disagreement is shown as disagreement, not probabilistic uncertainty.
- **Fallback:** hide unavailable sources and explain why; never substitute an unlabeled consensus.
- **Mobile/a11y:** user selects at most two sources plus BlitzBoard; full matrix is a details view.
- **Authority:** presentation only. A source may inform a separately preregistered model experiment but not silently alter v5.
- **Release test:** license receipt, exact as-of/source labels, scoring-format mismatch warning, identity conflicts, and deletion/expiry path.

#### View 9 — Compare players

- **Question:** “What is the most consequential tradeoff among two to four candidates?”
- **Required data:** the current recommendation list, structured components, roster effect, lawful market fields, and data state.
- **Reuse:** existing top-four recommendation objects, reason chips, equity impact, explanation lines, roster transforms.
- **Cost:** current data only; O(4 × components).
- **Uncertainty:** per-row missing/degraded state; do not manufacture an overall confidence score.
- **Fallback:** compare only available facts and show em dashes with explanations for missing cells.
- **Unit boundary:** `immediate_lineup` is the projected lineup edge over estimated next-turn
  replacement; coverage/breakout/redundancy values are weighted score contributions. Prefer concrete
  coverage assignments and never place all component values under a generic projected-points label.
- **Mobile/a11y:** stacked candidate cards on narrow screens, sticky metric labels only if screen-reader order stays logical, selection limited to four.
- **Authority:** presentation only.
- **Release test:** primary candidate remains unchanged; two/four selection; keyboard removal; 320/768 px; missing fields; one-line fidelity to explanation payload.

#### View 10 — What-if

- **Question:** “If I take this candidate, what is likely to be available next and what roster need becomes fragile?”
- **Required data:** candidate action, legal draft state, opponent mixture, next-turn simulation, roster evaluator, uncertainty receipt.
- **Reuse:** draft-state transition, `pickHumanAdp`, `draft_realism`, `season_eval`, `fillRoster`. Do **not** reuse the lab injury redistribution as a forecast.
- **Cost:** candidate × rollout count; first version offline only. Production must cap candidates, horizon, and time.
- **Uncertainty:** distribution over next-turn candidates/tiers and roster outcomes, with seeds/model date; scenario is not a promise.
- **Fallback:** deterministic “after this pick” roster delta plus uncalibrated tier depletion wording.
- **Mobile/a11y:** one selected scenario at a time; side-by-side only on larger screens; cancelable calculation; static results.
- **Authority:** experiment first; never auto-pick the simulated winner.
- **Release test:** exact replay, alternate-seed bounds, scenario legality, candidate action actually applied, weak-candidate honesty, and timeout fallback.

#### View 11 — User preference controls

- **Question:** “How does the recommendation change if I explicitly value safety, upside, roster balance, or market alignment?”
- **Required data:** transparent objective components already displayed and a versioned control setting.
- **Reuse:** existing scoring components and explanation payload; in-memory state for the first
  experiment. Persist nothing until users demonstrate that persistence is useful and reset-safe.
- **Cost:** one scorer recomputation per control change.
- **Uncertainty:** show “objective changed” and the component delta; never call a preference setting more accurate.
- **Fallback:** default v5 objective and a one-click reset.
- **Mobile/a11y:** three segmented controls at most: conservative/upside, value/balance, market/contrarian; descriptive labels and reset; no hidden sliders.
- **Authority:** experiment first. Controls are explicit strategy variants, never silent personalization.
- **Release test:** deterministic mapping, reset parity, explanation fidelity, no illegal recommendation, recommendation-stability report, and user comprehension.

### 5.3 Coherent navigation rather than eleven top-level tabs

The eleven concepts should collapse into three surfaces:

- **Board:** Best available, compact roster/scarcity/dynamics signals, and source/data state.
- **Compare:** value-versus-market, roster need, upside/risk, bye/absence, and source comparison for two to four candidates.
- **Scenario:** what-if rollouts and explicit preference controls, hidden until each model is validated.

This avoids a dense analytics dashboard while retaining every requested question.

## 6. Heterogeneous-opponent model design

### 6.1 Smallest viable framework

Extend the existing seeded market picker with an experiment-only plain policy descriptor:

```text
OpponentProfile
  market_board_id          lawful, point-in-time board receipt
  top_k                    bounded reach tolerance: preregister {1,4,8,12}
  qb_timing                early | neutral | late, format-aware caps
  roster_shape             balanced | rb_depth | wr_depth | shallow_bench
  position_offsets         bounded rank offsets learned on training drafts only
  run_response             bounded recent-position offset
  clock_response           off by default; require lawful pick-clock evidence
  stack_response           off by default; enable only with validated effect
  handcuff_response        off by default; local and published evidence is weak
  risk_response            market proxy only unless a lawful risk feature exists
  sophistication_tag       internal experiment label, never a user diagnosis
```

This is configuration around `pickHumanAdp`, not a new class hierarchy. Every pick must still:

- draw only from the opponent's lawful market board and visible draft state;
- obey roster eligibility/capacity, K/DST rules, and duplicate constraints;
- use a recorded seed and deterministic seed derivation;
- remain inside a bounded candidate set so randomness produces plausible reaches rather than chaos;
- expose a trace containing eligible candidates, market ADPs, applied offsets, random draw, and final choice;
- never read BlitzBoard projection/value/explanation fields for market-only opponents.

### 6.2 Initial mixture

**Post-campaign correction:** do not implement the four-profile table below as the initial field.
The `(1,4,8,12)` stress arm missed its primary gate and no roster/dynamic coefficient has a real-
history estimate. Use homogeneous `topK=8` as the reference and `(4,8,12)` as the bounded offline
stress profile. The table remains a factor inventory for later one-at-a-time tests, governed by the
[heterogeneous-opponent experiment](2026-08-29-heterogeneous-opponent-experiment.md).

Candidate factor inventory for later one-at-a-time validation:

| Profile | Market adherence | Roster behavior | Dynamic response | Rationale |
|---|---|---|---|---|
| Chalk | `topK=1` | starter-capacity balanced | none | Deterministic market baseline and replay anchor. |
| Bounded flexible | `topK=4` | balanced | small validated run response | Closest to current bounded human picker. |
| Reach-tolerant | `topK=8` | balanced with format-aware QB cap | none | Existing campaign shows broader `topK` is plausible without chaotic picks. |
| Construction-biased | `topK=4` or `8` | one preregistered QB/position/bench pattern | small observed-roster response | Tests heterogeneity in roster construction without learned utility. |

Do not initially include favorite-team/name bias: the direct fantasy study found no favorite-team effect in its 2017 data. Do not initially amplify handcuffs: both the direct study and local experiment provide negative evidence. Stack preference should remain off until draft-log evidence distinguishes intentional stacking from correlated ADP.
Time remaining is also excluded from the initial mixture. The adjacent laboratory evidence that
people inspect less opponent information under a 20-second game deadline is a hypothesis generator,
not a draft coefficient. Add a clock-conditioned factor only when a lawful point-in-time log records
remaining time at each pick and the effect improves held-out likelihood/calibration without turning a
fast pick into a sophistication label.

### 6.3 Partial-history updating

For each opponent seat, maintain weights over the fixed profiles:

```text
posterior(profile | visible picks) ∝ prior(profile) × Π pick_likelihood
```

Implementation constraints:

- derive pick likelihood from the same bounded candidate probabilities used by the picker;
- use priors fit only on training seasons/rooms and a nonzero weight floor;
- update after each observed pick; never infer from private user data outside the connected draft;
- include an “all profiles poor fit” diagnostic based on held-out log loss or low total likelihood;
- do not show psychological labels. User language should be factual: “Team 7 has taken QBs earlier than the current market mixture,” not “Team 7 is low sophistication.”

### 6.4 Escalation ladder

1. homogeneous `topK=8` baseline;
2. `(4,8,12)` bounded stress profile;
3. calibrated rank-only Plackett–Luce/random-utility picker;
4. one validated format/roster factor at a time;
5. one measured clock-state factor, only if lawful remaining-time labels exist;
6. Bayesian reweighting of the smallest accepted fixed profiles;
7. learned agent only after all prior methods fail held-out calibration and sufficient lawful data exist.

At each rung, advance only if the added method improves preregistered held-out next-pick log loss/Brier score or paired decision outcomes without violating legality, source isolation, latency, and stability gates.

## 7. Next-turn availability model

### 7.1 Target and name

Use the explicit target:

```text
P(player remains undrafted immediately before user's next scheduled pick
  | visible draft state, league rules, lawful market snapshot, opponent mixture)
```

Recommended code/data name: `next_pick_survival`, never `availability`. Health/startability remains `p_startable`.

### 7.2 First development instrument: empirical bounded rollouts

For each of the primary plus three alternatives:

1. clone the visible legal draft state;
2. optionally apply the candidate as the user's current pick for what-if mode;
3. assign fixed, seeded opponent profiles;
4. simulate only intervening picks using `pickHumanAdp`;
5. repeat with preregistered seeds;
6. estimate player and tier survival frequency;
7. attach a binomial interval, rollout count, model version, market snapshot ID, and seed-set hash.

This is smaller and more auditable than fitting a new model. It also directly reuses the current seam. One-step rollout has a strong methodological precedent as a way to improve a feasible base heuristic without solving the full dynamic program ([Bertsekas & Castañón, 1999](https://doi.org/10.1023/A:1009634810396)).

These rollouts are the first tool available before lawful real-room labels because they can prove
software replay, latency, sensitivity, and fallback behavior. They are not the first release-model
candidate and cannot establish a calibrated live percentage. Once lawful labels exist, evaluate the
unconditional horizon baseline and shrunk empirical market-gap table first, then a direct binary
next-turn logistic model if necessary; retain the rollout as a calibrated comparator and what-if
generator.

### 7.3 Calibration and validation

- Primary forecast metrics: Brier score, log loss with probability clipping fixed before the run, reliability diagram, expected calibration error reported descriptively, and calibration slope/intercept.
- Slices: 1–3, 4–8, 9+ picks to next turn; position; round; team count; 1QB/superflex; bench depth; market source; rookies/incomplete histories.
- Baselines: deterministic ADP cutoff, homogeneous `topK=8`, empirical ADP survival by pick horizon, and current coarse replacement heuristic where comparable.
- Intervals: binomial Monte Carlo interval reflects simulation error only. It must not be described as total model uncertainty.
- Promotion gate: improve held-out Brier and log loss versus the simplest baseline, no material calibration failure in a preregistered high-volume slice, and remain within the production latency budget.

### 7.4 If rollouts fail

- **Too slow but calibrated:** distill to a discrete-time hazard or cache by draft-state features; verify parity on the same cases.
- **Fast but miscalibrated:** improve opponent mixture/data before changing the estimator.
- **Unstable across seeds:** increase draws or show a wider/low-confidence state; do not smooth away real uncertainty.
- **No representative 2026 labels:** retain qualitative scarcity and do not ship percentages.

The first fitted target, if M1 is insufficient, should be the binary event that exactly matches the
product question: survival to the user's next turn. A per-pick discrete hazard is an escalation for
validated selection-time or scenario needs, not the default. Continuous-time Cox/competing-risk models
are deferred because draft events occur on an ordered pick index, and their extra assumptions do not
repair missing point-in-time labels.

## 8. Preregistered experiment and validation matrix

### 8.1 Unit of analysis and leakage control

- Split by season and draft room, never individual picks from the same room across train/test.
- Fit profile priors/coefficients on earlier point-in-time rooms; evaluate on later frozen rooms.
- Freeze source snapshots before calculating outcomes; hash raw/normalized inputs, code, configs, seeds, and outputs.
- Historical 2018/2021/2024 fixtures remain development diagnostics. At least one untouched 2026+ window is required for confirmation.
- A user-assistance view may ship presentation-only without changing policy, but its UI usefulness requires a separate study.

### 8.2 Offline model matrix

| Axis | Preregistered cells | Required comparisons | Key failure checks |
|---|---|---|---|
| Opponents | homogeneous `topK=8`; `(4,8,12)` stress profile; later validated factor/posterior arms | calibration and paired draft outcomes | hidden-field leakage, implausible reach distribution, posterior overconfidence |
| Slot | front, middle, back | paired within identical room/seed | snake-turn horizon imbalance |
| League size | 10, 12, 14 | interaction with position scarcity | legal roster completion |
| QB format | 1QB, superflex | format-specific QB caps and survival | repeat v5 QB overcapitalization |
| Bench | shallow 4, standard 6, deep 8 | roster coverage and late-round behavior | incomplete K/DST or starter slots |
| Positional run | none/control; preregistered RB, WR, QB, TE depletion shocks | forecast calibration and recommendation response | double-counting observed runs |
| Draft clock | absent/control; later ample/mid/near-deadline only when lawful remaining-time labels exist | fixed versus clock-conditioned opponent mixture; separate UI deadline protocol | inferring time from pick order, calling speed sophistication, or pooling timeouts/autopicks with human choices |
| Market degradation | complete; 10% missing; 30% missing; stale; wrong-format source rejected | graceful degradation and calibration | source substitution or fabricated confidence |
| Player history | veterans; rookies; incomplete identity/history | missingness honesty | zero-valued rookies treated as known busts |
| Injury/depth degradation | complete; missing injury; stale depth; neutral fallback | separate startability and draft-survival outputs | semantic leakage between the two probabilities |
| Seeds | exact replay; fixed alternate seed set | byte-stable replay; bounded distribution shift | recommendation thrash |
| Candidate strength | strong, near-tie, deliberately weak legal candidate | fidelity and regret | hiding weak outcomes or forcing positive explanation |

The full factorial is too large. Preregister a balanced core of 12-team front/middle/back ×
1QB/superflex × bench 4/8, then targeted 10/14-team, clock, and degradation slices. Add a cell only
when it tests a named interaction; do not brute-force the combinatorial fixture matrix without a
decision it can change.

### 8.3 Offline metrics

| Family | Metrics | Interpretation guardrail |
|---|---|---|
| Recommendation quality | `started_points`, starter strength vs league median, paired H2H, playoff/championship proxies | Proxies are development measures, never guaranteed wins. |
| Next-turn survival | Brier, log loss, reliability, calibration slope/intercept, survival hit rate at displayed bins | Calibration is assessed on frozen future picks, not simulated labels alone. |
| Roster quality | starter completion, bench coverage, absence coverage, legal/duplicate-free rate | Legality is a hard gate, not a weighted metric. |
| Regret | realized outcome gap from the chosen candidate to the best of the other **reasonable top-four** candidates; report distribution and tail | Do not compare to an omniscient player outside the contemporaneous reasonable set. |
| Stability | exact replay hash; top-four Jaccard; primary-switch rate; score/rank change under alternate seeds | A probabilistic view may vary, but variation must be bounded and explainable. |
| Explanation fidelity | every displayed claim maps to a nonmissing payload field and correct sign/unit; weak candidates permit negative tradeoffs | No generated rationale independent of scorer evidence. |
| View disagreement | frequency, direction, candidate overlap, and whether disagreement predicts later regret or changes user choice | Disagreement is potentially useful information, not an error by default. |

### 8.4 Preregistered hypotheses and gates

| ID | Hypothesis | Primary measure | Advance rule |
|---|---|---|---|
| H1 | A simple calibrated survival model using public room state improves over homogeneous `topK=8` rollouts. | held-out Brier and log loss | Both improve on aggregate; no preregistered major slice materially worsens; legality/source isolation pass. `(4,8,12)` remains a stress comparator unless real behavior fit supports its weights. |
| H2 | Posterior reweighting improves the fixed mixture after enough observed picks. | conditional log loss after rounds 3, 6, 9 | Improvement after the declared minimum history; poor-fit detection remains calibrated. |
| H3 | One-turn candidate rollout reduces regret versus v5 ranking alone. | paired top-four regret and `started_points` | Confidence interval excludes the preregistered harm margin; latency and stability pass. |
| H4 | Compact compare improves understanding without unacceptable clock cost. | tradeoff recall and decision time | Better recall; median time increase below preregistered budget; no rise in constraint errors. |
| H5 | Showing calibrated survival changes choices usefully, not merely more often. | regret/choice-quality proxy plus calibration comprehension | No deployment until labels are calibrated; pilot alone cannot claim outcome improvement. |

Multiplicity: designate H1 and H4 as separate primary model/UI hypotheses. Others are secondary; report all intervals and exact cell counts. Do not promote on one favorable subgroup.

### 8.5 UI usefulness study

Run this separately from offline policy evaluation:

- Conditions: E0q/E0/E0a-repaired dense v5 cards; repaired compact primary+alternatives;
  compact+compare; later compact+calibrated survival. E0q/E0/E0a are common to every arm so false
  quantiles, copy fidelity, source order, and basic operability are not confounds.
- Tasks: three separately reported strata—high-disagreement stress, representative/unchanged
  controls sampled from U0, and missing/degraded-market states selected from T0/T1/T3—spanning slot,
  format, run, missing source, late K/DST, and a weak-primary trap. Do not add a measured-evidence
  condition until a valid point-in-time fixture exists.
- Outcomes: decision time, legal-choice errors, most-important-tradeoff recall, source/freshness comprehension, appropriate rejection/acceptance, view use, and mental/temporal demand.
- Instrument: task logs plus a preregistered raw NASA-TLX subset or full raw TLX; do not invent a composite after seeing results.
- Sample: first conduct a 6–8 participant formative pilot for defects only. Power the confirmatory within-subject or mixed study from pilot variance and a declared smallest meaningful effect; if recruitment cannot meet it, publish descriptive usability evidence only.
- Accessibility: include keyboard-only and screen-reader use; a 375 px product smoke; the
  320-CSS-pixel-equivalent WCAG Reflow boundary for non-table content with an explicitly assessed
  two-dimensional table exception; 200% zoom; reduced motion; and color-independent meaning checks.
- Advice order: only after the hierarchy study, run a separately analyzed immediate-primary versus
  non-forcing user-first shortlist/objective pilot. It must not replace the default hierarchy based
  on adjacent luggage-screening evidence alone, and agreement with BlitzBoard is not success.

## 9. Point-in-time 2026+ data acquisition and archival plan

The operational receipt schemas, consent boundary, cadence, quality gates, split protocol, incident
response, and first no-code source review are expanded in
[`2026-08-29-point-in-time-data-acquisition.md`](2026-08-29-point-in-time-data-acquisition.md).

### 9.1 Snapshot families

| Snapshot | Cadence and cutoff | Required contents | Retention |
|---|---|---|---|
| Player identity/roster | daily preseason and before every experiment | canonical IDs, team, position, roster status, depth role, rookie/experience flags | raw receipt + normalized table + mapping decisions |
| Health/depth | daily and event-triggered | report status, practice/depth evidence, source/effective time | immutable receipt; corrections append, never rewrite |
| Market board | daily by source/format, more frequently during final preseason week if licensed | source kind (ADP/rank/projection), league/scoring format, ranks/values, source as-of and retrieval time | source-specific immutable snapshot and license receipt |
| BlitzBoard forecast | every pipeline build | conditional distribution, `p_startable`, engine/version, input snapshot IDs | immutable snapshot and manifest |
| Draft history | after each lawful connected draft or consented export | room/format, ordered picks, timestamps when available, auto-pick marker if available, anonymized seat ID | private raw copy with retention controls; de-identified research derivative |
| Realized season | weekly lock | player outcomes, lineup/startability observations, corrections | immutable weekly revisions plus final-season freeze |

### 9.2 Provenance and reproducibility

Every normalized snapshot must have a manifest containing:

- snapshot ID and schema version;
- `source_url`, source product name and kind, license/permission basis, retrieval method;
- `source_as_of_utc` and `retrieved_utc` separately;
- request parameters such as season, teams, scoring, QB format, and expert set;
- raw and normalized SHA-256 hashes;
- code commit, normalization version, identity-map version;
- row counts, missingness, duplicates, unmatched identities, and degradation reasons;
- whether raw redistribution is allowed and when raw data must be deleted.

Point-in-time means no later correction can silently overwrite what the model knew on draft day. Append a revision with a new hash and link it to the superseded receipt.

### 9.3 Source priorities

1. **First-party/licensed public data:** nflverse releases for football history/rosters where the specific dataset license permits the use. `nflverse-data` states CC BY 4.0, but its project README also warns that underlying NFL data rights may belong to their owners, so retain per-dataset license records and attribution rather than applying one blanket assumption ([repository/license](https://github.com/nflverse/nflverse-data); [project terms note](https://github.com/nflverse/nflverse/blob/main/README.md)).
2. **Documented platform API:** Sleeper's API documentation describes a read-only API free for non-commercial use and directs commercial users to licensing; its current general terms separately say third-party retrieval requires Sleeper's own authorization and that a user's credentials or approval are not a substitute. Treat that conflict conservatively: use the documented endpoints only within an explicitly authorized use, obtain written permission before any commercial or third-party production reliance, and archive the controlling terms version. These pages were checked on 2026-08-29; recheck them before ingestion ([Sleeper API docs](https://docs.sleeper.com/); [Sleeper terms](https://support.sleeper.com/en/articles/5486620-general-terms-of-use)).
3. **Contracted vendor API:** FantasyPros offers API access, but its public API terms limit ordinary access to personal, non-commercial use and its support materials distinguish commercial access. Do not use site scraping or recovered partner keys; obtain a commercial agreement that covers storage, display, derived features, and archival. These pages were checked on 2026-08-29; recheck them before ingestion ([API terms](https://api.fantasypros.com/public/v2/terms-of-use); [API access](https://support.fantasypros.com/hc/en-us/articles/49749297704475-How-do-I-request-access-to-the-FantasyPros-API)).
4. **User-supplied export:** permit a user to import a rank/ADP CSV they are authorized to use. Store it privately, label it “user import,” and never redistribute or represent it as a platform recommendation.
5. **Unresolved sources:** Fantasy Football Calculator's endpoint is used in historical experiments, but this review did not find controlling official API terms. Keep the historical receipts, but do not make new production reliance or redistribution decisions until permission and retention rights are documented.

### 9.4 Confirmation schedule

- The official calendar places preseason Week 3 on August 27–29 and the opener on September 9.
  Since this plan is dated August 29, a four-week prospective 2026 archive is no longer possible;
  do not backfill it from current pages. Audit already-existing lawful receipts, treat any newly
  approved late window as a partial pilot, and reserve 2027 as the first full-window confirmation
  season if no compliant earlier archive exists ([official schedule](https://www.nfl.com/schedules/2026/by-week/reg-1);
  [Week 1 release](https://www.nfl.com/news/2026-nfl-schedule-release-complete-slate-of-week-1-games)).
- Designate the first portion for fitting and the final untouched portion/rooms for confirmation before examining outcomes.
- After the season, evaluate against frozen weekly realization data, not revised end-of-season aggregates alone.
- Preserve an untouched point-in-time confirmation window; do not consume every available room in
  iterative tuning. Call it 2026 confirmation only if the preexisting/prospective receipt coverage
  and preregistered slices are sufficient; otherwise make 2027 the first confirmation season.

## 10. Privacy, licensing, scraping, and platform boundaries

### 10.1 Privacy

- Collect the minimum connected-draft identifiers needed for sync; inventory each data element, purpose, processor, and lifecycle, then hash or replace user/seat IDs in research derivatives. This is a scoped application of NIST's voluntary Privacy Framework, whose Core calls for inventorying data elements, purposes, processing actions, parties, and environments rather than treating security alone as privacy management ([NIST Privacy Framework](https://www.nist.gov/privacy-framework); [Framework Core](https://www.nist.gov/document/nist-privacy-frameworkv10pdf)).
- Do not infer or display protected traits, psychology, or real-world identity from draft behavior.
- Opponent profiles describe pick patterns in one room, not people.
- Exact pick timestamps and remaining-clock traces can make behavior more identifying than an
  ordered pick list. Collect them only with an approved purpose/consent boundary, keep raw room IDs
  access-controlled, and prefer coarse clock bands in derived research artifacts when exact seconds
  are not required for the preregistered analysis.
- Keep ESPN cookies and other credentials in the existing encrypted per-user vault; never put them in client bundles, artifacts, logs, or shared snapshots.
- Provide deletion for connected credentials, imported rank files, and identifiable draft histories; document aggregate retention after deletion.
- Do not train a learned opponent model on private drafts without explicit consent and a stated retention/use policy.

### 10.2 Platform and licensing boundaries

- ESPN does not provide the repository a documented public fantasy API. Disney's terms prohibit automated access/copying without express permission, so ESPN sync remains user-authorized, best-effort private league interoperability—not a source for a redistributable market corpus ([Disney/ESPN terms](https://disneytermsofuse.com/english/)).
- Sleeper endpoints are technically sufficient for a live league/draft workflow, but technical sufficiency is not permission. Resolve the API-page/general-terms conflict and obtain Sleeper authorization before any commercial third-party production use, syncing, storage, or bulk collection; a user's consent alone is insufficient under the current terms.
- FantasyPros ranks, ADP, projections, and recommendations are distinct products. A license for one cannot be presumed to cover the others.
- The existing `pipeline/calibration_run.py` experiment path that searches page JavaScript for a FantasyPros partner key must be quarantined from future collection and production. Historical derived receipts may remain evidence, but no rerun or expansion should occur without authorization.
- Robots.txt is not a license. A publicly reachable page or key is not permission to systematically collect, store, or redistribute content.
- Retain source attribution and no-endorsement language. Never imply that ESPN, Sleeper, FantasyPros, nflverse, or FFC sponsors BlitzBoard or recommends a displayed pick.

### 10.3 Required pre-ingestion review

For every new market source, record a short approval receipt answering:

1. What exact product and fields are accessed?
2. Is access documented, authenticated, user-supplied, or contractually licensed?
3. Are commercial use, derived features, display, caching, historical retention, and redistribution allowed?
4. What rate limits and deletion obligations apply?
5. What attribution and trademark language is required?
6. Who approved the source and on what date/version of the terms?

If any answer is unresolved, the source stays experiment-disabled.

## 11. Phased roadmap

### Phase A — smallest high-confidence UI improvements

**Goal:** make explanations truthful and reduce clock-pressure density without changing v5 ranking.

- Remove the false draft P10/P50/P90 presentation from VORP fields and show one honest unavailable
  state; do not redesign the shared uncertainty system in the draft-only unit.
- Repair VONA/run/upside/market-gap/fallback reason semantics (E0).
- Add native search labels, selected states, player-specific action names, and row-header semantics;
  label BlitzBoard rank and projected fantasy points, and render null rank as unavailable rather
  than filtered row order;
  demote `Auto-draft all` behind a secondary native disclosure without removing manual control.
- Place the single recommendation region before the long table on narrow screens while keeping it
  at the right-rail top on desktop; keep secondary roster/plan panels after the board. Fix the
  observed 320/375 page overflow, unsupported status labels, heading order, empty action
  header, and consequential-action target size before compaction.
- Compress `LiveRecommendations` to a primary plus three alternatives and one-line faithful reasons.
- Add a two-to-four candidate compare disclosure as a separate E2 unit after E1 is stable.
- Add explicit missing/degraded labels; only add freshness when the queried field has source/as-of provenance.
- Test mobile, keyboard, screen reader, reduced motion, weak-candidate honesty, and exact scorer parity.

**Exit:** presentation-only tests pass and a formative local pilot finds no blocking comprehension/
clock defects. Claims of faster or better decisions require the preregistered study, not code metrics.

### Phase B — next-turn availability experiment

**Goal:** calibrate a separate player/tier survival forecast.

- Add an offline experiment target and receipts, not a production field.
- Use bounded rollouts now only for software, sensitivity, and latency evidence.
- On lawful frozen histories, score the unconditional/shrunk empirical baseline first, then a direct
  binary next-turn logistic model if needed, with rollouts as a calibrated comparator.
- If calibrated, design an asynchronous/cached delivery contract with explicit model date and fallback.

**Exit:** preregistered Brier/log-loss/calibration and latency gates pass. Otherwise retain qualitative scarcity only.

### Phase C — heterogeneous opponent experiments

**Goal:** determine whether the small mixture and partial-history updates improve survival forecasts or decisions.

- Fit bounded profile priors on training rooms.
- Compare fixed mixture and posterior-updated mixture to homogeneous baseline.
- Treat remaining clock as a later observed-state factor only when source-defined clock/autopick
  labels exist; exclude platform automation from human-policy fitting.
- Stress all required league/slot/bench/run/degradation cells.
- Preserve source isolation and exact replay.

**Exit:** measurable held-out gain with no legality, stability, or source-leak regression. Otherwise keep homogeneous picker.

### Phase D — market/source comparison

**Goal:** show lawful, timestamped source differences without changing recommendations.

- Land source receipt/as-of schema and archive process.
- Integrate only documented API, contracted, or user-import sources.
- Distinguish ADP, rank, projection, expert consensus, and recommendation in data and UI.
- Add source mismatch/staleness warnings and deletion.

**Exit:** licensing review and provenance tests pass; UI never fabricates a source or endorsement.

### Phase E — candidate what-if and explicit objectives

**Goal:** let the user explore consequences while retaining final authority.

- Candidate-specific one-turn rollouts for primary plus alternatives.
- Show likely next-turn tier/player set, roster fragility, and observed/model uncertainty.
- Add transparent preference controls only as separately versioned objectives with reset and explanation deltas.

**Exit:** rollout and UI studies pass; default v5 remains available and unchanged.

### Phase F — longer-term methods, only on demonstrated need

- calibrated Plackett–Luce/random utility for opponent choice when the bounded picker is inadequate;
- per-pick discrete hazard only when a validated selection-time/scenario question needs more than
  direct next-turn survival;
- selective two-turn rollout;
- calibrated joint weekly roster simulations and risk summaries;
- learned opponents or POMDP/MCTS only after data, calibration, and simpler-method failure prerequisites.

## 12. Build now / experiment first / reject or defer

### Build now

- Suppress the draft-only false P10/P50/P90 range derived from the active VORP value row; retain one
  group-level calibrated-range-unavailable message and exact candidate/score/order parity.
- Repair VONA/run/rank-gap/fallback reason semantics without changing scores or order.
- After E0q, repair populated-board source order, page reflow, accessible names/states,
  heading/table semantics, and consequential action sizing with native HTML/CSS. Do not add a UI
  kit or a permanent fixture route.
- Presentation-only primary-plus-alternatives hierarchy.
- Compare two to four current candidates from existing payloads.
- One-line faithful tradeoffs and explicit missing/degraded state.
- Source semantics in copy/tests: rank ≠ ADP ≠ projection ≠ recommendation.
- Honest available-table rank: null BlitzBoard rank is unavailable, never the filtered `i + 1`.

### Experiment first

- Strict market-opponent runtime isolation and frozen-replay parity; this is a harness prerequisite,
  not a new policy factor.
- Next-pick survival probabilities and intervals.
- Fixed heterogeneous opponent mixture and Bayesian reweighting.
- Positional-run response beyond the already bounded local term.
- Candidate what-if rollouts.
- Conservative/upside, value/balance, market/contrarian objectives.
- Any ranking blend, correlated-upside score, absence coverage score, or risk-sensitive objective.
- Reading engine-published `p_startable` into the live board. The existing table already stores
  `source` and `updated_at`, but the query discards them and no live caller exists. Re-run the
  closed component plan's availability-only shadow and paired no-regression guards before any
  score or candidate-pool effect; do not reopen C05 through presentation work.
- User study claims about cognitive load or decision quality.
- Clock-conditioned opponent behavior and advice-order effects, only with source-defined clock/
  autopick labels and a separately frozen accessibility-aware study protocol.

### Reject or defer

- Direct unconditional total-point integration.
- Historical appearance maps as live availability.
- ADP dispersion as forecast uncertainty.
- VORP `bust/value/boom` relabeled P10/median/P90 projected points.
- Season-total quantiles as ceiling-week boom/bust.
- Scraped/recovered-key proprietary market feeds.
- Favorite-team bias in the initial mixture.
- Handcuff amplification without new evidence.
- Learned opponents, deep recursive reasoning, CFR, full POMDP/MCTS, and CVaR optimization now.
- Clock pressure inferred from polling gaps/pick order, fast-pick sophistication labels, or platform
  autopicks pooled as human choices.
- Any guarantee, “optimal pick,” vendor endorsement, or unattended autodraft framing.

## 13. Exact files likely to change

These are likely changes by phase, not scaffolding to create now.

### Immediate usability sequence

E0q executes first. Suppress the invalid draft uncertainty strip in
`frontend/components/draft/LiveRecommendations.tsx` and freeze candidate/scorer parity in
`frontend/lib/v6DraftLiveIntegration.c04.test.ts`; add one focused renderer test only if needed.
The exact boundary and separate cross-product follow-on audit are in
[`2026-08-29-draft-uncertainty-semantics.md`](2026-08-29-draft-uncertainty-semantics.md).

After E0q, E0 repairs explanation fidelity:

- `frontend/components/draft/DraftWarRoom.tsx` — drive the VONA tag from the already computed
  `marginalStarterValue` explanation component, without another scorer call;
- `frontend/components/draft/reasons.ts` and `reasons.test.ts` — bounded run/market/fallback copy;
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts` — preserve one scorer call and exact score/order.
- `frontend/lib/v6DraftExplanation.ts` plus `frontend/lib/v6DraftExplanation.c03Interface.test.ts` —
  make the expanded immediate-lineup sentence name the next-turn comparator and unit without
  changing its component key/value/state.

The E0 boundary is specified in
[`2026-08-29-reason-fidelity-unit.md`](2026-08-29-reason-fidelity-unit.md).

E0a then restores the native-control and source-order baseline in
`frontend/components/draft/DraftWarRoom.tsx` plus one existing/focused renderer test: label search,
expose selected filter/view state, name draft actions by player, use player row headers, and demote
autodraft with native disclosure. Add no component library, state framework, or dependency. Label
the rank column and remove the filtered index fallback without changing row order. Its exact
interaction and QA boundary is in
[`2026-08-29-draft-board-native-semantics.md`](2026-08-29-draft-board-native-semantics.md).
The populated probe also authorizes only narrowly scoped semantic corrections in
`RosterHealthPanel.tsx`, `BenchPanel.tsx`, `LiveRecommendations.tsx`, and the existing sidebar heading
elements: remove unsupported status-dot names, restore a sequential heading outline, and preserve all
visible values/calculations. E0q removes the invalid draft uncertainty strip; do not modify the shared
uncertainty adapter/component in E0a. CSS changes stay within the existing JSX/Tailwind classes unless
the focused reflow fix demonstrably requires an existing stylesheet rule. Acceptance requires zero
page-level overflow at 320/375, a single recommendation before every player-row action in source/focus
order, table-local overflow only, and no listed axe violation on the populated synthetic route.
Add one `frontend/scripts/draft-board-smoke.mjs` QA script using only Node built-ins and the existing
Playwright/axe packages so that server-rendered populated state is reproducible without credentials.
Do not add `/draft` to the current shell-only non-blocking axe route list and call that coverage; its
no-key build cannot reach the board. The new script owns its loopback mock/Next lifecycle and writes
no default artifact.

After E0q, E0, and E0a are green, E1 is:

- `frontend/components/draft/LiveRecommendations.tsx` — E1 compact primary/alternative hierarchy
  and native full-evidence disclosure only; no compare state in this unit.
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts` — preserve single scorer invocation, primary parity, and rendered claim contract.
- A colocated component test only if current test infrastructure cannot exercise the disclosure through the integration test. Prefer not to add a component abstraction until the markup proves unwieldy.

E2 is a separate follow-on. Only after E1 is stable, add
`frontend/components/draft/PlayerCompare.tsx` plus a focused test; touch
`frontend/components/draft/DraftWarRoom.tsx` only if compare selection cannot remain local to the
new component. No scorer, engine, or database file belongs in E2.

### Provenance/source contract

- `db/migrations/<timestamp>_market_snapshot_provenance.sql` — only after schema review; source/as-of/license receipt fields or a normalized source-snapshot table.
- `db/schema.sql` — mirror the approved migration.
- `frontend/lib/types.ts` and `frontend/lib/queries.ts` — typed provenance reads and null-safe fallback.
- `pipeline/publish_snapshot.py` and/or engine snapshot schema — propagate source/as-of without enlarging the live payload unnecessarily.
- focused migration/query/snapshot tests.

Health/startability uses an existing schema and therefore needs no speculative migration:

- `frontend/lib/types.ts` — add a provenance-bearing read type using the already stored
  `season`, `week`, `source`, and `updated_at` fields;
- `frontend/lib/queries.ts` — preserve those fields instead of returning only a flat number;
- `frontend/app/draft/page.tsx` and `frontend/components/draft/DraftWarRoom.tsx` — only in an
  authorized shadow/integration unit, pass one immutable snapshot through to the scorer;
- `frontend/lib/draftAI.ts` and `frontend/lib/availability.ts` — reconcile `candidatePool` and
  final-score consumption under the same snapshot only if the paired experiment authorizes it;
- existing availability, draft scorer, fixture, and live integration tests — prove neutral
  degradation, source/date fidelity, no second scorer call, legality, exact replay, and no duplicate
  availability penalty;
- `engine/blitz_engine/snapshot/publish_availability.py` and its existing tests remain the publisher;
  do not add a second pipeline or storage framework.

This is not part of E0q/E0/E0a/E1/E2. Until its shadow gate passes, correct the overstated comments in the
frontend files when touched, but do not relabel the local fallback as engine-published truth.

### Next-turn survival experiment

- `frontend/lib/draftAI.ts` — define/reuse the narrow market-player/context picker seam; do not add production survival scoring here initially.
- `frontend/scripts/draft-eval.mjs` — project market arms to narrow runtime rows and bridge experiment inputs/outputs only.
- `engine/blitz_engine/backtest/draft_realism.py` — experiment-only opponent profile and rollout orchestration.
- `engine/blitz_engine/backtest/blind_market.py` or one narrowly named new experiment module if separation is necessary — survival labels, calibration report, receipt hashes.
- `engine/tests/test_draft_realism.py`, `engine/tests/test_blind_market_benchmark.py`, and `frontend/lib/blindDraft.test.ts` — replay, bounded variation, retained poison invariance plus runtime forbidden-key non-receipt, legality, and calibration fixtures.
- `docs/modeling/<dated-next-pick-survival-experiment>.md` — preregistration and results.

### Heterogeneous opponents and what-if

- Prefer the same draft realism and picker files above. Add no general agent package unless the fixed descriptor becomes demonstrably insufficient.
- `frontend/components/draft/DraftWarRoom.tsx` and `LiveRecommendations.tsx` only after offline validation and an approved delivery contract.
- Do not modify `frontend/components/lab/whatif.ts` to impersonate draft simulation; it remains a separate toy injury scenario.

### Data acquisition

- Replace or disable the recovered-key logic in `pipeline/calibration_run.py` before any future run involving FantasyPros.
- Add source-specific collection only after the license receipt identifies an approved script location; do not guess a connector/file in advance.
- Reuse the existing artifact manifest and snapshot hashing patterns rather than adding a second storage framework.

## 14. Acceptance criteria and rollback

### 14.1 Global acceptance criteria

- v5 remains production authority; C05 promotion is still unreachable.
- No implementation silently changes the default scorer, weights, market source, or availability semantics.
- Every recommendation remains legal; all simulated drafts/rosters are duplicate-free and complete.
- Exact seed replay is byte-stable; different seeds stay inside preregistered variation bounds.
- Market-only opponents receive no BlitzBoard projections, values, distributions, availability,
  metadata, or explanations; poison invariance and a runtime forbidden-key assertion both pass.
- Next-pick survival and health/startability have distinct types, labels, tests, and provenance.
- Every displayed explanation claim is supported by a present payload field with the correct sign/unit.
- No VORP floor/shaped-value/ceiling tuple is labeled as projection P10/median/P90 or raw points;
  an unavailable calibrated range is explicit until a typed calibrated snapshot exists.
- Missing, stale, rookie, injury, depth, and market degradation states are honest and usable.
- Host-platform, BlitzBoard-authored, and study timing are separately identified; missing clock is
  not inferred, autopicks are not human labels, and no timeout automatically selects for the user.
- Mobile, keyboard, screen-reader, zoom, color, and reduced-motion checks pass.
- No secret, credential, proprietary raw payload, or recovered key enters a client bundle, commit, or shared artifact.
- Full repository DoD is required for implementation units; this research-only unit requires Markdown/link/diff validation and repository-state preservation.

### 14.2 Per-layer rollback

| Change | Rollback mechanism | Data compatibility |
|---|---|---|
| Draft false-quantile suppression | restore component only for diagnosis; safe operational fallback remains one unavailable-range message, never the old strip | no DB change |
| Native semantics/reflow | revert the bounded markup/CSS/test unit; no scorer, pick, or persisted-state contract changes | no DB change |
| Compact E1 UI | revert the E1 renderer/test unit; current v5 recommendation payload remains intact | no DB change |
| Compare E2 UI | remove the optional compare component and entry control without reverting E1 | no DB change |
| Provenance fields | additive nullable schema; old readers ignore fields; new reader falls back to unknown source/date | keep migration; disable source ingestion/display rather than destructive rollback |
| Survival forecast | keep experiment/shadow output outside recommendation score; hide UI field on gate failure | immutable receipts retained for audit |
| Opponent mixture | config switch to homogeneous `topK=8`; same picker and seed contract | no user data migration |
| What-if | disable scenario action; default board remains synchronous v5 | cached scenario receipts may expire normally |
| Preference objective | one-click reset and server/client feature flag; versioned objective ID | stored old setting ignored safely if objective removed |

Stop and roll back a layer if it causes illegal picks/rosters, breaks replay, leaks hidden fields, mislabels a source/probability, exceeds the clock latency budget, materially worsens a preregistered primary metric, or creates an accessibility blocker.

## Recommended next implementation unit

**Unit: E0q draft-only false-quantile suppression, no scoring or schema change.**

Remove `playerUncertainty(player.value, null, "pts")` and its range strip from
`LiveRecommendations`. The active draft reads VORP: its outer fields are replacement-adjusted
floor/ceiling and its center is a unitless shaped ranking value, so the current P10/median/P90
projected-points display is not a coherent target or unit. Render one visible group limitation,
`Calibrated projection range unavailable`, and leave shared player uncertainty surfaces for the
separate audited follow-on. The exact test-first boundary is in
[`2026-08-29-draft-uncertainty-semantics.md`](2026-08-29-draft-uncertainty-semantics.md).

Acceptance for this independent unit:

1. identical four IDs, order, scores, links, reasons, and authorized actions;
2. one unchanged scorer call and no database, engine, query, weight, or simulation change;
3. no draft-path P10/P50/P90, median, probability, distribution, or points range reconstructed from
   `PlayerValue.bust/value/boom`;
4. exactly one visible, non-hover unavailable-range limitation;
5. focused renderer/live-integration tests and full frontend gates pass.

This two-or-three-file renderer/test unit removes a direct false probability/unit claim. E0 reason
fidelity, E0a native semantics/reflow, E1 compact hierarchy, and E2 compare then follow as separate
rollback units.
