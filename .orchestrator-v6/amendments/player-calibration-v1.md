# v6 amendment — player rating correctness and calibration

Authorized after C00 because independent user tests found widespread player-rating errors. This
amendment adds requirements to C01 and C02 without weakening or replacing their original scope.

## C01 additions — deterministic value correctness

1. Replace ambiguous `boom`/`bust` use with explicit semantic fields or types for raw projection
   mean/ceiling/floor, positional replacement, mean VOR, and ceiling/floor VOR. A raw projection
   may never be compared with a replacement-adjusted value.
2. Consolidate the TypeScript consumers on that contract. In particular, a candidate whose raw
   ceiling exceeds a starter must not lose all ceiling-week credit merely because stored `boom`
   was reduced by replacement.
3. Derive superflex/2QB QB replacement demand from authoritative or measured lineup usage. Equal
   division of an OP slot among QB/RB/WR/TE is not acceptable evidence. Conservative fallback must
   be explicit and format-specific.
4. Redraft age may affect the forecast of this season's production once. A separate dynasty/future
   value multiplier must be inert in seasonal redraft.
5. Sleeper `search_rank` is search/display metadata, not expert consensus or ADP, and must not alter
   player value. Missing ADP degrades explicitly rather than substituting search popularity.
6. Preserve original C01 candidate-aware coverage and contingent-role requirements. Numerical
   fitting of elite/cliff/upside/predictability/bench coefficients remains excluded.

Independent evidence includes raw-versus-VOR ceiling, redraft age double-counting, search-rank
contamination, superflex replacement, rookie/missing-ADP, veteran, and cohort invariants.

## C02 additions — player-level calibration gate

1. Freeze pre-correction and candidate boards with every component needed to reproduce rank.
2. Compare separately against current half-PPR expert consensus, half-PPR multi-platform ADP,
   superflex expert consensus/ADP, and positional ranks. Benchmarks are references, not targets.
3. Report Spearman rank correlation, weighted absolute rank error, top-12/24/50 recall, positional
   median bias, and the largest player-level outliers. Report rookie, veteran, injury, team-change,
   missing-ADP, missing-depth, and low-availability cohorts separately.
4. Decompose each ranking into raw projection, replacement, VOR, elite, cliff, upside,
   predictability, age, consensus/market, availability, and downstream policy adjustments.
5. Any coefficient change requires a versioned preregistration, held-out historical validation,
   current-board benchmark improvement, and the existing leakage-safe season-evaluator
   no-regression gate. Market agreement alone never earns promotion.
6. Do not ingest or commit restricted/purchased ranking data. Record source date, format, permitted
   derived fields, matching failures, and immutable input hashes for every executed benchmark.

## Gate effect

C01 cannot pass with a value-unit mismatch, search-popularity value input, double age adjustment,
or unsupported superflex replacement baseline. C02 cannot pass without a reproducible player-level
calibration report and cohort evidence. Failed/inconclusive coefficients preserve shipped values.
