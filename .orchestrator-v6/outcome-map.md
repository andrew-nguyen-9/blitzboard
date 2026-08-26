# v6 outcome evidence map — production

Eight tracked outcomes → implementation surface, tests, metrics, checkpoint evidence.

| # | Outcome | Implementation surface (baseline today) | Tests (Claude-side) | Metrics | Checkpoint evidence |
|---|---------|------------------------------------------|---------------------|---------|---------------------|
| 1 | Candidate-aware slot coverage | `frontend/lib/benchScore.ts:197` `byeCoverage` (scalar starter-bye compare; no slot eligibility, shared bye still credits 0.25) → replace with max-matched by-week coverage | new `benchScore` coverage tests: missing bye, FLEX, superflex, double counting, shared bye = 0 credit | coverage term value per candidate/week | C01-claude.md + reviewer adversarial tests |
| 2 | Structured contingent role | `frontend/lib/benchScore.ts:181` `handcuffValue` (own-roster positional depth only) → structured evidence: RB succession; QB authoritative depth; WR/TE explicit role transfer | evidence-typed tests: unrelated backup, ambiguous depth, missing metadata → no credit | contingent-role evidence status distribution | C01-claude.md |
| 3 | Proactive point-in-time waivers | `engine/blitz_engine/simulation/season_eval.py:530` `_run_waivers` (reactive-only: exits when no lineup hole) → bounded proactive adds, costs, reverse-standings, shared pool | engine tests: stale bench upgrade, breakout claim, contested pool, cost bound, K/DST stream, leak guard | waiver_adds, started_points delta | C02-claude.md |
| 4 | Paired H2H + playoff outcomes | `season_eval.py` `SeasonEvalResult` (has started_points, h2h_win_rate) → add paired H2H + playoff/championship proxies, deterministic seeds | determinism (same seed = same result), sample counts, CI receipts | paired deltas + CI95 | C02-claude.md, C05-claude.md |
| 5 | Whole-bench portfolio | bench count vectors w/ FLEX/SF substitution, scarcity, byes, fragility, correlation, replacement, budget (new engine surface) | composition vs independent-bound experiment | portfolio value vs v5 bench heuristic | C03-claude.md |
| 6 | Versioned shared shape | `fixtures/bench_shape.json` (16 rows; `version:1` but NO `schema_version`, `source_hash`, evidence status, league key) → versioned schema + browser-safe artifact + parity hash | schema/hash/parity/fallback tests; drift fails | canonical hash match frontend↔fixture | C03-claude.md |
| 7 | Live scoring + explanations | `frontend/lib/draftAI.ts:133` fixed `DEFAULT_POLICY.overfillDepth` used at `:405` → shared lookup + fallback; component-level explanations, degraded-input status; browser stays simulation-free | trace goldens across format/bench/TE/IR configs | golden parity | C04-claude.md |
| 8 | Promotion + land decision | `.orchestrator-v6/experiments/promotion-v1.json` (preregistered, sha256 020047cd…36d7f, byte-identical to reviewer copy) | matched-seat reproduction, blind audit | thresholds in manifest | C05-claude.md, C06 reviewer verdict |

## Carried-forward v5 risks (all remain open at baseline)

- `t14-2qb-std-te0.5-b4-ir1`: real −25.3 regression (p=0.0025), `engine/tests/test_roster_shape.py:241` KNOWN_REGRESSION_ROW; stays blocked until C03 clears it.
- No promoted static-fit candidate (v5 dynamic lost; leaf evaluator is the constraint).
- Reactive-only waivers (`_run_waivers` docstring lists deliberate omissions).
- Fixed frontend `overfillDepth` as sole authority.
- Scalar same-position bye credit (`byeCoverage`).
- Positional-depth handcuff inference (`handcuffValue`).
- `bench_shape.json` rows lack evidence-status labels — unsupported rows must not be labeled measured.
