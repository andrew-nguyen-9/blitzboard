# C02-claude — evaluator realism + player-level calibration (amended scope)

## Identity

- base: `b81541c226dd5aeeacbe9ed79df927853a4b8954` (C01A, independent PASS at review
  commit `2be8a22`), integration record `13ec3c2`
- branch: `v6/bench-portfolio`; head = the commit containing this file
- scope: wishlist C02 (evaluator realism) + the C02 half of the 2026-08-26 player-rating
  amendment (player-level calibration gate, `player-calibration-v1.json` — the frozen,
  reviewer-owned manifest, executed and NEVER modified)
- excluded: any coefficient change (none attempted — see calibration disposition), C03
  bench-portfolio work, integration of this checkpoint (blocked until independent PASS)
- git identity: Andrew; no assistant attribution; date 2026-08-26

## Half A — evaluator realism (`engine/blitz_engine/simulation/season_eval.py`)

### What changed

1. **Bounded point-in-time proactive waivers.** `_run_waivers` now runs two claim kinds,
   both reading ONLY the believed projection built from observed weeks (time-honest by
   construction) and both charged against a per-team season cap (`season_moves_cap`):
   - EMERGENCY (existing, ≤ `waiver_moves_per_week`): an unfillable starting slot claims
     the best free agent at the missing position.
   - UPSIDE (new, ≤ `proactive_moves_per_week`): the (drop, add) swap with the largest
     believed edge over the team's worst same-position body, gated by `upgrade_margin`
     (default 0.15). A started body may be replaced — which is exactly K/DST streaming
     when a position carries one body; no special case exists.
   Priority stays reverse-standings; the pool stays ONE shared list, so contested claims
   are real. FAAB game theory, trades, and speculative stashes remain deliberately out
   (contract exclusions).
2. **Transaction costs.** `waiver_cost` (points per successful claim) is charged at
   season aggregation into `per_season`/`started_points`. Weekly H2H results are decided
   on the field and are untouched — documented in the config.
3. **Emergency/upside distinction.** `SeasonEvalResult.emergency_adds` / `upside_adds`
   (`waiver_adds` = their sum, backward compatible), also in `by_policy()`.
4. **Paired outcome families.** New per-season sample arrays: `per_season_h2h`,
   `per_season_playoff`, `per_season_champ` (+ `playoff_rate`/`champ_rate` means).
   Playoff proxy = top `playoff_slots` seats by (wins, season points); championship
   proxy = highest-scoring playoff seat — the corpus has no bracket weeks, and the
   proxy is documented as such. `paired_ci(a, b, seats, field)` returns
   {mean, lo, hi, n} normal-approx CI95 over per-season paired deltas for any of the
   four families; `paired_effect` unchanged.
5. **Determinism & leakage.** All new logic is driven by the existing seed streams and
   deterministic tie-breaks; `detect_leakage` still runs on every week's decision frame
   and the `leak` test hook still trips it under the realism path.

Defaults: realism ON (`proactive_moves_per_week=1`, `upgrade_margin=0.15`,
`season_moves_cap=25`, `waiver_cost=0.0`, `playoff_slots=4`). Every pre-existing
evaluator acceptance property was re-run under these defaults and held — including THE
bench-insurance contrast (`test_bench_insurance_moves_the_new_metric_and_not_hindsight`)
and the mixed-policy H2H non-degeneracy test.

### Production-side tests (`engine/tests/test_waiver_realism.py`, 11 tests)

Stale-bench upgrade is an upside claim; upgrade margin bounds churn; contested single
prize goes to the worse record; K/DST streams through the same upgrade rule (realism-on
strictly outscores realism-off); transaction cost charged exactly per claim; season cap
0/1 is a hard bound; emergency and upside counters are distinct; full-path seed
determinism across all nine result arrays (real availability model, no monkeypatch);
playoff/champ proxy invariants (exactly N playoff seats, exactly one champion, champ ⊆
playoff, means reconcile); `paired_ci` shape/order; leak guard live.

## Half B — player-level calibration (manifest `player-calibration-v1.json`, executed)

Runner: `pipeline/calibration_run.py` (snapshot | boards | report). Everything frozen
BEFORE metrics: Supabase players (4265) + season history (1682) + scoring + FFC ADP per
league size; three FantasyPros benchmarks (derived fields only; raw HTML in uncommitted
`artifacts/calibration/`, sha256 recorded). Committed artifacts in
`.orchestrator-v6/experiments/calibration/`: `snapshot.json.gz`, `benchmarks.json.gz`,
`boards-v5.json.gz`, `boards-v6.json.gz`, `report.json`, `report.md`,
`promotion-v3.json` (v1/v2 untouched).

