# C02-codex — independent evaluator/calibration review

## Verdict: BLOCK

- production base/integration record: `13ec3c2672010a81f8e72944bd891f855d1413b7`
- reviewed production head: `edbcc4d743b447ebcbbfe84a0e1210380c6250d1`
- review order: acceptance criteria and production diff first; independent adversarial
  reproduction second; `C02-claude.md` reconciled last
- C03 compatibility evidence: disposable commit `23078d4` (non-authoritative)
- C04 provisional contract follow-up: `5df6728` (queued, not integrated)
- C05 provisional adapter evidence: `a79af01` (synthetic/non-authoritative)

## Requirement evidence

### Point-in-time behavior, leakage, determinism — proven

Weekly lineups and waiver forecasts are based on preseason projection plus observations already
available to the manager. The post-week waiver call is conservative by one observation because it
uses the projection computed at the prior lock, but it does not read future outcomes. The active
leak detector still rejects an injected current-week decision row. Identical seeds reproduce all
new outcome arrays and a changed seed changes stochastic results.

Claude's 11 focused realism tests pass. The disposable C03 compatibility run independently
reproduced those 11 tests and the C05 adapter independently confirmed that the leakage probe is
live.

### Shared pool, priority, bounds, counters, streaming — proven within bounded model

One finite mutable free-agent pool is shared in reverse-standings order with deterministic seat
tie-breaking. Claimed players leave it and dropped bodies return to it. Weekly and season claim
bounds are enforced. Emergency/upside counters reconcile to total claims. K/DST starters can be
replaced through the proactive rule without a special-case mandate.

### Roster-wide proactive replacement — contradicted

The contract requires comparing the lowest forward-looking nonstarter with available players.
`_best_upgrade` instead requires the added and dropped players to have the same nominal position.
It does not receive the league slots and cannot recognize legal substitution across FLEX-style
eligibility.

Independent failing reproduction: a roster with a low RB nonstarter and a materially better free
TE, where both are legal FLEX bodies, returns no swap. This is an observable false negative, not a
modeling disagreement.

### Transaction-cost decision boundary — contradicted

The preregistered C02 contract requires a transaction only when its forward improvement exceeds
the transaction-cost threshold. In the implementation, `upgrade_margin` decides whether to claim
and `waiver_cost` is subtracted only after the season. Cost is not passed into `_run_waivers` or
`_best_upgrade`; it therefore cannot veto a transaction.

Independent failing reproduction: a claim still executes with `waiver_cost=10,000`, producing a
large negative net result. Claude's own test explicitly asserts that claims are identical with and
without cost, confirming the semantic mismatch. The default `upgrade_margin=0.15` was also not
frozen in a versioned C02 experiment manifest before implementation and is a relative projection
margin, not the documented per-claim points cost.

### Breakout acquisition — incomplete

The submitted stale-bench test gives the free agent a superior preseason projection. It proves
proactive replacement but not acquisition of a genuine in-season breakout whose preseason prior
was initially low and whose point-in-time observations later make it actionable. Add a direct
trajectory test after correcting the decision rule.

### Paired outcomes — proven as samples; provenance remains downstream work

Per-season started-points, H2H, playoff, and championship-proxy arrays have coherent shapes and
accounting. Playoff/championship are honestly labeled proxies. C03 found them usable provided the
caller independently verifies league, seed, config, seats, arm, and shape; `SeasonEvalResult` does
not itself carry that provenance. That is a C03/C05 runner obligation rather than an additional
C02 blocker.

The transaction-cost mismatch must be reconciled in the promotion manifest because
`per_season` is net of cost while H2H/proxy outcomes remain on-field outcomes. C05 correctly
refused to edit the frozen manifest.

### Player calibration — executed but numerically inconclusive

The committed snapshot, derived benchmark data, boards, decompositions, hashes, retrieval
deviations, and unavailable cohorts form a substantive reproducible report. No coefficient was
changed. Superflex agreement improves materially and supports the OP correction; 1QB and 2QB fail
the frozen non-regression thresholds for Spearman and weighted rank error. The report records those
failures and remains `executed_report_only`, which is the correct disposition. C05's independent
adapter maps the report and still returns `do_not_ship_candidate` even with synthetic favorable
season evidence.

This calibration result neither reverses the already accepted deterministic C01 fixes nor proves
a numerical promotion. Existing production behavior remains the authority wherever evidence is
inconclusive.

## Required C02A correction

1. Before changing the decision rule, freeze a new versioned waiver-realism manifest containing
   the hypotheses, exact cost units, threshold, remaining-horizon conversion, boundary semantics,
   configs, seeds, metrics, and failure interpretation. Do not rewrite existing manifests.
2. Evaluate feasible roster-wide add/drop moves using actual lineup-slot eligibility and the
   lowest forward-looking nonstarter opportunity cost. Do not require identical nominal positions.
3. Make transaction cost part of the claim decision in consistent units. A claim whose expected
   remaining-horizon improvement is equal to or below its cost must not execute; retain any
   separately documented accounting penalty without double-charging it.
4. Add adversarial tests for cross-position FLEX substitution, just-below/equal/just-above cost
   boundaries, and a genuine in-season breakout that begins below the incumbent preseason prior.
5. Preserve the proven shared-pool, reverse-priority, caps, emergency/upside distinction, K/DST,
   determinism, leakage, paired samples, and calibration artifacts. Do not tune player-value
   coefficients or reinterpret failed calibration thresholds.
6. Preserve `C02-claude.md`; write immutable `C02A-claude.md` and stop for re-review.

The C03 compatibility branch remains disposable and must be recreated from C02A if behavior or
interfaces change. No integration, C03 production, authoritative experiment, push, or merge is
authorized by this review.
