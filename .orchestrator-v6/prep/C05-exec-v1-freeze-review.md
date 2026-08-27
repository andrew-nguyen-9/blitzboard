# C05 promotion-v3-exec-v1 independent freeze review

Verdict: **BLOCK EXECUTION**

- candidate policy SHA: `7b3fd73578943b992402ad693259a3e92358da69`
- reviewed C05 tooling/addendum head: `4c31f9e126b5bc529ab3b2707472c5aef78a4bc1`
- addendum SHA-256: `24e5e50afdad75006ca3a1814317d9254ea98de25bbb97dba4b06bbee7c3b7ad`
- frozen manifest SHA-256: `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`

## Proven freeze properties

The branch is clean and linear from the accepted C02-C04 production head. Five owned C05 commits
were transferred individually without conflict; the netting disposition/dry-run receipt precedes
the execution addendum; the addendum was committed alone. `promotion-v3.json` is byte-identical.
Candidate, control, board-corpus, canonical source, generated artifact, and waiver-cost identities
are recorded. The dry run is clearly non-authoritative. C05 focused tests pass 37/37, Ruff and diff
checks are clean, and the old parked adapter branch remains untouched.

The waiver-cost disposition is acceptable only with a mechanical execution binding to exactly
`0.0`. Any nonzero cost still requires a new manifest version.

## Deterministic execution blockers

1. `promotion-v3.json` retains the required immutable null candidate SHA. The addendum freezes the
   real SHA, but no loader or execution harness applies it. `evaluate_promotion(...,
   authoritative=True)` reads only `manifest["arms"]["candidate"]["combined_candidate_sha"]` and
   therefore still raises the null-SHA precondition error. The freeze exists on disk but cannot be
   consumed by the authoritative gate.
2. `promotion.runner.run_arm` still writes `playoff_proxy=None` and
   `championship_proxy=None`. Accepted C02 supplies `per_season_playoff` and `per_season_champ`, but
   the direct runner never maps them. An authoritative run through this path must end inconclusive
   regardless of actual evidence.
3. `run_arm` trusts the caller-supplied `policy_sha` string and does not prove the evaluator was
   loaded from that checkout. Before execution, the exact two-checkout command/harness must verify
   checkout HEADs and produce arm receipts from baseline `01f01d3c...` and candidate `7b3fd735...`,
   not from the later C05 tooling tree.

The already-accepted C02 calibration report fails frozen calibration thresholds. The authoritative
run may harvest the numerical result, but it cannot promote even if season points improve. Runtime
attestations may fill only genuinely proven report gaps and must not reinterpret failed benchmark
deltas or non-computable cohorts.

## Required correction before execution authorization

Add C05-owned execution tooling and tests without changing the frozen candidate policy SHA,
manifest, or exec-v1 addendum:

1. Load and hash-verify manifest plus exec-v1 into an effective in-memory execution manifest;
   inject only the frozen candidate SHA and explicit `waiver_cost: 0.0` binding.
2. Map accepted C02 per-season playoff/championship proxy arrays into every arm receipt.
3. Provide exact separate-checkout arm commands that assert actual Git HEAD equals the arm SHA,
   verify board hashes and pairing identity, and refuse a later C05 tooling checkout as the
   candidate policy identity.
4. Keep fit and held-out execution write-once and mechanically separated. No authoritative run is
   permitted during this correction.
5. Run the reviewer test unchanged, existing 37 tests, Ruff, hash/immutability checks, a cheap
   real two-checkout/null rehearsal, leakage/determinism probes, and diff/cleanliness checks.
6. Commit an append-only readiness record and stop for a second freeze review.

Do not edit `promotion-v3.json`, `promotion-v3-exec-v1.json`, candidate policy code, frozen
experiment evidence, or accepted C02-C04 behavior. Do not run authoritative fit or held-out arms,
push, merge, or open a PR.
