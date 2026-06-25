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

- `MC_VOL_GAIN` (`models/value_engine.py`) is the σ-widening knob; its final value is
  set by the **2021–2025 backtest** (`DRAFT_LOGIC.md`, v2.4.3), not hand-tuned here.
- To run the check against **real** outcomes, feed `pit_values(means, eff_stdevs,
  realized)` the emitted season projections (`projections.mean`, the MC effective σ)
  and the realized season points from `player_stats_history`, then read off
  `reliability_table` / `calibration_error`. The synthetic harness is the offline
  stand-in until a full season of v2 projections has a realized season to grade against.
