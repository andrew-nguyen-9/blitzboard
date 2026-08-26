# v5 "Perfect the Draft" — cycle harvest (2026-08-25)

17 units, 9 waves. Companions: `docs/modeling/experiments.md` (how to reproduce every fit),
`docs/modeling/draft-eval.md` (the metric everything was tuned against),
`docs/design/v5-static-dynamic.md` (E12's reconciliation), `docs/design/v5-architecture.md`
(the design contract, now annotated with what the cycle overturned).

Every number below traces to a unit's own committed receipt. Nothing here is re-derived.

---

## 1. The headline: both fit units shipped ZERO weights

E10 (static, `draftAI.ts`/`benchScore.ts`) gated **six** candidates and shipped **none**.
E11 (dynamic, `FastDraftPolicy`/`DEFAULT_WEIGHTS`) gated **two** arms and promoted **neither**.
No shipped weight *value* changed anywhere in the cycle.

That is the deliverable, not a shortfall. Block-release (`v5-architecture.md` §6) was under real
pressure in wave 7 and held: every candidate failed honestly instead of being tuned into a pass.
Two of E11's arms are *measured losses* (CI95 entirely below zero), not merely unproven wins —
which is a strictly more useful result than a null.

**Why "did not help" is now trustworthy:** because E5 replaced the metric first. The
bench-insurance ablation moves E5's `started_points` by **+19.5 pts/season, p=0.0055**, while the
retired perfect-hindsight metric scores the *same two rosters* at **+43.9, p=0.2295 — blind**. A
negative result under the old metric meant nothing. Under the new one it means something.

## 2. Decisions taken

| # | Decision | Owner | Receipt |
|---|---|---|---|
| D1 | **THE METRIC** = `SeasonEvalResult.started_points` — points a *locked* lineup scored, per seat, under sampled availability × clinical injury × byes × contested waivers, leakage-guarded weekly by `detect_leakage`. | E5 | `docs/modeling/draft-eval.md` |
| D2 | Production and availability are **factorised**: the corpus week is "what he scores *if he plays*"; whether he plays is sampled. History's own absences never leak into the manager's decision. | E5 | `test_league_sim.py` |
| D3 | `roster_status` and `depth_rank` availability ceilings are **fitted**, not priors. Only NFI (0.0) and HOLDOUT (0.05) remain stated priors — no feed carries a code for either. | E2a | `survival/availability.py`, `fit_roster_state_priors` |
| D4 | The injury event is **clinical injury** (`report_status ∈ {Out, Doubtful}` OR `status ∈ {RES,PUP,NFI}`), carrying **zero snap-presence signal**, so E4 may multiply it by E2a availability without squaring the same signal. | E3 | `fixtures/injury_rates.json` `"event"` string; E4 asserts it in a test |
| D5 | Bench positional bounds are **derived** per config row against D1, not hand-set. `bench_bounds(row) -> BenchBounds`, all 432 rows (16 measured, 416 interpolated). | E6 | `fixtures/bench_shape.json` |
| D6 | The static fit drives the **real TypeScript policy** over a node bridge (one process per *batch* of drafts), never a Python port. `static_proxy` is unused in E10. | E10 | `frontend/scripts/draft-eval.mjs` |
| D7 | **Outcome B — the two draft formulas stay divergent**, and the split is now *measured*: seated on the same board/seed, the shipped dynamic policy is **−23.7 pts/season BEHIND** the static closed form, CI95 [−65.9, +19.0]. No 4-feature→20-knob bridge was built. | E12 | `docs/design/v5-static-dynamic.md` |
| D8 | `faPenalty` and `injuryDiscount` are **deleted** from `PolicyParams`/`DEFAULT_POLICY`; the web tier now multiplies by a published `p_startable` (`player_availability` table, RLS read-only). | E2b | `db/migrations/20260825_v5.2_player_availability.sql` |

## 3. Decisions reversed / overturned by measurement

- **E1's P1 (`byeStackPenalty: 12` as a flat constant) — refuted as a *shape*, upheld as a
  *lever*.** E6's roster-shape ablation found the sign is conditional on bench depth (8-slot
  benches: clustering beats spreading +18.9/+16.0/+12.4; 6-slot benches: reverses −23.6/−15.3).
  E10 then implemented exactly that conditional rule inside the shipped `scoreBoard` and measured
  it **worse** (−10.4, no_regression FAIL); dropping the penalty was also worse (−9.0).
  **Resolved by E12 as shape vs lever — different objects, neither wrong.** A shape can be right
  while the lever that reaches it is not. `byeStackPenalty` stays flat 12; the bench-depth seam
  (`byeStackDeepBenchSlots: 99` / `byeStackPenaltyDeepBench: 12`) ships **inert and
  behaviour-identical to E1**, so a future cycle can arm it without re-deriving the mechanism.
