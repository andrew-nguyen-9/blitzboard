# Decisions — v4 quant-engine cycle (2026-07-14)

Harvested from the `v4-quant-engine` orchestrating cycle (30 units + 4 D-phase fixes,
PR #105 → main @ 8544004). One line per unit's load-bearing decision; the `.orchestrator/`
scratch these came from is not retained (git history is the archive). Gotchas that recur
across units are collected at the end.

## E0 — foundation

- **scaffold**: `blitz_engine/{config,store/,snapshot/,registry/,cli.py,pipeline_bridge.py}`; engine editable-installed into the shared `pipeline/.venv` (`pip install -e engine --no-deps`). Snapshot version is FROZEN-EARLY / ADDITIVE-ONLY; raw draws never enter the compact export.
- **ingest**: `from blitz_engine.data.ingest import ingest_all, ingest_source`; `data.validation.gate(store, DEFAULT_SPECS)` runs FIRST and raises `ValidationError` on any anomaly (schema/row-count/key-uniqueness/provenance/freshness) → BLOCKS. `validate()` = non-raising report. Provenance is column-based, not a side table.
- **sources**: shared `EngineSource` mirrors the pipeline adapter degrade contract but writes via `ParquetStore.write_parquet` (not Supabase). `run(store, raw=None)` skips network when `raw` supplied (tests). `vegas_odds` reuses the pipeline `OddsAdapter`, redirecting only the write.
- **survey**: STORAGE = adopt **Cloudflare R2** for the published snapshot/CDN (zero egress, S3-compatible); Supabase kept for the relational/live tier; raw history + posterior draws stay LOCAL (Parquet+DuckDB). COMPUTE = local M1/16GB default; cloud-burst opt-in only. Burst path = CLI emits a self-contained notebook + Parquet manifest → run on Kaggle (primary) or Colab (fallback) → result re-enters the local store. Burst is compute-only, never a store.

## E1 — projection

- **core**: `HierarchicalProjector(config, *, priors, scoring, factors=(), latent=None, talent_prior=None, ...)`; `.fit(...) -> ConvergenceReport` (raises `ConvergenceError` = the PUBLISH BLOCK); `.predict()/.project()`. Two-stage: opportunity (NegBin, Dirichlet share × team_plays) → efficiency conditions on observed opp when fitting, expected opp when `predictive=True`. Raw draws → local Parquet only; quantiles → Snapshot. NUTS `chain_method='sequential'`, `init_to_median` (M1). Real fits marginal at 300–400 draws (r-hat ~1.02) — publish needs more warmup or `target_accept 0.95`.
- **factors**: 7 pure per-player factors on the `FactorHook` seam, clamped to `FACTOR_BOUNDS=(0.5,2.0)`, context-free player → 1.0. Seam moves opportunity MEAN only.
- **latents**: four latents additive on log scale; all feed efficiency, only position-differential parts feed opportunity (team-constant opportunity latent cancels in the Dirichlet share — dropped as unidentifiable). Closed-form empirical-Bayes shrinkage, no optimizer.
- **talent**: `TalentModel.fit(history, *, draft=None, ...)` is a drop-in `TalentPriorHook`; shifts ONLY the opportunity prior, neutral elsewhere. Layers: GP career arc + scalar Kalman in-season nudge + per-position aging quadratics + Gaussian-HMM regime. CFBD-absent → college layer skipped, wide scale, no crash.
- **sentiment-vegas**: `SentimentPrior(...)` implements `TalentPriorHook`; composes OVER an optional base talent hook via `base=`. `resolve_scorer(prefer_transformer=True)` → HF transformer else VADER. Only ONE `talent_prior` slot — SentimentPrior + TalentModel must compose at wiring time.

## E2 — availability

- **survival**: `DiscreteTimeHazard().fit(history).predict_available(frame)` = discrete-time logistic hazard (scipy L-BFGS, no lifelines). `AvailabilityModel.p_available(...)` fuses hazard ∘ status ∘ suspension (precedence suspension > status > model). `apply_availability(projection, p_map)` scales quantiles + redistributes Dirichlet shares (α' = α·P, within-team renorm). Every `p_map` lookup defaults 1.0 (missing player = no-op).

## E3 — simulation

- **mc-core**: `simulate(marginals, players, *, corr, spec, config, adp)` / `simulate_projection(projection, ...)`. Marginals = Gaussian(mean, stdev) clipped at 0 (projection- and calibration-preserving). Scale knob = `SimConfig.n_runs` (10k interactive → 1M publish). Streaming reduction: draws batch → integer counters → freed; peak memory independent of `n_runs`. `cloud_burst_suggested=True` only when even `min_batch` won't fit (opt-in; run still completes locally).
- **league-sim**: base fantasy-schedule SOS is self-contained; latent-defense SOS is the optional `difficulty` hook, not a hard dep. Exposes `p_champion()` + `strength_of_schedule()`.

## E4 — draft policy & value

- **value-equity**: draft objective = Δ P(win league). Offline `championship_equity(...)` re-sims E3. LIVE (no sim): `live_draft_value(players_by_position, opponent_field, *, sensitivity=1.0) -> LiveBoard`. Player VALUE units = points·wk⁻¹ (VORP).
- **mcts-policy / rl-policy**: `FastDraftPolicy.pick/pick_live` is the live surface (E8 reads it). Callers MUST pass `positions:{pid→pos}` (LiveBoard carries no position column). Backtest gate = bootstrap-CI-clears-0, not per-seed domination. RL is pure torch (sklearn absent from the venv).
- **D-phase fixes (F1–F4)**: `team-reconcile` (pure-stdlib team assignment, thresholds `MAX_UNASSIGNED_FRAC`/`MAX_MISMATCH_FRAC`); `roster-solver` (combined selection+assignment in ONE CP-SAT, ortools); `fa-penalty` (truly-FA = falsy team AND `has_news is False` → 0.02 haircut + rebase whole FA band below every non-FA, order preserved, rows kept visible); `regression-test` (a truly-FA bait tops the raw board yet sinks below every non-FA after the fix — fails loudly on regression). Frontier-pruned pool = top-8/pos keeps CP-SAT small without dropping scarce K/DST/TE.

## E5 — in-season

- **lineup**: ONE win-prob objective — draw E3 sim once over combined roster+opp, IP over an `opt_draws` subsample with boolean `win[d]` + big-M link; maximise `sum(win[d])`. Floor and ceiling both emerge. Reported `win_prob` re-measured on full `n_draws`.
- **inseason**: Thompson = draw+argmax (no framework). Trade value uses starting-lineup IP so positional surplus/need falls out. No re-sim on any path.

## E6 — ensemble, features, graph, explain

- **ensemble**: `StackedEnsemble` convex Gaussian-mixture blend; `bma_weights` = softmax of per-member OOS log predictive density. GBM falls back to numpy stumps when lightgbm missing.
- **features**: `discover_features` (z-scored base + degree-2 interactions, no AutoML) → `screen_features` (numpy MI/entropy, no sklearn) → `compute_importance` (per-season) → `ImportanceFactorHook` (feeds back into E1 as a bounded, degrade-neutral opportunity multiplier). `DriftMonitor` (JS/KL in bits).
- **graph**: autoencoder embeddings → k-means archetypes → same-team adjacency → `EcosystemGNN`. **GNN outputs are LIVE only when `ablation.passed` (lift ≥ threshold); otherwise degrade-neutral** (every player → 0, base projection untouched). Shipping inert is the intended degrade path, not a failure.
- **explain**: `explain(projection, *, weights)` + exact `shapley_contributions` (2³ coalitions over volume/efficiency/scoring, no shap dep). Writes `pipeline/artifacts/projection_why.json`; `war_room_article` lifts the brief verbatim only when the artifact is present (keeps E3's 4-article contract byte-identical).

## E7 — backtest & calibration

- **backtest**: generalized to a predictor-callable harness (`(train_df, test_df) → points`) so units test with cheap synthetic predictors (no NUTS). Headline APIs `ablation()` + `no_regression()`; PSI drift + version-keyed benchmark board.
- **calibration**: `calibrated(quantiles, realized, *, max_calibration_error=0.10) -> CalibrationReport` (truthy iff calibrated). `CAL_ERROR_MAX=0.10` clears sampling noise for hundreds of player-weeks. Model units: `assert calibrated(proj.quantiles, y)`.

## E8 — UI

- **draft-room**: live policy = frontend `scoreBoard` (mirrors `FastDraftPolicy` features — no JS bridge to the Python engine, so the committed TS policy IS the live surface). `app/draft/page.tsx` repointed `DraftRoom → DraftWarRoom`; old `DraftRoom.tsx` orphaned (later deleted in the draft-fix cleanup). Re-plan predicate = `isConsequential` (my pick | planned target taken | starter-caliber-at-need taken); plan gated in `useEffect`, recs/board live every pick.
- **model-lab**: gated behind a dev-only lab flag (not shipped to prod nav). Diagnostics reuse E7 metric axes.
- **uncertainty-ui**: prop-driven + colourblind-safe (position+glyph+label, never colour alone). `PlayerValue` has no `mc_probs` yet → top5/beatsAdp omit rather than fake 0%.

## Recurring gotchas (engine-wide)

- **Shared venv, no sklearn**: `pipeline/.venv` has numpy/scipy/pandas/torch/ortools but NOT sklearn — MI/entropy/JS/k-means/Shapley are all hand-rolled on numpy+scipy (platform-primitive over heavy dep).
- **Worktree runs**: dispatched agents' worktrees share git objects but NOT `node_modules` (`npm ci` first) and shadow the main-checkout editable install — run engine pytest from `<worktree>/engine` with `PYTHONPATH=$PWD`.
- **Degrade-neutral seams**: every hook (factor/talent/latent/graph/availability) returns identity/neutral for unknown players or missing signals, so no layer can worsen the base fit.

## Operational facts

- Keys provisioned: `ODDS_API_KEY`, `CFBD_API_KEY` (both in `pipeline/.env` + GitHub secret). Storage/data-source setup: see `docs/architecture/DATA_SOURCES.md`.
- Still optional/unprovisioned: `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT` (richer news; the sentiment path degrades to nflverse/VADER without them).
- Land gate at PR #105: engine 328 · pipeline 129 · frontend 350 tests green.
