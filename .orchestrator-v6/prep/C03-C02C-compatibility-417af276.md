# C03 compatibility with accepted C02C `417af276`

Status: **green compatibility evidence; disposable branch, not integration authority**.

Accepted dependencies:

- production: `417af276dd4438d8a35f38d08bfc26206044925e`
- immutable production checkpoint: `.orchestrator-v6/checkpoints/C02C-claude.md`
- independent PASS: `f2a1537dbae7a0a5419fb39ad4aa1ea184f850ac`
- preserved C03 preparation source: `5741cd6ad2fcc0d9523f0a2034ca17123b670011`
- compatibility cherry-pick: `8e9a36d`

This report does not issue a C03 verdict, clear a blocked slice, authorize an experiment, or make this disposable branch an integration source.

## Compatibility gates

```sh
C03_PYTHON="$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  bash scripts/v6-independent-c03-gate.sh
```

Result: **22 passed, 4 strict expected failures in 5.48s**. The expected failures remain exclusively C03 work: legacy shape schema v1, absent browser-safe generated artifact, absent exact drift checker, and no explicit canonical `unsupported` status for `t14-2qb-std-te0.5-b4-ir1`.

The refreshed synthetic-only receipt records 3.827055s runtime, 0.63419 MiB traced peak allocation, and 24.84375 MiB process peak RSS. It is not promotion evidence.

```sh
PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  -m pytest engine/tests/test_waiver_realism.py -q
```

Result: **42 passed in 4.15s**.

## Accepted public dependency boundary

| C03 dependency | Accepted C02C surface | C03 usage rule |
|---|---|---|
| Point-in-time evaluator | `evaluate_rosters`, `evaluate_season`, `EvalConfig`; weekly beliefs use only preseason projection and already observed weeks, with active leakage detection. | Treat evaluator internals as a black box. C03 records league row, evaluator config, seed, arm, seats, and commit externally; it must not import private decision arrays/functions. |
| Shared waiver outcomes | One contested pool; reverse-standings priority; shared weekly and season budgets; emergency/upside counters; roster-wide legal add/drop moves; remaining-horizon cost gate; FLEX/OP/SFLX/SUPERFLEX aliases. | Consume end outcomes and public counters. Mechanism-level claims beyond those accepted behaviors require explicit receipts; never couple to `_run_waivers` or `_best_upgrade`. |
| Paired metrics | `SeasonEvalResult.per_season`, `.per_season_h2h`, `.per_season_playoff`, `.per_season_champ`; `paired_ci`. | Before pairing, independently assert equal shapes, league/config, seed, seat map, arm map, and common-random-number lineage. Playoff/championship remain labeled proxies. |
| Deterministic seeds | `EvalConfig.seed` drives draft, injury, availability, and deterministic waiver order; accepted tests prove exact repeatability. | Record seed and accepted production SHA in every C03 result. Private stream offsets are implementation details and are not part of the C03 public interface. |
| Slot legality | Public shared `value.mcts.slot_positions` recognizes dedicated slots, FLEX, SUPERFLEX, OP, and SFLX; roster solver uses the same alias semantics. | C03 enumeration uses canonical slot eligibility, including OP/SFLX aliases, without copying C02 private tables into production. |

## Remaining C03-only blockers

1. No accepted complete-vector portfolio producer or authoritative portfolio measurements exist.
2. The canonical shape remains schema v1 with hard independent positional bounds.
3. Evidence status, canonical source hash, browser artifact, exact parity, and explicit degradation are unimplemented.
4. `t14-2qb-std-te0.5-b4-ir1` remains blocked and must be encoded as `unsupported` until preregistered evidence clears it.
5. The C03 public artifact/lookup interface must be frozen separately before C03 implementation so C04 can consume it concurrently.

Disposition: accepted C02C interfaces are compatible with the existing C03 preparation gates. Freeze the C03 interface next; do not run the authoritative C03 experiment until implementation, generation, parity, and accepted-interface checks are ready.
