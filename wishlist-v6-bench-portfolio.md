# v6 Bench Portfolio — Synchronous Build and Review Contract

This file supersedes the earlier v6 wishlist. The immutable starting point is the post-pruning
`integration` SHA recorded in `.orchestrator-v6/state.md`.

## Operating model

- Claude owns production TypeScript, engine behavior, canonical generated artifacts, product
  documentation, checkpoint claims, and integration.
- The independent reviewer owns new adversarial tests, independent experiments/gates, checkpoint
  reviews, and corrections explicitly transferred after a blocked checkpoint.
- Each side works in a separate worktree. The reviewer may commit only its branch and owned files
  using Andrew's configured identity. No push, merge, PR, release, protected-branch change, or
  branch deletion is authorized.
- Claude stops before every checkpoint merge until the independent verdict is `PASS`. `BLOCK`
  requires correction. `INCONCLUSIVE` preserves existing production behavior unless Andrew decides.
- Deterministic failures always block. Modeling disputes use preregistered matched-seat experiments.

Every checkpoint has immutable `checkpoints/CNN-claude.md` and `checkpoints/CNN-codex.md` records.
The reviewer first inspects criteria and diff without Claude's rationale, then reconciles the claims.
Verdicts are `PASS`, `BLOCK`, or `INCONCLUSIVE`, with requirement-level evidence.

Experiments are frozen before execution with hypotheses, arms, configurations, seasons, seeds,
metrics, thresholds, and failure interpretation. Amendments create a new manifest version; results
never replace preregistration.

## Checkpoints

### C00 — baseline and contract

Freeze the integration SHA, create separate worktrees, initialize fresh `.orchestrator-v6/` state,
map all eight outcomes to owners/evidence, freeze the promotion manifest and baseline outputs, and
independently reproduce same-bye coverage, broad handcuffs, fixed `overfillDepth`, and reactive-only
waivers. Gate: clean baseline, reproducible receipts, explicit ownership, carried-forward v5 risks.

### C01 — bench logic correctness

Add candidate-aware maximum-matched slot coverage by week; one candidate cannot cover simultaneous
holes and a shared bye gets no credit. Replace the handcuff boolean with structured contingent-role
evidence. Initially support RB succession; QB only with authoritative depth; WR/TE only with explicit
role-transfer evidence. Adversarial coverage includes missing byes, FLEX, superflex, double counting,
false positives, ambiguous depth, and missing metadata. Numerical tuning is excluded.

### C02 — evaluator realism

Add bounded point-in-time proactive waivers, transaction costs, reverse-standings priority, one shared
pool, deterministic seeds, K/DST streaming, and active leakage detection. Retain `started_points` and
add paired H2H plus playoff/championship proxy samples. Gate on emergency/upside distinction,
insurance contrast, determinism, and leakage.

### C03 — complete bench portfolios and shared shape

Evaluate feasible bench count vectors with FLEX/superflex substitution, scarcity, byes, fragility,
correlation, replacement, and budget. Measure the mandatory 10/12/14-team, 1QB/superflex/2QB,
four/eight bench, TE premium, and IR slices. Keep `t14-2qb-std-te0.5-b4-ir1` blocked until cleared.
Version `fixtures/bench_shape.json`, mark measured/interpolated evidence, and generate a browser-safe
artifact with canonical hash and drift-failing parity. Shapes are soft costs, never unsupported caps.

### C04 — live integration and explanations

Replace fixed `overfillDepth` as sole authority with shared lookup/fallback. Expose immediate lineup,
bye/absence, contingent role, breakout, waiver replacement, and redundancy components plus degraded
inputs and evidence status. Keep browser scoring simulation-free. Gate representative traces and
goldens across format/bench/TE/IR configurations.

### C05 — preregistered promotion

Compare against shipped v5 with matched boards, seats, seasons, and common random numbers. Promotion
requires deterministic correctness; started-points CI95 lower bound above zero; zero-tolerance
`no_regression` for every mandatory high-risk slice; H2H lower bound at least -0.005 absolute;
playoff/championship lower bound at least -0.002; no hidden slice regression; held-out confirmation;
and free-local runtime/memory. Failed or inconclusive numerical candidates remain unshipped.

### C06 — independent land gate

Audit the combined tree producer-blind before reconciling Claude's claims. Run frontend build,
typecheck, lint and tests; pipeline pytest; engine Ruff and full pytest; focused experiment
reproduction; secrets/portable-path checks; and original-checkout comparison. Report every outcome
as proven, contradicted, incomplete, or missing. Landing remains blocked until all are proven or
Andrew explicitly removes scope.

## Required interfaces and constraints

- Structured candidate-aware coverage replaces the scalar count.
- Structured contingent-role evidence replaces the handcuff boolean.
- Bench-shape schema carries version, source hash, evidence status, and league key.
- Season evaluation supports bounded proactive waivers and paired outcomes.
- Explanations identify data coverage and fallback state.
- Preserve v5 behavior whenever evidence is inconclusive.
- Exclude trades, full FAAB game theory, dynasty, best ball, auction/keeper strategy, paid data, and
  visual redesign.
- Compute remains local/free; frontend scoring remains simulation-free; pipeline remains JAX/torch-free.
- Git artifacts use Andrew's configured identity and contain no assistant attribution.
