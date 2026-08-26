# v5 experiments — how to reproduce every fit

Every fit run in the v5 "Perfect the Draft" cycle, with its seed, command and expected output.
Assembled from `engine/experiments/static/README.md`, `engine/experiments/dynamic/README.md` and
each unit's committed receipts. Verdicts and interpretation live in
`docs/decisions/2026-08-25-v5-perfect-the-draft.md`; the metric itself is `docs/modeling/draft-eval.md`.

**One seed rules the cycle: `20260825`** — it is E7b's `GOLDEN_SEED`, E5's `SEASON_EVAL_SEED`, and
the default `EvalConfig.seed`. Same seed ⇒ bit-identical `per_season` matrices (asserted with
`array_equal`, not `allclose`). E3's fit is the one exception: it uses `DEFAULT_SEED = 7`, and
nothing in that fit draws a random number anyway — the seed only feeds `DurationModel.sample`.

---

## 0. Environment — read this first

One venv serves both Python tiers: **`pipeline/.venv`** (3.12, jax/torch/numpyro + `blitz_engine`
installed **editable**). Homebrew `python3` is 3.14 and will not work.

**In a linked git worktree the editable install resolves to the MAIN checkout.** So
`cd engine && pytest` collects the *worktree's* tests but imports the *main checkout's*
`blitz_engine` — you can green-light code that is not yours, silently. Two consequences:

```sh
# correct invocation from a linked worktree
cd <worktree>/engine
PYTHONPATH="$PWD" /abs/path/to/blitzboard/pipeline/.venv/bin/python -m pytest
```

- `PYTHONPATH=<worktree>/engine` is **mandatory**, not a nicety.
- `../pipeline/.venv` **does not exist** in a linked worktree (`.venv` is gitignored) — use the
  absolute main-checkout path.
- `frontend/node_modules` is not shared either: run `npm ci` in the worktree's `frontend/` before
  anything that needs `node_modules/.bin/tsx` (the static-fit bridge does).

From the main checkout the relative forms in the commands below are correct as written.

**Data root.** Everything ingested lives at `~/.blitz_engine` (outside the repo, uncommitted):
13 flat `<table>.parquet` files, ~353 MB, seasons 2014–2025 with no holes. E9 ingested
`pbp` (580,005 rows) · `snap_counts` (300,812) · `ngs_{passing,rushing,receiving}` ·
`pfr_{pass,rush,rec}` · `ftn_charting`. E9b added `injuries` (65,864) · `weekly_rosters` (530,345) ·
`depth_charts` (954,626) · `player_ids` (12,480 crosswalk, no season column). Rebuild:

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.data.ingest.nflverse --season 2024   # per season, resumable
```

The **checked-in fixtures** are the shareable artefacts — every experiment below reads a fixture,
not the store, except the two model fits in §1 and §2.

---

## 1. E3 — injury hazard fit (clinical injury)

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.survival.hazard \
    --data-root ~/.blitz_engine --seed 7 --out fixtures/injury_rates.json
```

Exits 1 if the calibration gate blocks. Entry point in-process:
`blitz_engine.survival.hazard.fit_injury_model(data_root, seed=7, holdout=2)`.

**Expected:** `[PASS] cal_err=0.055 log_loss=2.439 crps=1.661 sharpness=2.901
discrimination=0.958 top12=0.83 (n=180)` — threshold 0.10, hold-out 2024–25, overdispersion 1.63.
Two full refits at seed 7 produce **byte-identical** `fixtures/injury_rates.json`.

**Published rates** (`injuryRate`, clinical incidence): QB 0.0953 · RB 0.1588 · WR 0.1620 ·
TE 0.1725 · K 0.0847 · DST 0.0. QB is the **lowest** non-K rate; under the retired snap proxy it
was the **highest** (0.2162). That ordering flip is the headline evidence the refit worked.

Event definition: `injuries.report_status ∈ {Out, Doubtful}` OR
`weekly_rosters.status ∈ {RES, PUP, NFI}` — **zero snap-presence signal**. The fixture carries an
`"event"` string saying so; read it before ever baking these numbers into a policy knob (they are
*not* the same quantity as `DEFAULT_POLICY.injuryRate` — see `draft-eval.md` §5).

Companion re-injury/duration numbers: baseline onset hazard 0.0378/week, re-injury elevation
**0.616** decaying over 8 weeks, `expected_games_missed` QB 6.9 / RB 6.7 / WR 6.8 / TE 7.6 / K 9.6
(season-capped **latent** duration; 38 % of spells are right-censored, so it exceeds the observed
mean spell of ~4.3 — reconcile via the renewal identity against the *observed* mean, not this one).

