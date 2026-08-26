# v5 "Perfect the Draft" — architecture & shared decisions

The design contract every v5 unit builds against. Written before implementation (Session B),
**annotated at cycle close (2026-08-25, E14)** with what the cycle confirmed and what it overturned
— `OUTCOME:` callouts below are retrospective; everything else is the original contract.
Referenced by every unit brief so no brief re-derives a shared decision. Companion docs:
`docs/design/v4-engine-architecture.md` (engine layout), `docs/design/v4-bench-scoring.md`
(the hand-authored bench tables this cycle finally backtests),
`docs/modeling/BENCH_MODEL.md` (the theory doc E1 writes — the yardstick for E6/E8/E10; **see its
§6 for which predictions survived**). Cycle outputs: `docs/modeling/draft-eval.md` (the metric),
`docs/modeling/experiments.md` (every fit, seed and command),
`docs/decisions/2026-08-25-v5-perfect-the-draft.md` (the harvest),
`docs/design/v5-static-dynamic.md` (E12's reconciliation).

## 1. The problem in one line

The autodraft builds bad benches, we never wrote down what a good bench is, and the metric we
would tune against (`docs/modeling/backtest-report.md`'s perfect-hindsight weekly-optimal lineup)
is structurally blind to bench insurance. Fixing the metric precedes fitting anything.

> **OUTCOME — the premise was right and the metric is fixed.** `started_points`
> (`docs/modeling/draft-eval.md`) replaced it. Proof it mattered: a bench-insurance ablation moves
> the new metric **+19.5 pts/season p=0.0055** while the retired one scores the same two rosters at
> **+43.9 p=0.2295 — blind**. The autodraft, however, was **not** measurably improved: both fit
> units gated their candidates and shipped **zero** weight changes. What the cycle actually bought
> is a metric you can trust a negative result from, plus a measured diagnosis of where the headroom
> is (the leaf evaluator — see §5).

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

> **OUTCOME — the graph held, with one insertion.** E9's ingest shipped **without** injuries,
> rosters or depth_charts, which E3 and E2a both depended on; a scoped **E9b** was inserted at wave
> 3 and **E3 and E2a were re-fitted** (wave 3b) before E4 could multiply them together. That
> ordering was load-bearing: pre-refit, E2a's availability and E3's hazard were **the same
> snap-presence signal**, so building E4 first would have baked in a double-count. E13 stayed out.

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

> **OUTCOME — done, and the fakes are GONE.** `faPenalty`, `injuryDiscount` and
> `injuryAvailability()` were **deleted** from `PolicyParams`/`DEFAULT_POLICY` (E2b); `scoreBoard`
> now multiplies by `availabilityOf(p, ctx.availability)`, read from `public.player_availability`
> (RLS: anon/auth read-only, service-role writes) with a local estimate and then neutral (1) as
> fallbacks. The engine-side producer is `snapshot/publish_availability.py` wired into the `publish`
> verb; absent a service-role key it no-ops rather than raising. **Any doc or brief still describing
> `faPenalty`/`injuryDiscount` as live knobs is stale.** Availability values also *moved materially*
> in the refit — PRACTICE_SQUAD 0.06 → 0.0043 now crosses `ZERO_AVAILABILITY_EPS`, a semantic state
> change; read `p_startable` at publish time, never bake numbers.

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

> **OUTCOME — the bridge was built and used; the split stays (E12, Outcome B).** E10 drove the
> unmodified TS policy over `draft-eval.mjs` (one process per *batch* of drafts, ~0.5 s/draft) and
> `static_proxy` was **not** used in the static fit. E12 then measured both tiers in ONE league,
> same board, same seed: the **shipped dynamic policy is −23.7 pts/season BEHIND the static closed
> form**, CI95 [−65.9, +19.0] — indistinguishable from zero and pointing the wrong way. So **no
> 4-feature → 20-knob bridge was built**; building one would import a policy weaker than the one it
> replaces. **But the headroom is real:** E5's own per-pick picker beats the static form by
> **+82.7 [+43.1, +122.5]** on the identical grid, so the shipped policy forfeits ~106 pts/season.
> The binding constraint is the **leaf evaluator**, not capacity, search depth or feature
> vocabulary — E11 and E12 reached that from opposite directions. **Flip condition to Outcome A,
> stated in advance:** a *learned* policy clearing `static_proxy` with a CI95 lower bound strictly
> above 0 on E11's 3×3 grid at seed 20260825. Detail: `docs/design/v5-static-dynamic.md`.
>
> Residual: `static_proxy` ≠ `draftAI.ts` is **bounded, not closed** (~1.1 %, in the static tier's
> favour). Closing it exactly needs TS seated per-*pick*, which this section forbids on cost.

## 6. Gates — nothing ships unproven

Inherited v4 model-unit DoD, binding on every model/weight unit:
**no walk-forward backtest regression AND calibrated AND `ablation()` verdict `helps`.**
`engine/blitz_engine/backtest/ablation.py` provides `ablation()` and `no_regression()`;
`harness.py` provides `walk_forward`.

**Block-release, no exceptions.** A unit that cannot meet its DoD blocks and does not ship
degraded. A shipped-but-unproven weight is worse than no change: it launders a guess as evidence.
Every fit is reproducible and **seeded**; every shipped weight carries its ablation receipt.

> **OUTCOME — block-release held under exactly the pressure it exists for.** Wave 7 put both fit
> units on the line and **both returned measured negatives and shipped nothing**: E10 gated six
> candidates (zero cleared `helps` + a clean `no_regression` on **both** slices) and E11 promoted
> neither arm (both CI95s entirely below zero). Nothing was tuned into a pass and no threshold was
> widened — E10 ran `no_regression` at `tolerance=0.0`, *tighter* than the 0.02 default, and E3's
> calibration gate blocked twice on real defects that were fixed rather than tuned around.
> **Held-out validation is what caught the only apparent win** (`trade_value_zero`: +5.34 helps on
> the 2024 fit slice, −1.08 neutral on held-out 2021). Receipts:
> `engine/experiments/{static,dynamic}/`, reproduced in `docs/modeling/experiments.md`.

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

> **OUTCOME — the per-unit DoD narrowing worked, but a WORKTREE HAZARD degraded it all cycle.**
> The venv's **editable** `blitz_engine` resolves to the **MAIN checkout**, so `cd engine && pytest`
> inside a linked worktree collects the *worktree's* tests while importing *main's* code — a unit
> can silently green-light code that is not its own. Treat per-unit engine `verified:` claims from
> this cycle as **corroborating, not authoritative**; the per-wave integration DoD on the main
> checkout (green every wave, counts rising monotonically 328 → 4079) is the authoritative record.
> **Fix, now on the `CLAUDE.md` `DoD-note:` line:** run
> `(cd engine && PYTHONPATH="$PWD" /abs/path/to/blitzboard/pipeline/.venv/bin/python -m pytest)`;
> `../pipeline/.venv` does not exist in a linked worktree (gitignored) and `frontend/node_modules`
> is not shared either (`npm ci` first). See `docs/modeling/experiments.md` §0.
>
> The per-wave integration gate also earned its keep directly: it caught a circular import between
> `lineup.feasibility` and `simulation` that existed **only once E4 and E5 were both merged** —
> each was green alone. That is the exact class of failure a per-unit DoD cannot see.

## 8. Out of scope

Visual redesign, marketing surface, auth work, **E13 war-room explainability UI** (deferred to a
later UI pass; the existing `explain` / `shapley_pick_attribution` surfaces are left intact for it),
and the standing "Pending activation" backlog (factor hydrator, `/betting` + `/articles` nav links,
sitemap, college enrich). A unit that genuinely blocks on one flags it rather than absorbing it.

> **OUTCOME — scope held. E13 was deferred with no work started**; the `explain` /
> `shapley_pick_attribution` surfaces are untouched and intact for it. Nothing shipped this cycle
> depends on it. Open work carried forward is listed in
> `docs/decisions/2026-08-25-v5-perfect-the-draft.md` §8 — headline items: swap the MCTS leaf to a
> sim-priced evaluator, variance-reduce the RL reward, and the ~14 `DEFAULT_POLICY` knobs plus the
> whole `GENERAL_WEIGHTS` / `GENERAL_PENALTIES` / `SF_QB_WEIGHTS` surface that were **never
> backtested**. `matrix.all()` (432 rows) was never simulated by anything — every fit ran
> `smoke()`'s 16 rows.
