# Component Probabilistic Preseason Phase

**Authority:** exploratory synthetic development evidence only. Shipped v5 remains production
authority; this phase cannot reopen C05 promotion.

## Decision ledger

1. Replace v5's conditional projection with unconditional season totals. Rejected: the prior
   phase measured double-discounted availability and worse draft outcomes.
2. Reuse the existing intelligence contract and evaluate conditional production and availability
   separately. Selected: smallest reversible change, no dependency, and matches the runtime model.
3. Build a new joint production/availability model. Deferred: the archive lacks point-in-time
   injury, depth-chart, rookie, and preseason roster inputs needed to identify it honestly.

The historical appearance fraction is an exploratory availability baseline, not a replacement for
`AvailabilityModel.p_startable`. A stat-bearing game is only a proxy for startability and cannot
distinguish injury, role, roster state, or a zero-stat appearance.

## Bounded design

- Add an expanding-origin component forecaster over the existing player-season table.
- Forecast full-schedule conditional production from prior per-game production, and forecast
  appearance probability separately from prior games divided by the known schedule.
- Compare prior, position-pooled, and two-season recency components without target-season inputs.
- Derive `expected_mean = conditional_mean * availability_p` only at the evaluation boundary.
- Score conditional MAE/rank, availability Brier/MAE/calibration gap, and expected-total MAE/rank.
- Wire an optional `availability_by_arm` map into the existing Node bridge. Only a v5 candidate arm
  may consume it. Existing poison tests prove `human_adp` behavioral isolation, but the bridge still
  passes full player objects; strict non-receipt requires the later narrow market-row hardening.
- Run an availability-only draft shadow first. A conditional projection shadow is allowed only if
  its point screen improves without changing the meaning of the existing boom/bust fields.

## TDD and verification

1. Add failing tests for exact component decomposition, bounded shrinkage, causal fold isolation,
   deterministic scores, bridge validation, candidate-arm causality, and human-arm isolation.
2. Implement the smallest functions and bridge fields needed to pass those tests.
3. Run the 2014-2024 archive screen and fixed-seed 2024 blind-market shadows.
4. Record compact JSON artifacts, hashes, limitations, and an accept/reject decision in the
   modeling note; do not commit raw simulation rows.
5. Run focused frontend/engine tests, Ruff, TypeScript checks, `git diff --check`, and inspect all
   changed paths. Full repository suites are required before any completion claim.
