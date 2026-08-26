# C03 preparation wishlist

- Outcome: independent specifications, adversarial tests, synthetic prototypes, and gate infrastructure for complete bench portfolios and the shared bench-shape artifact.
- In scope: reviewer-owned C03 notes, versioned preregistration, tests, scripts, and synthetic receipts.
- Out of scope: production scoring/evaluator changes, canonical or generated production artifacts, authoritative promotion experiments, and a C03 verdict.
- Constraints: start at accepted C01A `b81541c226dd5aeeacbe9ed79df927853a4b8954`; preserve the blocked 14-team 2QB slice; remain local/free and browser-safe; do not depend on C02 internals.
- Verification / DoD: focused adversarial tests classify current gaps honestly; prototype enumerates every feasible vector; deterministic receipt records runtime/memory; owned diff is clean; branch is committed without attribution.
- Branch prefix: `v6/c03-prep`
- Delegation allowed: no

Routing: orchestrator-sized. Durable state is namespaced under `.orchestrator-v6/prep/C03-*` to avoid the active production/review state.