- Arms: v5 = full baseline pipeline tree at `01f01d3c` (git archive); v6 = this tree.
  Identical frozen inputs and projectors; the arms differ ONLY in
  `models/{value_engine,league_rules}.py`. Verified structural signature: superflex QB
  replacement rank 15 → 24; 1QB (12) and dedicated 2QB (28) identical.
- Boards carry every manifest component field per player (projection mean/ceiling,
  replacement, vor, ceiling_vor, elite, cliff, upside, predictability discount, age,
  market ADP, v5-only youth/consensus; availability and policy_adjustment recorded as
  null-by-design with reasons). Boards are a pure function of the frozen snapshot —
  re-running reproduces the recorded content hashes byte-for-byte (verified twice).
- Results (offense-only, top-150, dense-rank): superflex ρ 0.683→0.785, weighted error
  17.50→11.68, top-12 recall 0.58→0.75 (the OP correction, market-validated). 1QB/2QB
  decline slightly (Δρ ≤ 0.028), localized by cohort tables to veteran_age_30_plus /
  rookie — the removed age double-count no longer reproduces the market's age discount.
  Unmatched top-100 rate 0.0 everywhere (threshold ≤ 0.02).
- Disposition (`promotion-v3.json`): `executed_report_only`. NO coefficient promotion
  attempted; no tuned constant differs between arms. Benchmark thresholds gate
  coefficient promotion, and per the manifest benchmarks are references, not targets;
  the deterministic corrections stand on the C01/C01A correctness gate. C05 remains the
  promotion authority.
- Deviations recorded for reviewer adjudication (also in report.md): ECR/superflex print
  retrieval variants (manifest URLs server-render partial tables), ADP rows from the
  page's own partners endpoint (public in-page key; platforms Yahoo/RTSports/Sleeper),
  2QB graded against superflex ECR (closest public reference), cohorts `team_change` and
  `low_availability` not computable from the frozen snapshot (reported as such, never
  approximated).

## promotion-v3 version collision (coordination report, per Andrew's 2026-08-26 instruction)

Two files named `promotion-v3.json` now exist, at distinct paths; neither has been
renamed, overwritten, or deleted:

- **C05 preparation (first-committed):** `.orchestrator-v6/experiments/promotion-v3.json`
  on `v6/c05-prep`, commit `82b7705038a6fd420517bfadb77dea5357660927`, SHA-256
  `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab` — the frozen C05
  promotion preregistration. This checkpoint REFERENCES it as the promotion authority
  (its candidate SHA stays null until C02/C03/C04 pass).
- **This checkpoint (later):** `.orchestrator-v6/experiments/calibration/promotion-v3.json`,
  SHA-256 `368657acb9ff17d086bf94854d63ce38604959e121486dc7751a0e668a692829`, committed
  in the C02 commit containing this file — the EXECUTED calibration record
  (`executed_report_only`), not a preregistration.

Per the coordination instruction, integration preserves the first v3 (C05's) and
renumbers this checkpoint's later-integrated record to v4 with an explicit append-only
amendment; every in-document reference here to "promotion-v3.json" for the calibration
record should then be read as the renumbered v4. The reviewer-owned
`player-calibration-v1.json` and its amendment were never copied or modified.

## Coefficients — none tuned

Engine: no constant changed; new `EvalConfig` fields are evaluator-realism structure
with documented defaults, not fitted values. Pipeline: value-shaping constants untouched
(the calibration compares code already landed in C01 against baseline). Frontend:
untouched this checkpoint.

## Verification (this worktree)

- engine: ruff clean on changed files; full pytest —
  **4134 passed, 1 skipped** (worktree PYTHONPATH form; includes the 11 new realism
  tests and all pre-C02 acceptance properties under realism-on defaults).
- pipeline: **157 passed** (calibration runner is tooling; no pipeline test touches it);
  jax/torch-free preserved (calibration_run imports only stdlib + requests + numpy +
  the existing models package).
- frontend: unchanged in C02 — typecheck clean, lint carries only the pre-existing
  `useEspnSync.ts` warning, **492 passed**.
- `git diff --check` clean; reviewer worktree untouched; no push/merge/PR/release.

## Stop

C02 is recorded and NOT integrated. Next action: independent C02 review; integration
and C03 remain blocked until PASS.
