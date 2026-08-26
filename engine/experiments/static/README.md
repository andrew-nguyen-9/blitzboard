# e10 — static-tier weight fit (`draftAI.ts` + `benchScore.ts`)

**Headline: ZERO weight values changed. Six candidates were gated; none cleared block-release.**
That is the deliverable. Every negative below is a measured result with a re-runnable command,
not an omission — an unproven weight is worse than no weight.

## What is scored

`blitz_engine.simulation.season_eval.SeasonEvalResult.started_points` (e5's metric): the points a
**locked** starting lineup actually scored, per seat, over the corpus season's regular weeks, under
sampled availability + injury + byes + contested waivers, leakage-guarded by `detect_leakage`.
Higher is better. The retired hindsight metric is never touched, and no side metric exists.

## How the real policy is driven (v5-architecture §5)

`engine/blitz_engine/backtest/static_fit.py` → `frontend/scripts/draft-eval.mjs` → the *unmodified*
`lib/draftAI.ts` + `lib/benchScore.ts`. **e5's `static_proxy` Python stand-in is not used anywhere
in this unit** — that swap was e10's named handoff and it is done. One node process per *batch* of
drafts (never per pick; per-batch because the tsx compile would otherwise dominate at ~1 s vs
~0.5 s/draft). `benchScore`'s tables are module consts with no injection seam, so the bridge
mutates-and-restores them around each draft.

## Method

**Mirrored half-league ablation**, e6's construct reused verbatim. Both arms sit in the SAME snake
draft (seats alternate A/B); a second draft swaps every seat's arm. Seat *t*'s paired difference
`A(t) − B(t)` therefore cancels the draft-slot effect. One observation per (sampled season, seat).
Search: **exhaustive gate over a hand-enumerated candidate set**, not a free search — every
candidate is a specific upstream-derived hypothesis, so there is nothing to overfit and no
zero-gradient knob gets a confident number. Seed `20260825` (= e5 `SEASON_EVAL_SEED` = e7b
`GOLDEN_SEED`), `n_seasons=8`, all 16 `matrix.smoke()` rows, corpus season 2024 → n_obs = 1176.

The DoD gates in `backtest/ablation.py` are MAE-shaped (lower better) and the metric is points
(higher better), so each arm is presented as a **shortfall** predictor `CEILING − started_points`
against an actual of 0. MAE is then a strictly decreasing affine function of the metric, so
`ablation()`'s verdict and `no_regression()`'s tolerance keep their published meaning. Neither
`ablation.py` nor `harness.py` nor the simulator was modified. `no_regression` runs at
`tolerance=0.0` — a shipped weight must be no worse than the incumbent, not merely within 2 %.

## Reproduce

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.backtest.static_fit --all --seasons 8   # -> results.json
../pipeline/.venv/bin/python -m blitz_engine.backtest.static_fit \
    --only trade_value_zero --seasons 8 --season 2021 --seed 20260826 \
    --out experiments/static/holdout-2021.json                                       # -> holdout
```

(In a linked worktree: absolute venv path, and `PYTHONPATH=<worktree>/engine`. Run `npm ci` in
`frontend/` first — the bridge needs `node_modules/.bin/tsx`.)

## Verdicts — `results.json` (2024 fit slice, seed 20260825, n=1176)

| exp id | change tested | Δ started pts | verdict | p | no_regression | ships |
|---|---|---|---|---|---|---|
| `byeStack_conditional` | `>=7` bench slots ⇒ −12 (cluster bonus), else 18 | −10.44 | neutral | 0.0525 | FAIL | no |
| `byeStack_off` | `byeStackPenalty: 0` | −9.03 | neutral | 0.1175 | FAIL | no |
| `sf_multiplier_rb` | `SF_MULTIPLIER.RB 1.2 → 0.67` | +1.20 | neutral | 0.5445 | pass | no |
| `trade_value_zero` | SF RB/WR `TradeValue 10 → 0` | +5.34 | **helps** | 0.0205 | pass | cleared here, then failed held-out |
| `injury_rate_clinical` | `injuryRate` ← e3 clinical rates | −13.97 | **hurts** | 0.0015 | FAIL | no |
| `kdst_soft_penalty_e6` | `kdstSoftPenalty 20 → 4.06` (cap 2 unchanged) | +2.08 | neutral | 0.6730 | pass | no |

## Held-out — `holdout-2021.json` (corpus 2021, seed 20260826)

`trade_value_zero`: **−1.08 pts, neutral, p=0.4025, no_regression FAIL.** The only candidate that
cleared the fit slice does not replicate. Sign-flipping across slices is the exact signature e6's
P11 predicted **structurally**: e5 simulates no trades, so `TradeValue` has zero gradient under
`started_points` and the fit-slice "helps" was noise. It is therefore **pinned, not fitted**, with
an in-code comment forbidding any future free-fit. Ablating it would have been equally defensible;
pinning was chosen because ablation could not be *proven* either.

## Notes carried forward

- e6's RB/WR asymmetry was respected: only RB was proposed for correction, WR's 1.1 was never
  touched. The RB correction is *directionally* right per e6 and simply invisible to this metric.
- `injuryRate` is the one candidate the metric actively rejects. Read `fixtures/injury_rates.json`'s
  `event` string before ever proposing this again — it is clinical incidence, not availability.
- The bench-depth seam (`byeStackDeepBenchSlots` / `byeStackPenaltyDeepBench`) ships **inert**
  (values chosen so behaviour is bit-identical to e1's flat 12); it exists so e12 can re-test the
  conditional form without re-deriving the mechanism.
- Because no weight value moved, e7b's golden drafts are **byte-identical** and were not
  regenerated (`gen-golden-drafts.mjs --check` is the proof).
