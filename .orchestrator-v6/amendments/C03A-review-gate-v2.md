# C03A reviewer-gate amendment v2

The original reviewer test at `ff50f693` incorrectly required immutable
`bench-portfolio-c03-source-v1.json` to contain corrected consumer dispositions while the verdict
simultaneously required that receipt to remain byte-for-byte unchanged.

This amendment resolves the contradiction without weakening the C03 BLOCK finding:

- source-v1 must retain SHA-256
  `01734b796d605788bf6b6815d2484242a4c25a2fe1c0a148f173280d3efc7e2b`;
- the corrected canonical artifact must name
  `.orchestrator-v6/experiments/bench-portfolio-c03-source-v2.json` as its exact hashed source;
- source-v2 must retain the authoritative `do_not_promote` disposition and expose every consumer
  row as `unsupported`;
- the canonical artifact must likewise expose every row as `unsupported`.

The authoritative experiment, results-v1, source-v1, frozen manifests, formulas, thresholds, and
numerical findings remain immutable. This test amendment is reviewer-owned and precedes C03A
production correction.
