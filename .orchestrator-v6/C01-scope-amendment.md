# C01 scope amendment — player-rating deterministic correctness (2026-08-26)

Andrew expanded C01/C02 after an independently confirmed player-rating audit. C01 stays
logic/correctness only; ELITE_PREMIUM, CLIFF_W, UPSIDE_W, predictability constants, and bench
weights are NOT freely tuned. The projection-ensemble refit and all calibration reporting move to
C02 (promotion-v3.json, never overwriting v1/v2).

## C01 additions (deterministic correctness)

| # | Item | Defect (confirmed) | Correction |
|---|------|--------------------|-----------|
| A1 | Explicit unit contracts | `PlayerValue.boom` stores ceiling−replacement (`pipeline/models/value_engine.py:175`) while frontend consumes it as a raw season ceiling | projectionMean / projectionCeiling / replacement / vor / ceilingVor contracts, both sides; unit-contract tests |
| A2 | Mixed-unit comparisons prohibited | `draftAI.ceilingWeeks` compares boom (ceilingVor) against a raw marginal-starter projection | compare raw ceiling vs raw projection; direct regression tests for ceilingWeeks/benchScore |
| A3 | Superflex/2QB replacement demand | `league_rules.py` splits the OP slot equally across QB/RB/WR/TE (QB≈15 replacement in 12-team SF; realistic ≈24) | OP demand from measured QB usage (measured from the deterministic golden-draft corpus, receipt recorded), not equal allocation |
| A4 | Redraft age double-count | `_youth_factor` applies an 18% future-value multiplier after projections already age-adjust | remove the second multiplier from shaped redraft value |
| A5 | search_rank contamination | negative-VOR pool adds up to 18 pts of Sleeper search popularity as "consensus" | search_rank removed from shaped value; search/display metadata only |
| A6 | Test coverage | — | rookie, productive-veteran, missing-ADP, negative-VOR, superflex-QB, unit-contract tests |
| A7 | Original C01 scope | — | bye-coverage + contingent-role requirements preserved (already implemented this checkpoint) |

## Deferred to C02 (explicitly NOT in C01)

Calibration report vs frozen half-PPR + superflex ECR/ADP benchmarks (Spearman, weighted rank
error, top-N recall, positional bias, cohort errors, outliers); per-player rank decomposition;
held-out + season-evaluator no-regression evidence before any coefficient promotion;
promotion-v3.json.
