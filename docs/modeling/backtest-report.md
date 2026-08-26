# v2.4 Backtest Report — **SUPERSEDED (v5, 2026-08-25)**

> **This report's METRIC is retired. Do not tune against it and do not cite its ablation Δs as
> evidence about bench value.**
>
> The current metric is `SeasonEvalResult.started_points` — see **`docs/modeling/draft-eval.md`**.
> The numbers below are kept as history; §Superseded at the bottom says exactly what was wrong and
> what replaced it. The **marginal-starter-value** finding (§Reading) still stands; the
> **"`DEFAULT_POLICY` is left unchanged"** verdict does not — it was re-tested properly in v5 and
> the reasoning behind it has been replaced by measurement.

Seasons [2021, 2022, 2023, 2024] · 4 seeds/season · 12-team superflex (Smores rules). Means with bootstrap 95% CIs. Higher is better on both metrics.

## Policy vs. baselines

| policy | season points-for | H2H win% |
|--------|-------------------|----------|
| **v2 (additive)** | 2176 (2148–2203) | 50.0% (48.2–51.8) |
| raw-VORP | 1800 (1761–1840) | 50.0% (47.3–52.7) |
| ADP-follow | 2069 (2040–2096) | 50.0% (47.9–52.0) |

v2 **beats** both baselines on mean season points-for.

## Ablations (v2 with one component removed)

| ablation | season points-for | H2H win% | Δ points vs v2 |
|----------|-------------------|----------|----------------|
| no-kdef-cap | 2176 (2148–2203) | 50.0% (48.2–51.8) | +0 |
| no-bench-ceiling | 2182 (2156–2208) | 50.0% (48.2–51.8) | +6 |
| no-bench-injury | 2192 (2164–2220) | 50.0% (48.1–51.8) | +16 |
| naive-replacement | 2175 (2147–2203) | 50.0% (48.1–51.9) | -1 |

A negative Δ means the full policy is better with that component — it earns its place.

## Metric notes (historical — see §Superseded)

- **Season points-for** is the discriminating metric. **H2H win% is ~50% on every row by construction** — the harness runs all 12 teams on the *same* policy, so "vs the field" is symmetric. A true policy-vs-policy H2H needs *mixed-policy* drafts (harness follow-up).
- Points-for scores a **perfect-hindsight** weekly-optimal lineup, which structurally under-values bench insurance (injury cover, ceiling stashes): you "start whoever actually scored," so depth pays off less than in a real imperfect-information season. A neutral or positive ablation Δ on a bench term does **not** prove the term is useless — only that this metric cannot see its value. Bench terms are kept for real-season robustness and revisited under a mixed-draft / injury-aware eval.

## Reading (historical — see §Superseded)

The **marginal-starter-value core** is what beats the baselines: v2's +376 over raw-VORP and +107 over ADP-follow come from valuing each pick by how much it raises the *optimal starting lineup* against the replacement still available, not by raw VOR or ADP. The K/DEF cap and bench terms are neutral-to-slightly-negative on this hindsight metric — expected, since it can't price insurance — so `DEFAULT_POLICY` is **left unchanged** rather than overfit to a metric blind to bench value. Reproduce: `python -m backtest.tune --seasons 2021 2022 2023 2024 --seeds 4` (add `--grid` for the param sweep).

---

## Superseded — what v5 changed and why (2026-08-25)

### What was wrong

The §Metric notes above were **honest and correct about the metric, and that was the problem.**
The report correctly identified that a perfect-hindsight weekly-optimal lineup is structurally
blind to bench insurance — and then drew a conclusion *from* that blind metric anyway: bench terms
were kept because the metric "cannot see their value", and `DEFAULT_POLICY` was **left unchanged**
rather than fitted. That is not a null result. It is **no result**, reported as a decision.

Two specific defects:

1. **The metric could not see a real effect.** Measured directly in v5 on the *same two rosters*:
   a bench-insurance ablation moves the new metric **+19.5 pts/season, p=0.0055**, while
   `hindsight_points` scores it **+43.9, p=0.2295 — not significant.** Command:
   `(cd engine && ../pipeline/.venv/bin/python -m pytest tests/test_league_sim.py -k bench_insurance)`.
2. **H2H win% was 50.0 % on every row *by construction*.** The harness ran all 12 teams on the
   same policy, so "vs the field" is symmetric. The report says this; it is repeated here because
   the table above still shows twelve 50.0 % cells and they mean nothing. v5 fixed it with
   mixed-policy seats (`DEFAULT_POLICY_MIX`): engine_msv .59 / static_proxy .52 / vorp_adp .39.

### What replaced it

`blitz_engine.simulation.season_eval.SeasonEvalResult.started_points` — the points a **locked**
lineup actually scored, per seat, under sampled availability × clinical injury × byes × contested
waivers, leakage-guarded every week by `detect_leakage`. Full specification, limitations and the
acceptance test: **`docs/modeling/draft-eval.md`**.

`hindsight_points(players, rosters, row)` is retained in `season_eval.py` **solely** to reproduce
the contrast above. Never tune against it.

### What actually happened when `DEFAULT_POLICY` was re-tested properly

The "left unchanged" verdict was replaced by a real fit. `frontend/lib/draftAI.ts` and
`benchScore.ts` were driven unmodified over a node bridge and six candidates were gated against
`started_points` at seed 20260825, `n_seasons=8`, 16 `matrix.smoke()` rows, n=1176:

**Zero weight values changed — but for a different reason than in v2.4.** Not "the metric can't
see it", but "each candidate was measured and none cleared block-release":
`byeStack_conditional` −10.44 (no_regression FAIL) · `byeStack_off` −9.03 (FAIL) ·
`sf_multiplier_rb` +1.20 (p=.545) · `trade_value_zero` +5.34 fit-slice **helps** → **−1.08
neutral on held-out 2021** · `injury_rate_clinical` **−13.97, HURTS, p=.0015** ·
`kdst_soft_penalty_e6` +2.08 (p=.673). The dynamic tier fared worse: both arms returned CI95
intervals **entirely below zero** (−60.2 and −26.7 pts/season).

Full tables, seeds and commands: `docs/modeling/experiments.md`.
Interpretation and the cycle's decisions: `docs/decisions/2026-08-25-v5-perfect-the-draft.md`.

### The old reproduce line

`python -m backtest.tune --seasons 2021 2022 2023 2024 --seeds 4` refers to the v2 pipeline-era
harness layout and is **not** the v5 reproduction path. Use the commands in
`docs/modeling/experiments.md` §5–§6.
