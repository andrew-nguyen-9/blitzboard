# 2026 independent ensemble comparison

The independent comparison reuses `blitz_engine.ensemble`—its GBM, neural-network, Bayesian model
averaging, calibration, market benchmark, and walk-forward infrastructure. It does not create a
second training stack. `blitz_engine.intelligence.model` adds the boundary needed by the current-
season intelligence system.

Both existing and independent forecasts emit one schema: model/version, point-in-time timestamp,
player, position, league configuration, weekly or rest-of-season horizon, availability
probability, conditional mean/stdev, and p10/p50/p90. Expected fantasy points are
`availability_p × conditional_mean`; keeping the terms separate prevents injury uncertainty from
being hidden inside an opaque point adjustment.

## Modes

- `daily`: at most 10 minutes, 8 GB RAM, and 12 search trials. Reuse cached features and the last
  promoted hyperparameters; create a shadow forecast even when promotion is unavailable.
- `deep`: at most eight hours, 12 GB RAM, and 200 trials. Intended for overnight walk-forward
  evaluation, never an unattended daily requirement.

These are enforceable budgets/configuration, not runtime claims. A later training driver records
actual elapsed time, memory, seed, folds, and artifact hashes in the snapshot manifest.

## Promotion gate

The independent model stays shadow-only unless it has no regression versus the existing model in
every position and league configuration for MAE, RMSE, rank correlation, interval calibration,
and top-k decision utility. Evaluation uses shared walk-forward folds and timestamp-vintage inputs.
K and DST require their own members/features rather than borrowing offensive-player coefficients.

Personal/context events remain zero-weight. Trade scenarios produce separate destination outputs;
they do not blend into the primary forecast. Market inputs are timestamped features and must prove
incremental out-of-sample value rather than merely reproduce consensus.