- **E1's P4 (`SF_MULTIPLIER` RB 1.2 / WR 1.1 both wrong-signed) — half right.** E6 measured mean
  derived bench ceiling 1qb → superflex/2qb: RB 3.75 → 2.50 (**−1.25**, so 1.2 is backwards),
  WR 1.50 → 2.25 (**+0.75**, so 1.1 has the *right* sign). A blanket "fix the SF multipliers"
  would have broken WR. E10 proposed RB only; it came back neutral (p=0.545) and did not ship.
- **The v2.4 backtest's "left unchanged" verdict** — the reasoning ("the metric can't see bench
  value, so keep the terms") was *correct about the metric* and is now superseded by having fixed
  the metric. See `docs/modeling/backtest-report.md` §Superseded.
- **`status_description_abbr` as the IR signal** — looks exactly right, is unusable. See §5.
- **E8a's bench-coverage invariant** — was not merely unfinished, it was **FALSE**. E6's derived
  bounds give ceiling 0 for a position in 234/432 rows, so the coverage claim cannot hold as
  written. E8b **removed** it and superseded it with a real bench-mix *upper*-bound test rather
  than loosening it until green. Engine xfail count 432 → 0, skip 3 → 2.

## 4. Negative results — the most valuable output of the cycle

These are measured, re-runnable, and the reason nothing shipped. Commands in
`docs/modeling/experiments.md`.

| exp | Δ pts/season | verdict | why it matters |
|---|---|---|---|
| `byeStack_conditional` | −10.44 (p=.053) | no_regression FAIL | the conditional rule that E6's shape ablation implied *loses* as a lever |
| `byeStack_off` | −9.03 (p=.118) | no_regression FAIL | dropping the penalty is also worse — the flat 12 earns its place |
| `sf_multiplier_rb` | +1.20 (p=.545) | neutral | directionally right per E6, invisible to this metric |
| `trade_value_zero` | +5.34 (p=.021) fit slice → **−1.08 (p=.403)** held-out 2021 | FAIL held-out | the sign-flipping signature E6's P11 predicted **structurally**; TradeValue is **pinned at 10, never free-fit** |
| `injury_rate_clinical` | **−13.97 (p=.0015)** | HURTS | see §5 — a semantic mismatch, not a bad number |
| `kdst_soft_penalty_e6` | +2.08 (p=.673) | neutral | E6's high-confidence median (cap 2 + soft_penalty 4.06) unproven; incumbent 20 stands |
| MCTS-distilled dynamic | **−60.2** CI95 [−93.3, −25.7] | no-help | distillation *worked* (agreement 0.357 → 0.643) — copying the search better moved it further from the metric |
| PPO (E5 reward) | **−26.7** CI95 [−45.7, −7.2] | no-help | scaling PPO 5× made it *worse* (+1.7 → −26.7): reward noise swamping signal |

### The convergent diagnosis — the defect is the LEAF EVALUATOR

Two units reached it from opposite directions and this is the single most reusable finding:

- **E11 (from inside):** the distilled linear policy faithfully copies an MCTS search whose leaf
  evaluator is the static `starter_value` roster sum — **blind to byes, inactives and waiver
  holes**. Higher agreement therefore means a *worse* E5 score. The lever is the leaf, not more
  search, not more features, not more PPO steps. E11's fitted `equity` and `vona` came out
  numerically **identical** (collinear on the real board) — capacity is not the constraint.
