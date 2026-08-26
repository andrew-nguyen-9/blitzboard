# engine/tests/regression — traceability map

Every invariant here maps to a requirement it enforces: a `BENCH_MODEL.md` falsifiable
prediction (`P<n>`), a wishlist bullet, or the W2 bug-fix acceptance gate (E4fix). An invariant
with no source below gets removed or gets a source — none currently lack one.

## `test_draft_invariants.py`

| Test | Source | Notes |
|---|---|---|
| `test_draft_invariants_hold_for_every_team` | W2 acceptance gate (E4fix-roster-solver, E4fix-fa-penalty, E4fix-team-reconcile) | 4-team snake draft, 5 seeds |
| `test_fa_baits_are_top_raw_value_but_sunk_after_penalty` | same (non-vacuity guard) | proves the FA bait scenario is load-bearing |
| `test_interim_value_import_surface_is_stable` | import/rename drift guard | cheap smoke |
| `test_no_empty_offensive_slot_across_grid` | brief item 2 bullet 1 (e8a) | `matrix.all()`, 432 rows |
| `test_k_dst_cap_before_final_rounds_across_grid` | BENCH_MODEL P6/P10 (dead weight, K/DST half) | `matrix.all()` |
| `test_k_dst_cap_threshold_is_a_per_row_round_number` | same | cap threshold is per-row, not a literal |
| `test_bench_coverage_predicate_catches_an_uncovered_slot` | predicate-soundness guard only | grid-wide claim RETIRED (see below) |
| `test_full_season_feasible_smoke_grid` | brief item 2 bullet 4 (e8a) | `SMOKE_ROWS` by default, `BLITZ_ENGINE_FULL_SWEEP=1` for `ALL_ROWS` |
| `test_no_zero_availability_player_survives_the_availability_filter` | brief item 2 bullet 5 (e8a) | e2a's `ROSTER_STATE_P` read live, never retyped |
| `test_bench_positional_mix_within_e6_bounds_across_grid_predicate_soundness` | BENCH_MODEL P10 (e8b) | proves `BenchBounds.contains` bites, standalone |
| `test_bench_positional_mix_naive_value_max_would_violate_e6_bounds` | BENCH_MODEL P10 (e8b) | the "optimal-under-naive-score, insane-under-invariant" case named in the brief |
| `test_bench_positional_mix_within_e6_bounds_across_grid` | BENCH_MODEL P10 (e8b), e6 `bench_bounds`/`to_requirements` | `matrix.all()`, hard CP-SAT constraint |
| `test_kdst_timing_cap_matches_derived_rule_across_grid` | BENCH_MODEL P10 (e8b), e6 `kdst_timing` | the derived K/DST timing rule, named per the brief |

### Retired invariant: `test_bench_covers_every_starting_position_across_grid`

e8a wrote this `xfail`'d, pending e6's bounds. With the bounds landed, the claim was checked
and found **false**, not merely untested: e6's own `bench_bounds` derives a bench CEILING of
`0` for a position in 234/432 rows (e.g. QB/DST/TE `hi=0` on several 4–6-slot benches) — the
measured, evidence-based optimum genuinely carries zero bench depth there. Forcing coverage of
every starting position would contradict e6's own measurement, not fix a value-maximizer's
pathology. Removed (not left decoratively `xfail`'d); superseded by
`test_bench_positional_mix_within_e6_bounds_across_grid`, the correctly-generalised property
(an UPPER bound per e6, not a coverage LOWER bound). The uncovered-slot predicate itself is kept
and proven sound by `test_bench_coverage_predicate_catches_an_uncovered_slot` in case a future
unit needs it once floors are non-trivial.

## Full-matrix sweep

`test_no_empty_offensive_slot_across_grid`, both K/DST cap tests, the availability test, and
both new e8b bench-mix/timing tests already run over `matrix.all()` (432 rows) by default — see
e8b's `.done.md` for the measured wall-clock. Only `test_full_season_feasible_smoke_grid` (18x
`optimize_lineup` per row) stays on the 16-row `smoke()` set by default:

```
BLITZ_ENGINE_FULL_SWEEP=1 pytest tests/regression/test_draft_invariants.py -k full_season
```
