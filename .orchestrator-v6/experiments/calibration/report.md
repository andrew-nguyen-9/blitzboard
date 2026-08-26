# C02 player-level calibration report

Executes the frozen, reviewer-owned manifest `player-calibration-v1.json` (never modified).
Machine-readable results: `report.json`; execution record: `promotion-v3.json`; runner:
`pipeline/calibration_run.py`. All inputs frozen before any metric was computed (hashes in
`promotion-v3.json`).

## Arms

Identical frozen inputs (players, season history, scoring, FFC ADP), identical projectors.
The ONLY difference is `models/value_engine.py` + `models/league_rules.py`:

- **v5_shipped_rating** — baseline `01f01d3c`: youth multiplier, search_rank consensus
  nudge, OP slot split equally across QB/RB/WR/TE.
- **v6_candidate_rating** — this tree: C01 deterministic corrections only. Every tuned
  constant (ELITE_PREMIUM, CLIFF_W, UPSIDE_W, DISCOUNT_K, STREAMER_PCT) is byte-identical.

The structural consequence shows up exactly where designed: superflex QB replacement rank
15 (v5) → 24 (v6); 1QB (12) and dedicated 2QB (28) identical between arms.

## Headline results (offense-only, benchmark top-150, dense-rank comparison)

| Format × benchmark | ρ v5 | ρ v6 | wErr v5 | wErr v6 | top-12 recall v5→v6 |
|---|---|---|---|---|---|
| 12-team 1QB × half-PPR ECR (112 experts) | 0.729 | 0.716 | 12.16 | 12.71 | 0.50 → 0.50 |
| 12-team 1QB × half-PPR ADP (3 platforms) | 0.697 | 0.682 | 12.08 | 12.68 | 0.58 → 0.58 |
| 12-team superflex × superflex ECR (104 experts) | 0.683 | **0.785** | 17.50 | **11.68** | 0.58 → **0.75** |
| 14-team 2QB × superflex ECR | 0.834 | 0.807 | 9.91 | 10.89 | 0.75 → 0.75 |

Unmatched top-100 rate: 0.0 on every comparison (threshold ≤ 0.02 — PASS).

## Reading

1. **The superflex replacement correction is decisively validated by the market.** The one
   format where the OP rule changes replacement is the one format with a large agreement
   gain (+0.10 ρ, −5.8 weighted error, +0.17 top-12 recall). The 2QB board uses dedicated
   QB slots (identical in both arms), so its delta cannot come from the OP rule.
2. **The 1QB/2QB declines are the age-double-count removal meeting the market's age
   preference.** Cohort tables (report.json) localize the delta: `veteran_age_30_plus`
   free-bias moves −23.9 → −26.8 (the v6 board ranks productive veterans HIGHER than
   consensus does) and rookie error rises symmetrically. v5's youth multiplier reproduced
   the market's age discount on top of a projection that already ages players — the
   double-count the independent audit ordered removed. The manifest anticipates this:
   benchmarks are references, not targets, and market agreement alone neither earns nor
   vetoes promotion.
3. **search_rank removal is invisible here** — it only shaped the negative-VOR pool, which
   sits outside every matched top-150.

## Threshold disposition (manifest `thresholds` / `failure_interpretation`)

- `deterministic_unit_failures = 0` — PASS (C01/C01A gates, independently verified).
- `unmatched_top_100_rate ≤ 0.02` — PASS everywhere.
- `spearman_delta ≥ 0` / `weighted_rank_error_delta ≤ 0` — PASS superflex; FAIL 1QB/2QB
  by small margins (Δρ ≤ 0.028). Interpretation: these thresholds gate COEFFICIENT
  promotion. No coefficient is being promoted — the arm delta is exactly the C01
  deterministic corrections, which shipped under `failure_interpretation.deterministic`
  (correctness governs, BLOCK_C01 otherwise), not under benchmark agreement. Recorded as
  `executed_report_only`; any numerical candidate still owes C05's matched-seat,
  held-out, no-regression gauntlet.

## Deviations (for reviewer adjudication)

1. ECR retrieval variant: the manifest cheatsheet URL server-renders only 24 rows; the
   print rankings page embeds the identical half-PPR draft ECR (`ecrData`, 934 rows,
   112 experts).
2. ADP rows come from the ADP page's own partners endpoint (public in-page key); its HTML
   carries a 5-row preview. Platforms recorded: Yahoo, RTSports, Sleeper.
3. Superflex ECR uses the draft cheatsheet print variant (525 rows, 104 experts).
4. The 2QB format is graded against superflex ECR — the closest public reference; no
   public 2QB-specific consensus board exists at the frozen sources.
5. Cohorts `team_change` and `low_availability` are not computable from the frozen
   snapshot (no prior-team field; `player_availability` absent from this database) and
   are reported as such rather than approximated. All other manifest cohorts are in
   `report.json`.

## Reproduction

```
python pipeline/calibration_run.py snapshot                 # (already frozen — do not re-run to verify; refetch would drift)
python pipeline/calibration_run.py boards --arm v6 --pipeline-dir pipeline
python pipeline/calibration_run.py boards --arm v5 --pipeline-dir <git archive 01f01d3c pipeline>
python pipeline/calibration_run.py report
```

Boards and report are pure functions of the committed frozen snapshot; re-running
`boards`/`report` must reproduce the recorded content hashes byte-for-byte.
