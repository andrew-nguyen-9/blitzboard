# v5 "Perfect the Draft" — architecture & shared decisions

The design contract every v5 unit builds against. Written before implementation (Session B),
referenced by every unit brief so no brief re-derives a shared decision. Companion docs:
`docs/design/v4-engine-architecture.md` (engine layout), `docs/design/v4-bench-scoring.md`
(the hand-authored bench tables this cycle finally backtests),
`docs/modeling/BENCH_MODEL.md` (the theory doc E1 writes — the yardstick for E6/E8/E10).

## 1. The problem in one line

The autodraft builds bad benches, we never wrote down what a good bench is, and the metric we
would tune against (`docs/modeling/backtest-report.md`'s perfect-hindsight weekly-optimal lineup)
is structurally blind to bench insurance. Fixing the metric precedes fitting anything.

## 2. The layering — what depends on what, and why

```
E1 theory (BENCH_MODEL.md)  ─────────────────────────────┐
E7a config matrix (data)  ──────────────┐                │
E9 CLI wired + 2014+ store populated ───┤                │
                                        v                │
        E7b corpus/golden drafts · E2a availability · E3 injury hazard
                                        │                │
                        E2b publish  ·  E4 bye feasibility│
                                        v                │
                       E5 imperfect-information eval  ·  E8a structural invariants
                                        v                │
                                  E6 roster shape  <─────┘
                                        v
                                 E8b bench-mix invariant
                                        v
                        E10 static fit  ·  E11 dynamic fit
                                        v
                              E12 static/dynamic reconciliation
                                        v
                                  E14 docs + decisions
```

Rationale for the two non-obvious edges:

- **E6 depends on E5.** Positional-count bounds are a *derived* quantity. Deriving them against the
  old hindsight metric reproduces the v4 null (cycle decision 7). They must be derived against the
  new imperfect-information metric.
- **E10/E11 depend on E8b.** The invariant suite is the guardrail that stops a fit from producing a
  technically-optimal-but-insane board. It has to exist before a fit is allowed to ship.

## 3. The league-config matrix (E7a) — a config is a data row, not code

Canonical data lives at `fixtures/league_matrix.json` (repo root, tier-neutral) so both the Python
engine and the TypeScript frontend read one source and cannot drift.

Full grid — the exhaustive product of:

| Factor | Levels |
|--------|--------|
| `teams` | 8, 10, 12, 14 |
| `qb_mode` | `1qb`, `superflex`, `2qb` |
| `scoring` | `std`, `half`, `ppr` |
| `te_premium` | `0.0`, `0.5` (extra PPR per TE reception; a scoring modifier, not a slot) |
| `bench_slots` | 4, 6, 8 |
| `ir_slots` | 0, 1 |

= **432 rows**. Starting slots are derived, not enumerated: base `QB1 RB2 WR2 TE1 FLEX1 K1 DST1`;
`superflex` adds a `SUPERFLEX` slot; `2qb` makes it `QB2` with no superflex.

**Two access functions, one deliberate compromise.** 432 rows × a full season simulation does not
fit an M1 inside a test run, so the loader exposes:

- `all()` — all 432 rows. Cheap, non-simulating assertions (property/invariant tests, lineup
  legality, roster-shape bounds) run the **full grid**.
- `smoke()` — a checked-in, deterministic **16-row pairwise-covering subset** (every pair of factor
  levels appears at least once). Simulation- and fit-driven units run `smoke()` in their DoD and the
  full `all()` sweep behind an explicit `--full` flag, recording the sweep result in their notes.

`smoke()` rows are **data, not regenerated at import time** — a test asserts the pairwise-coverage
property so a hand edit that breaks coverage fails loudly.

Loaders (thin, no logic beyond parsing + the two selectors):
- Python: `engine/blitz_engine/testing/matrix.py`
- TypeScript: `frontend/lib/testing/leagueMatrix.ts` — **test-only**, reads via `node:fs`, never
  imported by app code (the `leak-boundary` test guards the client bundle).

## 4. Availability and the publish path (E2)

`engine/blitz_engine/survival/availability.py` (`AvailabilityModel`, `resolve_status_p`) already
exists and is the seam to extend — this is brownfield, not a new subsystem. It absorbs what
`frontend/lib/draftAI.ts` currently fakes with `faPenalty: 1000` and the `injuryDiscount` lookup,
and what `engine/blitz_engine/value/fa_penalty.py` approximates.

**Publish path decision.** The availability surface reaches Supabase through the **engine's own
`publish` CLI verb** (wired in E9), run locally — *not* through `pipeline/`. This is deliberate:
`pipeline/` must never import jax/torch (it keeps the GitHub-Actions cron on the free tier), and
`blitz_engine` does. Engine writes rows with `SUPABASE_SERVICE_ROLE_KEY` from the local
environment; the frontend reads them through `frontend/lib/queries.ts` with the anon key under RLS.
No service-role credential ever enters a client bundle. Key absent → the publish step writes the
local Parquet snapshot and skips the upload without raising.

## 5. Static ↔ dynamic: the evaluation bridge (E10)

The static tier must stay a cheap closed form with no per-pick simulation — that is the entire
reason two formulas exist (`[[draft-formula-static-dynamic-split]]`). Fitting it against a Python
metric therefore needs a bridge, and the bridge must not duplicate the formula:

**Decision: drive the real TypeScript policy from Python, one process per draft.** A thin node
harness (`frontend/scripts/draft-eval.mjs`) takes `{leagueConfig, policy, playerPool, seed}` on
stdin and returns the drafted rosters; `engine/blitz_engine/backtest/static_fit.py` calls it once
per simulated draft (not once per pick) and scores the resulting rosters with the E5 season
simulator. A per-draft spawn is affordable; a per-pick spawn is not.

Rejected: porting `DEFAULT_POLICY` + `benchScore` into Python. It removes the spawn cost but
introduces two copies of the scoring formula that silently drift — exactly the failure mode this
cycle exists to end.

## 6. Gates — nothing ships unproven

Inherited v4 model-unit DoD, binding on every model/weight unit:
**no walk-forward backtest regression AND calibrated AND `ablation()` verdict `helps`.**
`engine/blitz_engine/backtest/ablation.py` provides `ablation()` and `no_regression()`;
`harness.py` provides `walk_forward`.

**Block-release, no exceptions.** A unit that cannot meet its DoD blocks and does not ship
degraded. A shipped-but-unproven weight is worse than no change: it launders a guess as evidence.
Every fit is reproducible and **seeded**; every shipped weight carries its ablation receipt.

## 7. Per-unit DoD narrowing (monorepo rule)

The repo-level `CLAUDE.md` DoD line stays the release gate and the integration branch runs it in
full after every wave. Individual units run only the tier(s) they touch, so an engine-only unit
does not pay for a Next.js build:

| Unit touches | DoD it runs |
|--------------|-------------|
| `engine/` only | `(cd engine && ../pipeline/.venv/bin/python -m pytest)` |
| `frontend/` | `(cd frontend && npm run build && npm run typecheck && npm run lint && npm test)` |
| `fixtures/` (shared data) | both of the above |
| docs only | the doc's own falsifiable check (links resolve, cited claims match code) |

`pipeline/` is not expected to change this cycle (see §4); a unit that does touch it also runs
`(cd pipeline && ./.venv/bin/python -m pytest)` and must keep jax/torch out of its imports.

**Python env:** one venv serves both tiers — `pipeline/.venv` (3.12, jax/torch/numpyro +
`blitz_engine` editable). Homebrew `python3` is 3.14 and will not work.

## 8. Out of scope

Visual redesign, marketing surface, auth work, **E13 war-room explainability UI** (deferred to a
later UI pass; the existing `explain` / `shapley_pick_attribution` surfaces are left intact for it),
and the standing "Pending activation" backlog (factor hydrator, `/betting` + `/articles` nav links,
sitemap, college enrich). A unit that genuinely blocks on one flags it rather than absorbing it.