- **E12 (from outside):** on the identical grid and seed, E5's own per-pick marginal-starter-value
  picker (`engine_msv`) beats the static closed form by **+82.68, CI95 [+43.11, +122.51]**. So a
  per-pick rule *can* win ~5%. The shipped policy delivers −23.7 of an available +82.7 — roughly
  **106 pts/season of real, unclaimed headroom**. Worst slice of the shipped comparison is
  `t12-1qb-half-te0.5-b8-ir0` at −117.52 [−177.33, −58.75]: deepest bench, thinnest wire —
  **exactly where a bye/inactive-blind leaf should fail**, which is what makes the diagnosis
  credible rather than a post-hoc story.

This separates *"dynamic search does not help"* from *"OUR dynamic implementation does not help."*
Different conclusions, different next actions.

### The falsifiable flip condition (inherited bar for the next cycle)

Outcome B flips to Outcome A — build the feature bridge — when a **learned** dynamic policy,
seated by `evaluate_seated`, beats `static_proxy` with a **CI95 lower bound strictly above 0** on
**E11's 3×3 grid at seed 20260825** (i.e. reproduces something like E12's contrast [3] without
being E5's own picker). Until then the seam stays open and unused. Stated up front, not after the
fact.

## 5. Data-layer traps that cost real time — do not re-discover these

1. **The join bridge (measured, not guessed).** Status feeds (`injuries`, `weekly_rosters`,
   `depth_charts`) key on `gsis_id`; `snap_counts` keys on `pfr_player_id`. Bridge via
   `player_ids` = **80.8 %** of snap_counts' 6,707 distinct pfr ids. Via `weekly_rosters.pfr_id` =
   **55.0 %**. **Use `player_ids`.** Filter `gsis_id IS NOT NULL` (4,480/12,480 crosswalk rows are
   non-NFL); collapse its 3 duplicate `pfr_id`s with `min(gsis_id)` or the join multiplies rows.
   The ~19 % unbridged players are **missing status**, never "healthy".
2. **The column trap.** `weekly_rosters.status_description_abbr` *looks* like the IR signal and is
   unusable: **51 % NULL in 2016**, and `R01` all but vanishes 2016–2019 (0.05 % of rows vs 12–19 %
   either side) while `status='RES'` stays flat. Using it manufactured a fake four-year injury
   drought and blocked E3's calibration gate at 0.283. **Use `status`.** Seasons 2014–15 are
   excluded (`FIRST_RELIABLE_SEASON = 2016`; reserve share 7.0 %/10.6 % vs a 13–17 % steady state).
   Separately: **2025 `depth_charts` carry a SECOND schema inside the same table** (`dt`/`team`/
   `pos_abb`/`pos_rank`, no week) — split on `season IS NOT NULL` vs `dt IS NOT NULL`.
3. **The semantic distinction (this is the one that must not silently re-form).**
   `DEFAULT_POLICY.injuryRate` means *"the fraction of a season a starter MISSES"* —
   availability-like. E3's fitted rates are **clinical incidence**. **Different quantities.**
   Swapping E3's numbers into the knob HURTS: **−14.0 pts, p=0.0015**. Availability is E2a's
   `p_startable`, published separately and multiplied separately. This distinction is exactly why
   the double-count was removed in wave 3b; `fixtures/injury_rates.json` now carries an `"event"`
   string spelling it out, and E4 asserts that string in a test so a future refit toward a snap
   proxy fails loudly instead of silently restoring the double-count.
4. **Worktree PYTHONPATH.** See `docs/modeling/experiments.md` §0 and the `DoD-note` in
   `CLAUDE.md`. It degraded per-unit verification for most of this cycle.

## 6. Process findings worth keeping

- **Three latent bugs surfaced only after the event definition was fixed** (E3): recurrence
  covariates leaking across the offseason (a December IR stint set week-1 hazard nine months
  later — 4.4σ, the single largest calibration error); `DurationModel` reporting unbounded latent
  means of 10–26 games missed inside a 17-game season; and `weeks_since_return` never coinciding
  with an event, making the entire re-injury fit a **structural zero**. All three were invisible
  under the old snap proxy. E3's gate blocked twice on the way (0.283, then 0.110) and **both were
  real defects fixed, not thresholds tuned around**; it passes at cal_err **0.055** (< 0.10).
