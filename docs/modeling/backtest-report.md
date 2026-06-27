# v2.4 Backtest Report

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

## Metric notes

- **Season points-for** is the discriminating metric. **H2H win% is ~50% on every row by construction** — the harness runs all 12 teams on the *same* policy, so "vs the field" is symmetric. A true policy-vs-policy H2H needs *mixed-policy* drafts (harness follow-up).
- Points-for scores a **perfect-hindsight** weekly-optimal lineup, which structurally under-values bench insurance (injury cover, ceiling stashes): you "start whoever actually scored," so depth pays off less than in a real imperfect-information season. A neutral or positive ablation Δ on a bench term does **not** prove the term is useless — only that this metric cannot see its value. Bench terms are kept for real-season robustness and revisited under a mixed-draft / injury-aware eval.

## Reading

The **marginal-starter-value core** is what beats the baselines: v2's +376 over raw-VORP and +107 over ADP-follow come from valuing each pick by how much it raises the *optimal starting lineup* against the replacement still available, not by raw VOR or ADP. The K/DEF cap and bench terms are neutral-to-slightly-negative on this hindsight metric — expected, since it can't price insurance — so `DEFAULT_POLICY` is **left unchanged** rather than overfit to a metric blind to bench value. Reproduce: `python -m backtest.tune --seasons 2021 2022 2023 2024 --seeds 4` (add `--grid` for the param sweep).
