# C02A-codex — independent correction review

## Verdict: BLOCK

- reviewed parent: `edbcc4d743b447ebcbbfe84a0e1210380c6250d1`
- preregistration commit: `62a93365b4bfe6461771fc7944257c80aef31bfd`
- reviewed production head: `de42301a0ab98342ed967136b36ee0af71307aa2`
- primary review evidence: `d50f757`
- supplemental remote evidence: `52ccba9` (original laptop-2 commit `0993a9c`)

## Accepted corrections

The new waiver manifest was committed before the behavior change and leaves prior manifests
untouched. It freezes cost units, strict boundary behavior, remaining-horizon conversion, the
anti-churn margin, seeds, configs, and failure interpretation.

The original primary review reproductions now pass unchanged:

- a FLEX-eligible cross-position substitution is recognized;
- a prohibitively costly claim does not execute.

The just-below/equal/just-above cost boundary, emergency cost gate, infeasible-add veto, and
low-preseason breakout trajectory are directly tested. Existing shared-pool, priority, season
cap, determinism, leakage, counters, K/DST, paired samples, and calibration artifacts remain
intact.

## Remaining deterministic contradictions

### Roster-wide lowest nonstarter — still incomplete

The corrected rule restricts drop candidates to bodies whose slot-role space overlaps the free
agent. This handles RB/TE through FLEX but is still narrower than the required roster-wide
opportunity cost. A dead or configuration-ineligible bench WR cannot be dropped for a legal RB
upgrade in an RB-only lineup, despite the WR being the obvious lowest nonstarter and the resulting
roster remaining legal.

The laptop-2 adversarial test remains red against C02A. The add must be legal and the post-swap
roster/lineup feasible; the dropped nonstarter does not need to share the added player's nominal
position or role space.

### One combined weekly move budget — not implemented

Emergency and proactive loops still each receive their own limit. With both limits set to one, a
team can make one emergency claim and then one upside claim in the same week. `moves_left` is the
season cap and does not impose a per-week combined bound. The supplemental test observes two moves
where the contract permits one.

`waiver-realism-v1.json` claims weekly caps are preserved but freezes the two separate defaults
without defining their combined-budget interaction. Correct this append-only; do not rewrite v1.

### Frozen calibration thresholds — still omitted

C02A intentionally leaves calibration artifacts untouched, so the supplemental finding remains:
the executed report does not calculate or explicitly dispose of
`position_or_cohort_material_regression` or `season_evaluator_no_regression_tolerance` from the
reviewer-frozen calibration manifest. An unavailable result must be recorded as failed or
inconclusive; it cannot disappear from the report.

## Independent verification

Reviewer suites against C02A: **7 passed, 2 failed**. The two failures are the dead/ineligible
cross-role bench drop and combined weekly cap described above. The original primary pair is green.
Claude's 17 focused tests and broader receipts reconcile, but do not cover these supplemental
cases. `git diff --check edbcc4d..de42301` is clean.

## Required C02B correction

1. Add an append-only `waiver-realism-v2.json` amendment before code changes. Define one total
   per-team weekly move budget shared by emergency and upside claims and clarify roster-wide drop
   feasibility. Preserve v1 byte-for-byte.
2. Select the lowest forward-looking nonstarter that can be dropped while keeping the resulting
   roster/lineup feasible. Do not require the drop to share the add's role space. Retain the rule
   that a started body is replaceable only when no feasible nonstarter drop exists.
3. Enforce one combined weekly allowance across emergency and upside claims. An emergency move
   consuming the allowance must prevent a second proactive move that week; retain distinct
   counters and the season cap.
4. Run the laptop-2 adversarial suite unchanged and add production-owned equivalents for both
   remaining cases.
5. Complete the executed calibration report's disposition of every frozen threshold, including
   the two omitted thresholds. Do not alter frozen benchmark data, reinterpret existing failures,
   or promote coefficients.
6. Preserve `C02-claude.md` and `C02A-claude.md`; write immutable `C02B-claude.md` and stop for
   re-review. Do not integrate or start C03 production.

All accepted C02A cost behavior and the genuine-breakout acquisition must remain green.
