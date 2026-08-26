# C01-codex — independent acceptance review

## Verdict: BLOCK

- production base: `b8ce3e76c0ae4dea8d655db09c9b36bd7d912c49`
- production head: `48ae46c14f23b72ee99a05900c9841d424b0ed35`
- review mode: implementation and acceptance criteria inspected before reading
  `C01-claude.md`; rationale reconciled afterward
- scope: original C01 plus the frozen player-calibration correctness amendment

## Requirement evidence

### Candidate-aware bye correctness — incomplete

The maximum-matching core correctly prevents same-bye credit, ineligible-slot credit, and
one-body/two-hole double counting. Claude's 26 focused tests pass. However the public result is
only `{ covered: number[], degraded: boolean }`. It does not return expected starts or the
covered week/slot/starter records required by the v6 public-interface contract. The matching
algorithm discards the winning assignment, so C04 cannot explain which starter and slot are
covered without reimplementing the logic.

`benchScore.starterTemplate` also ignores `ctx.config` roster slots. It selects one of two
hard-coded `SUPERFLEX_ROSTER` templates, unlike `draftAI`, which passes the live roster
definition. Consequently the two declared consumers do not evaluate the same league shape and
custom 2QB/slot configurations can be scored against slots they do not have.

Finally, an owned bench player's missing bye excludes that body from the baseline matching but
does not set `degraded`. That can award apparently certain marginal coverage when the result is
actually conditional on missing metadata.

### Structured contingent-role value — contradicted

`contingentRole` is structured evidence, but it is not the structured contingent-role **value**
specified by C01. Its result has no eligibility, inheritance probability, expected value, or
degradation reason. `draftAI` immediately collapses it to `status === "supported"` and feeds the
old boolean `injuryCover`; `benchScore` applies its own separate formula. The promised single
public implementation therefore does not prevent divergent valuation.

The evidence validator checks candidate depth 2 but does not verify that the proposed relevant
starter is the same position or authoritative depth 1. A depth-2 RB paired with a same-team WR,
or with an ambiguously ordered RB, can be marked supported. This is outside the stated RB/QB
succession rule and is not covered by the submitted adversarial tests.

### Player-value deterministic corrections — proven

The ceiling/raw projection conversion, redraft-age double-count removal, `search_rank` removal,
and full QB allocation of OP replacement demand are present in both applicable engines and
consumers. Reviewer-owned strict-xfail tests run against the production pipeline with
`--runxfail`: **3 passed**. Claude's focused frontend suites also pass: **67/67** across
`contingency`, `valueUnits`, and `draftAI`.

The OP corpus measurement is correctly labeled endogenous and rejected as evidence; the adopted
format rule is explicit. Numerical calibration remains appropriately deferred to C02.

### Golden behavior and hygiene — proven within submitted evidence

The regenerated fixtures remain canonical according to Claude's full engine receipt, and the
focused full-draft invariants pass. `git diff --check` is clean. No merge, push, or C02 work was
observed.

## Required correction

1. Make bye coverage return expected-start count plus deterministic covered
   week/slot/starter records from the actual matching assignment; preserve marginal semantics.
2. Give `BenchCtx` an actual roster-slot/template input derived from its league configuration,
   and have both consumers call the same implementation with that real template. Cover 2QB and
   a non-default/custom slot shape.
3. Treat missing bye metadata on any owned body that could affect baseline matching as degraded;
   add a direct adversarial test.
4. Replace the contingent boolean bridge with one shared structured valuation result containing
   eligibility, relevant starter, inheritance probability, expected value, evidence, and an
   explicit degradation reason. Both consumers may scale the shared expected value into their
   score, but may not independently reconstruct whether/value of succession.
5. Validate candidate/starter position compatibility and authoritative direct succession
   (including starter depth where required). Add cross-position, ambiguous-starter-depth, and
   missing-starter-depth tests.

Do not tune coefficients in this correction. Preserve the accepted player-value fixes and
immutable C01 checkpoint, write `C01A-claude.md`, and stop for re-review.
