# v4 Engine Architecture — the two-tier seam (durable design doc)

> Written by Session B (orchestration). Resolves the deferred Q8/Q37 seams:
> `engine/` vs `pipeline/` naming, and the free-storage / free-compute survey framing.
> This is the shared contract every v4 engine unit inherits. Committed on `integration`
> before wave 1 so unit branches see it.

## The two tiers (one brand: "BlitzBoard")

| Tier | Package | Runs where | Deps | Job |
|------|---------|-----------|------|-----|
| **Engine** (heavy) | `engine/` → `blitz_engine` | **Local M1, 16 GB** | JAX/NumPyro, torch, DuckDB, Parquet | ALL quant: MCMC fit, MC sim, IP solver, MCTS/RL. Produces **versioned snapshots**. CLI + local-only Model Lab. |
| **Cron pipeline** (light) | `pipeline/` (EXISTING, role unchanged) | **GitHub Actions (free)** | pandas, duckdb, adapters — **NO jax/torch** | Current-season live sync → Supabase; publish orchestration. Stays free by staying JAX-free. |
| **Website** (light) | `frontend/` (EXISTING) | Vercel + local (Lab) | Next.js 15 | Consumes snapshots; cheap live deltas (VONA/VORP/scarcity/roster-health). Prod build excludes Lab. |

**Why a new top-level `engine/`, not growing `pipeline/`:** the cron MUST stay on the free
GitHub-Actions tier — if it imports JAX/torch the free cron dies. Physical separation of the
`requirements.txt` files is the enforcement. `pipeline/` keeps its exact current role.

## Package layout (E0-scaffold owns the skeleton)

```
engine/
  pyproject.toml            # jax, numpyro, torch, duckdb, pyarrow, ortools; ruff+mypy+pytest
  blitz_engine/
    cli.py                  # fit | sim | draft | publish   (E0-scaffold)
    config.py               # M1 knobs: float32, mmap, chunk sizes, cloud-burst opt-in (E0-scaffold)
    store/                  # DuckDB + memory-mapped Parquet store API (E0-scaffold)
    snapshot/               # versioned bundle schema (E0-scaffold)
    registry/               # model registry {params,data-hash,git-SHA,seed} (E0-scaffold)
    data/
      ingest/  validation/  # 2014+ PBP ingest + validation gate (E0-ingest)
      sources/              # 4 new free sources, degrade-safe (E0-sources)
      reconcile/            # multi-source team assignment (E4fix-team-reconcile)
    projection/             # E1 Bayesian core + talent/factors/latents/context subpkgs
    survival/               # E2
    simulation/             # E3 mc + league/playoffs
    value/                  # E4 interim-fix + equity/mcts/rl + roster_solver/bench
    lineup/  inseason/      # E5
    ensemble/ features/ graph/ explain/   # E6
    calibration/ backtest/  # E7
  tests/                    # pytest; regression/ holds the locked draft-invariant test
```

**Ownership zones** (glob → unit; the depmap `files-owned` column is authoritative — this mirrors it):
disjoint subpackages per unit so no two agents edit one file. `value/` is shared across
E4fix / E4-deep but by distinct files (fa_penalty/roster_solver/interim vs equity/mcts/rl) in
different waves → sequential, never concurrent.

## Shared code seam (the one real coupling)

The **data-source adapters** are the only genuine shared surface between cron and engine
(`pipeline/adapters/`: base, odds, sleeper_state; `pipeline/models/` has more). Decision:

- **W1: no move.** Existing shared code IS the brownfield foundation (orchestrator rule). Engine
  imports the existing adapters by making `pipeline` importable (editable path / `pip install -e`).
  E0-sources adds NEW source adapters under `engine/blitz_engine/data/sources/`, reusing the
  existing `pipeline/adapters/base.py` degrade-safe contract.
- **Later, only if duplication bites:** extract `adapters/` to a `shared/` package. `ponytail:` do
  not pre-extract — a documented import path costs nothing; a premature shared package costs a
  refactor of the working cron.
- The existing `pipeline/models/` (projector, value_engine, season_sim, sentiment, calibration,
  factors/…) are the **interim / fallback** engine. They stay live until the corresponding
  `blitz_engine` module supersedes them via snapshot. E4-fix (W2) corrects the interim board;
  E1/E3/E4-deep swap the deep model underneath without touching the interim contract.

## Snapshot = the hand-off contract (E0-scaffold owns; frozen early, versioned)

Versioned bundle `{values, quantiles, corr_matrix, mc_probs, strategy_tree, policy}`.
**Raw posterior draws stay LOCAL** (Parquet); prod gets quantiles + correlation only (enough for
light live re-sim in the frontend). Every consumer (frontend, cron `publish_snapshot.py`) reads
this schema. Schema version bumps are additive; the frontend degrades to last-good + "as of <date>".

## M1 / 16 GB budget — the sizing constraint on EVERY engine unit

Baked into `config.py` and repeated in every engine brief:
- **float32 everywhere**, memory-mapped Parquet/DuckDB (never load full history into RAM).
- **Chunked / streamed** sims and MCMC; a 1M-run MC never materializes 1M×players in memory —
  stream in batches, accumulate sufficient statistics.
- **JAX-CPU** default (Metal experimental, opt-in). No GPU assumption.
- Any job that won't fit 16 GB → **optional cloud-burst** (opt-in Colab / own box / rented GPU),
  never the default path. Degrade-safe: the CLI runs a smaller-scale variant locally by default.

## Free storage / free-compute survey (Q37 — E0-survey research unit)

Framing (a **research deliverable**, not a code decision): survey R2 (Cloudflare), Colab, Kaggle,
Oracle-free tier, HF Spaces, local-only for (a) snapshot/CDN storage and (b) optional heavy-job
cloud-burst. Output = `docs/research/free-infra-survey.md` recommendation. Gated on the user
blocker "Confirm free storage / free-compute survey scope." Constraint from repo policy:
**free-tier only, no metered compute/storage**; heavy compute is free because it runs local;
storage = local Parquet+DuckDB for raw/history/samples, compact snapshot → Supabase/CDN only.

## Model-ops is foundation-tier, not last (blast-radius correction)

The Model-unit DoD (`spec §Model-unit DoD`) requires **no walk-forward backtest regression AND
calibrated AND ablation-helps**. Every model unit (E2–E6) needs that harness to EXIST to prove
"done." So **E7-calibration + E7-backtest land right after E1-core** (wave 3c), not at the end —
they gate the DoD of everything downstream. E1-core ships with a *minimal* walk-forward compare vs
the current pipeline engine (its own acceptance); E7 generalizes it into the full ablation /
adversarial-stress / benchmark-board harness the later units invoke.