## 2. E2a — availability priors fit

Not a CLI; two functions, both re-runnable in a REPL, both reproducing every baked constant:

```python
from blitz_engine.store import ParquetStore
from blitz_engine.survival.availability import (
    fit_roster_state_priors, fit_depth_rank_priors,
)
s = ParquetStore.open("~/.blitz_engine")
fit_roster_state_priors(s.table("weekly_rosters").df(),
                        s.table("snap_counts").df(),
                        s.table("player_ids").df())
fit_depth_rank_priors(s.table("depth_charts").df(), ...)
```

**Expected `ROSTER_STATE_P` raw rate/n** (weekly_rosters × snap_counts, 2014–2025 REG, QB/RB/WR/TE):
ROSTERED .7305/87,611 (the 1.0 reference) · INACTIVE .0008/9,555 · PRACTICE_SQUAD .0031/19,907 ·
IR .0009/13,228 · PUP .0000/321 · SUSPENDED .0066/301 · CAMP_BODY .0095/9,468 · RETIRED .0000/528 ·
FREE_AGENT .0000/52. **`DEPTH_RANK_P` 1/2/3 = .896 / .625 / .416** (n 31,298 / 29,392 / 17,751,
2014–2024 REG). Ranks 4/5/6 = .379/.261/.150 and tail .052 are the fitted rank-3 value continued in
`SNAP_RANK_P`'s ratios — a fitted anchor plus a documented monotone extension.

Exactly two ceilings remain **stated priors** — NFI (0.0) and HOLDOUT (0.05) — because
`weekly_rosters.status` carries no code for either. Both are marked `PRIOR:` inline. Do not bake
them as measured.

Join: **`gsis_id → player_ids.pfr_id → snap_counts.pfr_player_id` (80.8 %)**, never
`weekly_rosters.pfr_id` (55.0 %). Encapsulated in `gsis_to_pfr`.

## 3. E7a/E7b — the fixtures every later experiment reads

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.testing.generate_matrix     # fixtures/league_matrix.json, 432 rows + 16-row smoke
../pipeline/.venv/bin/python -m blitz_engine.testing.corpus --data-root ~/.blitz_engine   # fixtures/seasons/{2018,2021,2024}.json
cd ../frontend && node_modules/.bin/tsx scripts/gen-golden-drafts.mjs --check             # -> "16 row(s) byte-identical"
```

Corpus seasons are **2018 / 2021 / 2024** (NGS 2016+, PFR 2018+; 2018 is 16-game and 2021/2024 are
17-game so week-count assumptions get exercised). Golden season 2024, seed 20260825.
`points[<scoring>:<te_premium>]` is pre-computed for all six (scoring × te_premium) pairs, which is
why the corpus is byte-identical from Python and Node — there is no scoring logic on either side of
the boundary.

## 4. E6 — derived bench bounds and K/DST timing

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.value.roster_shape           # 16 smoke rows, ~20 s/row ≈ 5 min
../pipeline/.venv/bin/python -m blitz_engine.value.roster_shape --full    # all 432 rows, ~2.5 h — NEVER RUN
```

Seed 20260825. Writes `fixtures/bench_shape.json` (bounds + K/DST timing + every arm's
delta/stderr/p — the audit trail). Method: **mirrored half-league ablation** — half the seats play
the arm, half the FILLER baseline, then a second run swaps them with the same seat permutation, so
the per-seat paired difference cancels the draft-slot effect. Starters are identical in every arm,
so a delta is a pure **bench** effect. `lo` = deepest body clearing 2σ (hard); `hi` = deepest depth
within 1σ of the best (soft).

Block-release evidence: `pytest tests/test_roster_shape.py -k derived_numbers` — E6's derived
numbers vs v4's hand-set constants over all 16 smoke rows: **+12.3 started pts/season pooled,
positive on 10/16** (6 at p<0.05). **Not** a per-row win: `t12-1qb-half-te0.5-b8-ir0` is a null
(−0.66, p=0.96) and **`t14-2qb-std-te0.5-b4-ir1` is a real −25.3 regression (p=0.0025)**, exported
as `KNOWN_REGRESSION_ROW` and asserted so it cannot vanish silently.

**Only the 16 smoke rows are measured.** The other 416 are interpolated from the nearest measured
neighbour (`BenchBounds.measured == False`) and **are not evidence**.

E1-hypothesis verdicts produced here (P1 refuted as a flat constant, P4 RB confirmed wrong-signed /
WR refuted, P11 confirmed unfittable) are recorded in `BENCH_MODEL.md` §6 and the decisions harvest.

## 5. E10 — static-tier fit (`draftAI.ts` + `benchScore.ts`)

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.backtest.static_fit --all --seasons 8
#   -> engine/experiments/static/results.json