- **Held-out validation is what caught the only "win".** `trade_value_zero` cleared the 2024 fit
  slice at p=0.021. A single-slice fit would have shipped a meaningless number.
- **The per-wave integration DoD caught what no per-unit DoD could see:** a circular import between
  `lineup.feasibility` and `simulation` that existed only once E4 and E5 were *both* merged. Each
  was green alone.
- **RUFF DISCREPANCY (recorded, deliberately not fixed here).** 8 pre-existing ruff issues sit on
  `integration` in `engine/blitz_engine/testing/corpus.py` and `engine/tests/test_backtest_metrics.py`,
  attributed to E7b — whose note claimed ruff clean. Engine ruff is **not** on the `CLAUDE.md` DoD
  line (engine DoD = pytest), so this is not a gate violation. It is recorded because every
  downstream unit trades on notes, and a note-vs-tree inconsistency devalues all of them. Reconcile
  it deliberately; do not inherit it silently. Reproduce:
  `(cd engine && ../pipeline/.venv/bin/python -m ruff check blitz_engine/testing/corpus.py tests/test_backtest_metrics.py)`.

## 7. E13 deferred

**E13 war-room explainability UI is deferred**, deliberately and with no work started
(`v5-architecture.md` §8). The existing `explain` / `shapley_pick_attribution` surfaces are left
intact for it. Nothing in this cycle depends on it, and nothing it would need was removed.

## 8. Open questions for the next cycle

Ordered by expected value; (1) subsumes most of the others.

1. **Swap the MCTS leaf evaluator to a sim-priced one** (E11's `equity_evaluator` / `p_champion`)
   on the real board. Everything else in the dynamic tier is downstream of the leaf, and both E11
   and E12 point at it independently. This is the concrete next experiment.
2. **Variance-reduced RL reward** — common random numbers across rollouts, antithetic availability
   draws. E11's PPO reward used `n_seasons ≤ 2` per rollout for cost and the noise exceeded the
   signal; this was never tried.
3. **Close or bound the `static_proxy` ≠ `draftAI.ts` gap exactly.** E12 §4 bounds it at ~1.1 %
   *in the static tier's favour* (proxy 1527.1 vs real-TS 1543.6–1546.1) but the anchor's halves
   come from different league compositions. A per-config correction table from matched-seat runs is
   cheaper than seating TS per-pick (which `v5-architecture.md` §5 forbids on cost).
4. **Settle shape-vs-lever properly** by gating ONE bye candidate on **both** decision surfaces in
   a single run.
5. **~14 `DEFAULT_POLICY` knobs are still un-backtested hand-authored numbers**, as are the whole
   `GENERAL_WEIGHTS` / `GENERAL_PENALTIES` / `SF_QB_WEIGHTS` tables. `matrix.all()` (432 rows) was
   **never swept** by any simulating unit — only `smoke()`'s 16 rows.
6. **E6's 416 interpolated rows are not evidence.** Only 16 are measured; `--full` (~2.5 h) never
   ran. And E6 exported a **real regression row**: `t14-2qb-std-te0.5-b4-ir1` at **−25.3,
   p=0.0025**, checked in as `KNOWN_REGRESSION_ROW` so it cannot vanish silently. Thin-bench
   multi-QB rows need re-derivation before anything is applied there.
7. **E7b's corpus still drops injury / roster / ADP fields** (built before E9b landed those feeds).
   E5 samples from the models rather than the corpus, so this is not load-bearing today, but a
   corpus rebuild would now get real ADP and a real injury_status column.
8. **K/DST timing is not a constant and not v4's 2.** E6 measured caps spanning **2–13** and
   penalties **0.36–47.5 pts/round**, with 6 of 16 rows flagged `confidence="low"` because E5
   models no K/DST *streaming*. Fixing streaming in the simulator would make those rows usable.
9. **E5's declared omissions** — no FAAB, no trades, no speculative stashes, no playoff bracket.
   Trades in particular are why `TradeValue` has zero gradient; adding them is the only way that
   knob ever becomes fittable.
10. **Week-1 absences are under-predicted** (~8 predicted vs ~22 actual WRs) because training-camp
    injuries have no preseason exposure anywhere in the store. Survives the gate; biases the
    published rate very slightly low.
