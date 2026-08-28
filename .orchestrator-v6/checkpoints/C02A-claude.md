# C02A-claude — response to C02-codex BLOCK (decision-rule corrections)

## Identity

- base: `edbcc4d743b447ebcbbfe84a0e1210380c6250d1` (C02 head, the reviewed commit)
- branch: `v6/bench-portfolio`; head = the commit containing this file
- review responded to: `C02-codex.md` at review commit `d50f757` (verdict: BLOCK)
- scope: EXACTLY the six required C02A corrections. All C02-accepted behavior (shared
  pool, reverse priority, weekly/season caps, emergency/upside distinction, K/DST
  streaming, determinism, leakage guard, paired outcome families) and every calibration
  artifact are preserved untouched. No player-value coefficient changed; no failed
  calibration threshold reinterpreted. `C02-claude.md` immutable.
- git identity: Andrew; no assistant attribution; date 2026-08-26

## Correction 1 — manifest frozen BEFORE the behavior change

`.orchestrator-v6/experiments/waiver-realism-v1.json`, committed alone as
`62a9336` ("C02A(1/2)") strictly before any code change (auditable in history). It
freezes: hypotheses; cost units (fantasy points, same scale as started_points);
the decision threshold (strict `>`); the remaining-horizon conversion
(`weeks_left = weeks − 1 − w` for a claim decided after week w); boundary semantics
(equal-or-below-cost never transacts; ties never transact); the retained relative
anti-churn margin (`upgrade_margin = 0.15`, now frozen, explicitly documented as a
dimensionless relative margin and NOT the per-claim cost); role-space
feasibility/drop-selection semantics; single-charge accounting; configs and seeds;
metrics; acceptance tests; and failure interpretation (ambiguity preserves
C02-accepted behavior; calibration out of scope). No existing manifest was rewritten.

## Correction 2 — roster-wide feasible add/drop under actual slot eligibility

`_best_upgrade` now takes the league's `slots` and evaluates the ROLE SPACE of every
free agent: the slots it is eligible for under `slot_positions` over the row's actual
starting slots. Drop candidates are squad bodies sharing at least one eligible slot —
identical nominal positions are NOT required, so a FLEX-eligible TE can replace a
FLEX-space RB. Selection is the lowest forward-looking nonstarter in that role space
(believed projection, deterministic tie-break); only a role space containing no
nonstarter may replace a started body, which is exactly the K/DST streaming case the
C02 review accepted (and which prevents a high-scoring K from hoovering skill-position
bench slots through raw cross-position projection comparison). A body eligible for no
slot at all is an infeasible add and is never claimed, at any cost. With `slots=None`
(the reviewer probe's direct-call form) the role space is unconstrained and the drop
candidate is the lowest-believed-projection body, per the manifest's no-slots fallback.

The reviewer's failing reproduction (low FLEX-space RB nonstarter + materially better
free TE) now returns the swap; `engine/tests/test_v6_c02_decision_adversarial.py`
passes unmodified against production code (run with the worktree PYTHONPATH form from
the reviewer tree — the file itself remains reviewer-owned and was not copied).

## Correction 3 — transaction cost is part of the claim decision

`waiver_cost` (points) now reaches `_run_waivers` and `_best_upgrade` and gates BOTH
claim kinds: a claim executes only when per-week believed gain × `weeks_left`
STRICTLY exceeds the cost. Upside gain = `proj[add] − proj[drop]`; emergency gain =
`proj[add]` (the alternative is a 0-point hole). The C02 season-aggregation charge is
retained exactly as documented (one charge per executed claim into
`per_season`/`started_points`; H2H and proxies stay on-field) — the gate is a
comparison, not a second charge, so nothing is double-charged. The reviewer's
`waiver_cost=10_000` reproduction now executes zero claims (doubly dead in that
fixture: cost-vetoed and slot-infeasible).

## Correction 4 — adversarial tests (all in `engine/tests/test_waiver_realism.py`)

- Cross-position FLEX substitution: direct `_best_upgrade` with slots (started
  FLEX RB → free TE) and end-to-end through `evaluate_rosters` (bench RB → free TE,
  with the rival seat blocked by its own margin gate).
- Infeasibility: a 30-ppw free RB in a QB-only league never claims.
- Cost boundaries: gain 5 ppw × 3 weeks = 15 points; cost 14.9 executes, 15.0 and
  15.1 do not (strict `>` on both sides of the boundary).
- Emergency cost gate: the same bye-hole fixture that forces an emergency claim at
  cost 0 executes nothing at cost 10 000.
- Genuine in-season breakout: preseason prior 1 ppw (below every incumbent), realized
  30 ppw. Acquired once point-in-time observations lift the shrunk forecast past the
  margin gate; NOT acquired when the only waiver window precedes any observation of it
  (trajectory proof); NOT acquired in the no-breakout control with the same prior.

## Correction 5 — preservation

All 11 C02 realism tests pass UNCHANGED (the corrected rule reproduces their expected
behavior, including K/DST streaming, contested pool, caps, counters, determinism
across all nine result arrays, proxies, `paired_ci`, and the live leak guard). The
bench-insurance contrast and every other pre-C02A evaluator acceptance property pass
in the full suite below. Calibration artifacts, boards, hashes, `promotion-v3`
collision record, and thresholds: untouched. Player-value coefficients: untouched.
The one frozen new constant set is the manifest's own (margin 0.15 = the C02 default,
now preregistered; `waiver_cost` default 0.0 keeps the gate inert by default).

## Correction 6 — this record

`C02-claude.md` preserved byte-identical; this file is immutable once committed.

## Verification (this worktree)

- reviewer probe: `test_v6_c02_decision_adversarial.py` **2/2 passed** against
  production code (reviewer tree file, prod PYTHONPATH).
- engine: ruff clean on changed files; `tests/test_waiver_realism.py` **17 passed**
  (11 preserved + 6 new); full suite **4140 passed, 1 skipped** (worktree PYTHONPATH
  form).
- pipeline: **157 passed** (untouched). frontend: untouched since the C02-certified
  492/492 at `edbcc4d` (no frontend file in this diff).
- `git diff --check` clean; reviewer worktree untouched; no integration, no C03, no
  push, no merge.

## Stop

Stopping for independent re-review. The disposable C03 compatibility branch must be
recreated from C02A per the review; that recreation belongs to its owner, not to this
checkpoint.
