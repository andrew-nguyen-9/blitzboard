# Draft Logic Redo + Backtesting (2021–2025)

> Requirement: redo the draft logic; the autodraft hoards K/DEF and starves offense
> (QB/WR/RB/TE), and the **bench is the weakest part**. Phase **v2.4**. Depends on the
> v2.2 value upgrade.

## What's wrong in v1

The autodraft (`draftAI.ts`) picks "best available by need via VORP." Two failures:

1. **K/DEF hoarding**: with v1's over-generous K/DEF value (fixed in v2.2) and a naive
   need model, bots take kickers/defenses too early and too often, leaving startable
   offense on the board.
2. **Bench is an afterthought**: late picks default to whatever has the highest raw value —
   often a second/third K/DEF or a low-upside flier — instead of **upside offensive depth,
   bye/injury cover, and handcuffs** that actually win leagues.

## The redo — a need-and-upside draft policy

Best-pick-by-value, replaced with an objective that scores each candidate on:

```
pick_score = marginal_starter_value          # how much it raises my projected starting lineup
           + bench_value(candidate, roster)    # upside/cover value if it's a bench pick
           − positional_overfill_penalty       # diminishing returns past slot+reasonable depth
           − scarcity_adjusted_opportunity_cost # what I'd lose by not taking the run-position now
```

Key pieces:

- **Starting-lineup marginal value**: value a pick by how much it improves the *optimal
  starting lineup* (incl. FLEX/OP superflex), not raw VORP. A 3rd RB adds little to a full
  lineup; a needed QB in superflex adds a lot.
- **Bench model (the focus)**: bench slots are valued explicitly by (a) **upside** (ceiling /
  boom, not mean), (b) **handcuff/cover** correlation to your starters (RB handcuffs,
  backup QB in superflex), and (c) **bye-week and injury redundancy**. A bench pick's worth =
  expected starts × value-when-started × availability — which makes a high-ceiling WR4 beat a
  2nd kicker every time.
- **K/DEF cap**: at most one K and one D/ST until the final rounds; their compressed v2.2
  value plus an explicit late-round gate stops early hoarding.
- **Positional caps & scarcity runs**: respect league max per position; model superflex QB
  runs (opponents are QB-hungry) so the bot doesn't get left behind on QBs.
- **Opponent model**: bots draft need-aware with superflex-correct QB demand (feeds Monte
  Carlo too).

## Backtesting harness (2021–2025)

A reproducible offline harness — the core deliverable of v2.4, shared with `SCORING.md`.

1. **Data**: nflverse historical seasons 2021, 2022, 2023, 2024, 2025 (actual fantasy points
   under *our* league rules — superflex, half-PPR, distance-K, yardage-D/ST).
2. **Setup**: reconstruct each season's draft pool + realistic ADP; simulate a 12-team
   superflex snake draft with our policy vs. baselines.
3. **Baselines to beat**: v1 autodraft policy; raw-VORP; ADP-follow; "K/DEF last" heuristic.
4. **Metric**: season **points-for of the optimally-set lineup each week** (start-sit done
   greedily from actuals), plus head-to-head record vs. the field, averaged over seeds.
5. **Ablations**: turn off the predictability discount / bench-upside / K-DEF cap individually
   to confirm each helps.
6. **Output**: a tuned parameter set (`f(ρ)` exponent, bench weights, scarcity curve) and a
   report (`docs/modeling/backtest-report.md`, written when v2.4 runs).

> Note: backtests are **executed in v2.4**, not in this documentation phase. This doc
> specifies the harness, metrics, and acceptance so the work is turnkey.

## Acceptance (v2.4)

- Across 2021–2025, the v2 policy beats v1 and raw-VORP on mean season points-for and H2H
  record (report with seeds + CIs).
- Autodraft no longer takes K/DEF before the last rounds; benches are dominated by
  upside offense + cover, not duplicate K/DEF.
- Live + offline draft boards consume the same policy (thin consumers — `D7`), so manual and
  synced drafts get identical recommendations.