../pipeline/.venv/bin/python -m blitz_engine.backtest.static_fit \
    --only trade_value_zero --seasons 8 --season 2021 --seed 20260826 \
    --out experiments/static/holdout-2021.json
#   -> engine/experiments/static/holdout-2021.json
```

Seed **20260825**, `n_seasons=8`, all 16 `matrix.smoke()` rows, corpus season 2024 ⇒ **n = 1176**
paired observations. Needs `npm ci` in `frontend/` (the bridge shells out to `tsx`).

The real TypeScript policy is driven over `frontend/scripts/draft-eval.mjs` — one node process per
**batch** of drafts (~0.5 s/draft; per-batch because the tsx compile would otherwise dominate).
`benchScore`'s tables are module consts with no injection seam, so the bridge mutates-and-restores
them around each draft. **E5's `static_proxy` is not used anywhere in this unit.**

Gate adapter: `ablation()`/`no_regression()` are MAE-shaped (lower better) and the metric is points
(higher better), so each arm is presented as a shortfall predictor `CEILING(3000) − started_points`
against an actual of 0 — MAE is then a strictly decreasing affine function of the metric and both
gates keep their published meaning. `no_regression` runs at `tolerance=0.0` (no worse than
incumbent), deliberately tighter than the 0.02 default. Neither `ablation.py` nor `harness.py` nor
the simulator was modified.

**Expected (`results.json`, 2024 fit slice, seed 20260825, n=1176):**

| exp id | change tested | Δ started pts | verdict | p | no_regression | ships |
|---|---|---|---|---|---|---|
| `byeStack_conditional` | `>=7` bench slots ⇒ −12 (cluster bonus), else 18 | −10.44 | neutral | 0.0525 | FAIL | no |
| `byeStack_off` | `byeStackPenalty: 0` | −9.03 | neutral | 0.1175 | FAIL | no |
| `sf_multiplier_rb` | `SF_MULTIPLIER.RB 1.2 → 0.67` | +1.20 | neutral | 0.5445 | pass | no |
| `trade_value_zero` | SF RB/WR `TradeValue 10 → 0` | +5.34 | **helps** | 0.0205 | pass | cleared here, failed held-out |
| `injury_rate_clinical` | `injuryRate` ← E3 clinical rates | −13.97 | **HURTS** | 0.0015 | FAIL | no |
| `kdst_soft_penalty_e6` | `kdstSoftPenalty 20 → 4.06` (cap 2 unchanged) | +2.08 | neutral | 0.6730 | pass | no |

**Expected (`holdout-2021.json`, corpus 2021, seed 20260826):** `trade_value_zero` **−1.08 pts,
neutral, p=0.4025, no_regression FAIL.**

**ZERO weight values changed.** Because nothing moved, E7b's golden drafts are byte-identical and
were not regenerated (`gen-golden-drafts.mjs --check` is the proof).

## 6. E11 — dynamic fit (MCTS → distill → PPO)

```sh
cd engine
PY=../pipeline/.venv/bin/python      # linked worktree: absolute venv path + PYTHONPATH
$PY experiments/dynamic/run_dynamic_fit.py distill --mcts-iter 500 --drafts 9    # ~57 s
$PY experiments/dynamic/run_dynamic_fit.py gate --n-seasons 4                    # ~5 s
$PY experiments/dynamic/run_dynamic_fit.py ppo --ppo-iters 30 --episodes 6 \
      --reward-seasons 2 --n-seasons 4                                           # ~40 s
