# C03 independent preparation note

## Prepared contract

- Enumerate all exact-budget count vectors over QB/RB/WR/TE/K/DST (126 vectors for bench 4; 1,287 for bench 8), then score each composition as a whole.
- Enforce actual slot eligibility and maximum matching for dedicated slots, FLEX, superflex, and 2QB; include scarcity, starter bye/fragility, correlated contingencies, waiver replaceability, shallow/deep benches, TE premium, and IR/no-IR as portfolio terms.
- Require schema v2+, exact league key, `measured|interpolated|unsupported`, canonical SHA-256, exact generated-TypeScript parity, browser-safe lookup/arithmetic, and drift-failing check mode.
- Treat shapes as soft marginal costs. Missing/malformed evidence degrades explicitly; interpolation/unsupported fallback cannot claim measured provenance or impose a hard positional cap.
- Keep `t14-2qb-std-te0.5-b4-ir1` explicitly unsupported. Synthetic output is not evidence that can clear it.

## Reviewer-owned evidence

- `engine/tests/test_v6BenchPortfolio_adversarial.py`: complete enumeration, conservation, lineup matching, FLEX/SF/2QB, scarcity, fragility, correlation, waivers, bench depth, TE premium, IR, representative slices, and old-independent-vector contrast.
- `engine/tests/test_v6BenchShape_adversarial.py`: schema/status/provenance, soft fallback, malformed evidence, hash behavior, generated artifact safety, exact drift-gate existence, and blocked-slice status.
- `scripts/v6BenchPortfolioPrototype.py`: standalone synthetic exhaustive optimizer and contract validator.
- `scripts/v6-independent-c03-gate.sh`: repeatable focused gate and receipt generator.
- `.orchestrator-v6/experiments/bench-portfolio-c03-v1.json`: frozen real-experiment hypotheses, arms, exact configs/seeds/seats, metrics, thresholds, and failure meanings. It has not been executed.
- `.orchestrator-v6/prep/C03-synthetic-results.json`: synthetic-only runtime/composition receipt.

## Dependencies on C02

C03 may consume only accepted public contracts for point-in-time inputs, shared waiver-pool outcomes, paired metrics, and deterministic seeds. Tests do not import C02 code or assume its internal representation. Real portfolio comparisons remain blocked until C02 is accepted and its immutable interface is available.

## Unresolved production decisions

1. Exact canonical-source payload whose normalized bytes define `canonical_source_hash` (raw measurement receipt versus normalized producer input). The generator must make this unambiguous and independently reproducible.
2. Interpolation method and distance/support threshold. Extrapolation must default to `unsupported`, not silently become `interpolated`.
3. How uncertainty/sample size maps to soft marginal costs without manufacturing hard caps.
4. Whether K/DST remain in the vector artifact or are represented by explicit streaming soft costs; either choice must conserve the same bench budget.
5. Browser artifact module path/name. The adversarial test currently preregisters `frontend/lib/generated/benchShape.generated.ts`; reconcile explicitly if production selects another stable path.
6. The accepted C02 paired-evaluator adapter and memory budget for authoritative C03 measurement.

## Current implementation gaps (not a C03 verdict)

The accepted C01A fixture is version 1, exposes independent `lo`/`hi` bounds, lacks evidence status/source hash/league-key fields, has no browser-generated artifact or exact drift gate, and marks the known regression row only through test commentary. Four strict expected failures preserve those gaps without making a premature checkpoint decision.
