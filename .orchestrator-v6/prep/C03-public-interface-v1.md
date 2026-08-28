# C03 public interface freeze v1

Status: **frozen before C03 production implementation**  
Accepted dependency: C02C `417af276dd4438d8a35f38d08bfc26206044925e`  
Companion schema: `C03-public-interface-v1.schema.json`  
Companion TypeScript declarations: `C03-public-interface-v1.ts`

This contract is the concurrency boundary for C03 producers and C04 consumers. Changing a field, export, status, hash rule, or fallback semantic requires a new `C03-public-interface-v2.*` freeze before implementation. V1 is never overwritten.

## Canonical artifact

`fixtures/bench_shape.json` will implement schema version 2. Its top-level fields are exactly:

- `schema_version: 2`;
- `canonical_source_hash`: lowercase SHA-256 of the exact raw bytes of the immutable source receipt named by `canonical_source_receipt`;
- `canonical_source_receipt`: repository-relative portable path to that immutable receipt;
- `rows`: exact league-config-key to row mapping.

The hash is over receipt bytes, not parsed/reformatted JSON. Producers and parity checks must read the same committed bytes. This avoids language-dependent number or key canonicalization.

Canonical league keys use `t{teams}-{qb_mode}-{scoring}-te{premium}-b{bench}-ir{ir}`. Supported positions and stable serialization order are `QB,RB,WR,TE,K,DST`.

Every row contains an exact-budget `composition` and finite `soft_marginal_costs` for all six positions. A marginal-cost curve indexes the cost of adding the next body at depths `0..bench_slots`; it influences ranking but never rejects an otherwise legal player. `lo`, `hi`, `hard_caps`, or equivalent hard positional limits are forbidden.

Evidence provenance is a discriminated union:

- `measured`: immutable receipt ID, production/evaluator SHA, positive paired sample count, and non-empty seeds;
- `interpolated`: immutable receipt ID, non-empty measured source keys, and named method;
- `unsupported`: explicit reason and optional nearest measured keys, with no measured sample count or seeds.

`t14-2qb-std-te0.5-b4-ir1` must remain `unsupported` until a later preregistered result clears it. The schema cannot encode this policy alone; C03 gates must assert it by key.

## Generated browser artifact

The production generator will write `frontend/lib/generated/benchShape.generated.ts` and export exactly:

- `BENCH_SHAPE_SCHEMA_VERSION`;
- `BENCH_SHAPE_CANONICAL_SOURCE_HASH`;
- `BENCH_SHAPE_CANONICAL_SOURCE_RECEIPT`;
- `BENCH_SHAPE_ROWS`.

The module is static data only. It may not import Node modules or use filesystem, crypto, process, subprocess, network, randomness, or simulation APIs. Check mode must regenerate in memory and fail on any byte drift or semantic difference between fixture and TypeScript data.

## C04 resolver boundary

C04 consumes the declaration in `C03-public-interface-v1.ts`:

```ts
resolveBenchShape(key: LeagueConfigKey, benchSlots: number): BenchShapeResolution
```

Exact measured/interpolated/unsupported rows return their honest evidence status. A missing key, malformed artifact, schema mismatch, source-hash mismatch, or budget mismatch returns `evidenceStatus: "unsupported"`, `degraded: true`, a required `degradedReason`, and finite soft fallback curves. Resolution never throws for ordinary evidence absence and never returns a hard cap. C04 may explain the resolution but must remain simulation-free in the browser.

## Integration gates

1. JSON Schema validation and policy assertions pass.
2. Fixture/source-receipt SHA-256 matches exactly.
3. Generated exports match fixture values and hash exactly.
4. `--check` fails after a one-byte drift in either canonical or generated data.
5. Every mandatory 10/12/14-team slice resolves without throwing and conserves its bench budget.
6. Unsupported/interpolated rows never claim measured provenance.
7. Fallback costs are finite and soft; legal roster construction is never rejected by shape depth.
8. Browser artifact contains no Node/runtime-only dependencies and stays below the preregistered byte limit.

No authoritative C03 experiment is authorized by this interface freeze.