```

Grid: seasons **2018 / 2021 / 2024** × rows **`t8-1qb-std-te0.0-b4-ir0`**,
**`t12-1qb-half-te0.5-b8-ir0`**, **`t10-2qb-ppr-te0.0-b8-ir1`** = 9 configs × `n_seasons=4`
= **36 paired evaluation points**, seed **20260825**. Promotion bar: the 95 % bootstrap CI of the
paired edge must clear 0. The candidate is seated in the mix's `engine_msv` seats via
`real_env.policy_pick_fn`; every other seat is E5's own `_pick`, so the field is identical.
`season_metric_edge(p, p, …)` returns exactly `[0.0, …]` — pairing is bit-identical, so any
non-zero edge is real policy difference, not sampling noise.

**Expected (`experiments/dynamic/results/`):**

| experiment | mean edge (pts/season) | 95 % CI | verdict | promoted |
|---|---|---|---|---|
| MCTS-distilled weights vs shipped cold weights | **−60.2** | [−93.3, −25.7] | no-help | no |
| PPO (real universe, E5 reward) vs distilled baseline | **−26.7** | [−45.7, −7.2] | no-help | no |

Both CIs lie entirely below zero: measured losses, not unproven wins. Distillation agreement rises
**0.357 → 0.643** over 84 real decision points (`E11_AGREEMENT_FLOOR = 0.55` is the asserted floor
at the cheap `n_iter=60` test setting). Fitted-but-**rejected** weights sit in
`results/distill.json` (`equity −0.0077, vona −0.0077, run_prob 0.920, need −1.332`) — do **not**
ship them; `equity` and `vona` come out numerically identical, i.e. collinear on the real board.
PPO checkpoints: `checkpoints/trace.json` is committed as the receipt; the `.pt` is gitignored,
regenerate from the seeded runner. Local compute only — float32 CPU, a 4→16→1 net, ≤90-player board.

## 7. E12 — the cross-tier reconciling measurement

Not a fitted experiment: a single measurement seating **both tiers in one E5 league**
(`static_proxy` seats = static tier; `evaluate_seated(FastDraftPolicy())` replacing the
`engine_msv` seats = dynamic tier), same board, same draws, E11's 3×3 grid, `n_seasons=4`,
**36 paired points**, seed **20260825**, CI via `rl.train.bootstrap_ci(seed=20260825)`.
The script is embedded **verbatim** in `docs/design/v5-static-dynamic.md` §8; run it as:

```sh
cd engine
PYTHONPATH="$PWD" /abs/path/to/blitzboard/pipeline/.venv/bin/python xtier.py
```

**Expected:** `[1]` shipped dynamic − static = **−23.73**, CI95 [−65.94, +18.95] ·
`[2]` `vorp_adp` − static = **−136.87** [−179.19, −94.23] ·
`[3]` E5-native `engine_msv` − static = **+82.68** [+43.11, +122.51].
Slices of [1]: `t12-…-b8` **−117.52** [−177.33, −58.75] · `t8-…-b4` +2.32 ·
`t10-2qb-ppr-b8` +44.02 · 2018 −100.19 · 2021 +42.00 · 2024 −12.99.

**Never compare absolute levels across runs — the board is zero-sum.** `static_proxy` reads 1598.2
when a weak policy holds the `engine_msv` seats and 1555.4 when the native picker does, purely
because better players fall to it. Only within-league **paired** gaps are meaningful.

Proxy anchor: `static_proxy` over `matrix.smoke()`, 2024, `n_seasons=8`, seed 20260825 = **1527.1**
(488 obs) vs real-TS **1543.6–1546.1** (= 3000 − `mae_without` from `experiments/static/results.json`).
The proxy **understates** the static tier by ~1.1 %, so [1] is conservative in the static tier's
favour. It is an anchor, not an identity — the two halves come from different league compositions.

## 8. The invariant suite (the guardrail every fit must keep green)

```sh
cd engine
../pipeline/.venv/bin/python -m pytest tests/regression/test_draft_invariants.py \
    -k "bench_positional_mix or kdst_timing"                      # 866 passed — the E10/E11 gate
BLITZ_ENGINE_FULL_SWEEP=1 ../pipeline/.venv/bin/python -m pytest \
    tests/regression/test_draft_invariants.py -k full_season      # 433 passed, ~22 s
```

Traceability map: `engine/tests/regression/README.md`. Every invariant asserts a **property**
(bench counts within E6's per-row derived bounds; K/DST caps lifting at the row's own
`kdst_timing().cap_rounds_from_end`), never a fitted literal, so moving weights cannot break them.
Engine xfail count is **0** — E8b removed E8a's bench-coverage xfail because it was FALSE (E6's
bounds give ceiling 0 for a position in 234/432 rows) and superseded it with a real upper-bound
test. `BLITZ_EVAL_FULL=1` similarly unlocks E5's 432-row matrix sweep, which **has never been run**.

## 9. What was missing when this doc was assembled

Honest gaps, so the next cycle does not mistake absence for completeness:

- **E2a's fit has no CLI.** It is two library functions; the "command" above is a REPL snippet, and
  `ParquetStore.open` is the only part not spelled out in E2a's own note.
- **E12's script lives in a doc, not the repo.** `xtier.py` is pasted verbatim into
  `v5-static-dynamic.md` §8 rather than committed under `engine/experiments/`. It was re-run from
  the pasted copy and produced bit-identical output, so it is reproducible — but it is the one
  experiment with no file to execute.
- **No experiment record exists for E1.** It is a theory doc with cited sources, not a fit.
- **`matrix.all()` (432 rows) was never simulated** by anything — E5, E6, E10 and E11 all ran
  `smoke()`'s 16 rows. Only the non-simulating invariant tests use the full grid.
