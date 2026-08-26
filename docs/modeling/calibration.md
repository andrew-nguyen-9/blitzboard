# Reliability / Calibration of the projection distributions (v2.2.3)

Companion to `SCORING.md` ("Validation" → calibration check) and `VALUE_ENGINE.md`
(`MonteCarloEngine`). Code: `pipeline/models/calibration.py` (metric),
`pipeline/calibration_check.py` (runnable demonstration), `pipeline/tests/test_calibration.py`.

## Why this exists

The v1 bug (`SCORING.md` §research) is that the projector **overestimates busts and
underestimates booms** — a point projection treats a volatile D/ST like a stable WR.
v2.2.3 fixes the *shape* of the distribution: Monte Carlo samples a σ widened by low
predictability (`1 + MC_VOL_GAIN·(1−ρ)`), so volatile players get correctly wide
boom/bust. This doc is how we *check* the fix did the right thing rather than just
making every range wider.

## The method — Probability Integral Transform (PIT)

For a Normal forecast `N(μ,σ)` and a realized outcome `r`, the PIT is `Φ((r−μ)/σ)` —
the predicted percentile the outcome landed in. A **calibrated** forecaster yields PIT
values that are `Uniform(0,1)`: ~10% of outcomes below the predicted 10th percentile,
~10% above the 90th, and so on. Miscalibration is visible in the shape:

- **U-shape** (mass piling at 0 and 1) → *overconfident*: σ too small, booms/busts
  underestimated. This is the v1 signature.
- **∩-shape** (mass bunched in the middle) → *underconfident*: σ too wide.

`calibration_error` is the Kolmogorov–Smirnov distance from uniform (0 = perfect).

## Result

`python calibration_check.py` synthesizes a world where low-ρ players are *truly* more
volatile than the base σ admits, then compares the naive forecaster (base σ for
everyone) against the predictability-aware one on the same realized outcomes:

```
naive (base σ for everyone)      error=0.084   ← U-shaped (17% / 16% in the tail bins)
predictability-aware σ           error=0.026   ← flat (~10% per bin)

volatile cohort (ρ<0.4):  naive 0.120 → aware 0.036
```

The aware model flattens the reliability diagram, and the improvement concentrates in
exactly the cohort the fix targets (low-ρ K/DEF and boom/bust skill players). The true
volatility gain in the synthetic world (0.7) deliberately differs from the model's
`MC_VOL_GAIN` (0.6), so the gain is directional, not a fit-to-self.

## Tuning & real data

- `MC_VOL_GAIN` (`models/value_engine.py`) is the σ-widening knob. **Its stated provenance is
  falsified as of v5 (2026-08-25):** it was said to be "set by the 2021–2025 backtest
  (`DRAFT_LOGIC.md`, v2.4.3)", but that backtest's metric is **retired** — see
  `docs/modeling/backtest-report.md` §Superseded. A perfect-hindsight weekly-optimal lineup is
  blind to distribution *shape* (you start whoever actually scored, so a wide σ changes nothing),
  so it could not have set this knob's value in any meaningful sense. **`MC_VOL_GAIN` = 0.6 is
  currently an unvalidated hand-authored number.** It was not re-fitted in v5 (out of scope — v5
  fitted the draft policy, not the projector) and it is an open v6 item.
- To run the check against **real** outcomes, feed `pit_values(means, eff_stdevs,
  realized)` the emitted season projections (`projections.mean`, the MC effective σ)
  and the realized season points from `player_stats_history`, then read off
  `reliability_table` / `calibration_error`. The synthetic harness remains the offline stand-in for
  the **projector**; it is no longer the only real-data calibration in the repo (see below).

---

## v5 update (2026-08-25) — a second, real-data calibration gate now exists

This doc covers the **projection distributions** (pipeline tier, synthetic harness). v5 added an
independent calibration gate on the **injury hazard model** (engine tier), and unlike the above it
runs **on real data**, not a synthetic world:

```sh
cd engine
../pipeline/.venv/bin/python -m blitz_engine.survival.hazard \
    --data-root ~/.blitz_engine --seed 7 --out fixtures/injury_rates.json
```

**Result: `[PASS] cal_err=0.055 log_loss=2.439 crps=1.661 sharpness=2.901 discrimination=0.958
top12=0.83 (n=180)`** — threshold 0.10, hold-out 2024–25, overdispersion 1.63. The CLI exits 1 if
the gate blocks.

**The gate behaved the way a gate is supposed to.** It **blocked twice** on the way — at 0.283 and
then 0.110 — and **both were real defects, fixed; neither threshold was tuned around.** The three
bugs it forced out are the point of keeping this note:

1. **Offseason leakage.** Recurrence covariates (`recent_injury` / `injury_history`) were keyed on
   the player, not the player-**season**, so a December IR stint set week-1 hazard nine months
   later — a **4.4σ** over-prediction and the single largest calibration error in the fit.
2. **Unbounded latent durations.** The censored negative-binomial `DurationModel` reported means of
   **10–26 games missed inside a 17-game season**. Now truncated at `GAMES_PER_SEASON`.
3. **A structural zero.** `weeks_since_return` was unlagged, so `out == 1` was impossible at every
   `k > 0` — the entire re-injury fit was identically zero while *looking* fitted. Lagged; measured
   re-injury elevation is now **0.616**, decaying over 8 weeks.

All three were **invisible under the previous event definition** (a snap-presence proxy). Fixing
*what is being predicted* is what made the calibration diagnostics informative — the same lesson as
`backtest-report.md` §Superseded, one layer down.

### Two lessons this doc should carry forward

- **A calibration number is only as meaningful as the event it scores.** The pre-refit fit was
  "calibrated" against unavailability and would have passed happily while measuring the wrong
  quantity. Publish the event definition next to the metric: `fixtures/injury_rates.json` now
  carries an explicit `"event"` string, and a test in `engine/tests/test_feasibility.py` asserts it
  so a silent revert fails loudly.
- **Known residual, disclosed rather than smoothed:** week-1 absences are under-predicted (~8
  predicted vs ~22 actual WRs) because training-camp injuries have no preseason exposure anywhere
  in the store. It survives the gate and biases the published rate very slightly low. Documented in
  the module docstring.

See `docs/modeling/experiments.md` §1 for the full reproduction, and
`docs/decisions/2026-08-25-v5-perfect-the-draft.md` §5 for the data traps behind the event
redefinition.
