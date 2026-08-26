# v5 E12 — static ↔ dynamic reconciliation: **Outcome B, justified divergence**

**Chosen outcome: B (justified divergence). Not A (unification).** The brief asked for the
web tier's cost to be *measured*, not asserted, and the measurement inverts the premise of
unification. Seated in the same league, on the same board, with the same seed and the same
seasons, the **shipped dynamic policy scores −23.7 started_points/season *against* the static
formula** (CI95 [−65.9, +18.9], n = 36). There is nothing to transport. Building a
feature-vocabulary bridge today would spend the web tier's complexity budget importing a policy
that is *behind* the closed form it would replace. The split stands — see
`[[draft-formula-static-dynamic-split]]`, which this unit **confirms with numbers** rather than
overturning.

The falsifiable condition that flips this to Outcome A is stated in §6. It is already
half-satisfied, which is why this is a "not yet", not a "never".

---

## 1. What was measured, and why this design

Both tiers are graded by one yardstick: E5's imperfect-information season metric
(`started_points`, higher is better, `engine/blitz_engine/simulation/season_eval.py`).

The obvious experiment — seat the real TypeScript policy and the dynamic policy in the same
draft — is **not affordable and not allowed**. `docs/design/v5-architecture.md` §5 fixes the
bridge at *one node process per draft*; seating TS inside `draft_league` needs one per *pick*.
So the comparison uses the seat structure E5 already has:

- `season_eval.DEFAULT_POLICY_MIX = ("static_proxy", "vorp_adp", "engine_msv")`. Seats are
  assigned deterministically from the config seed, and `SeasonEvalResult.seat_policy` labels
  every column of `per_season`.
- `static_proxy` is E5's Python stand-in for `frontend/lib/draftAI.ts` — **the static tier's
  decision rule, closed form, no per-pick simulation.**
- `real_env.evaluate_seated(policy, …)` (E11) replaces the `engine_msv` seats with a given
  Python policy — **the dynamic tier.**

One league run therefore yields both tiers' `started_points` **on the same board, from the same
pool, under the same availability/injury/bye draws**. Paired per (config, season). This is
strictly better than differencing E10's and E11's published edges: those were measured against
*different baselines* in *different league compositions* and are not commensurable.

**Grid (identical to E11's, deliberately):** years `2018, 2021, 2024` × rows
`t8-1qb-std-te0.0-b4-ir0`, `t12-1qb-half-te0.5-b8-ir0`, `t10-2qb-ppr-te0.0-b8-ir1`;
`n_seasons=4`; **seed 20260825**. 36 paired points per contrast. CIs are
`blitz_engine.value.rl.train.bootstrap_ci` (2000 resamples, same seed).

> **Read only the within-league paired gaps, never the absolute levels across runs.** The board
> is zero-sum: when a weaker policy holds the `engine_msv` seats, `static_proxy`'s absolute level
> *rises* because better players fall to it (1598.2 in run 1 vs 1555.4 in run 3 below). The gaps
> are the finding; the levels are league-composition artefacts.

## 2. The three numbers

| # | Contrast (same league, same seed) | mean pts/season | CI95 | n |
|---|---|---|---|---|
| 1 | **shipped dynamic tier − static tier** (`FastDraftPolicy()` seated vs `static_proxy`) | **−23.73** | [−65.94, +18.95] | 36 |
| 2 | naive ADP baseline − static tier (`vorp_adp` vs `static_proxy`) | −136.87 | [−179.19, −94.23] | 36 |
| 3 | **E5's native per-pick picker − static tier** (`engine_msv` unseated vs `static_proxy`) | **+82.68** | [+43.11, +122.51] | 36 |

Per-config decomposition of contrast 1 (the "concentrated where?" the brief demanded):

| slice | mean | CI95 |
|---|---|---|
| `t12-1qb-half-te0.5-b8-ir0` | **−117.52** | [−177.33, −58.75] |
| `t8-1qb-std-te0.0-b4-ir0` | +2.32 | [−77.80, +82.25] |
| `t10-2qb-ppr-te0.0-b8-ir1` | +44.02 | [−11.65, +96.10] |
| year 2018 | −100.19 | [−183.94, −6.00] |
| year 2021 | +42.00 | [−18.79, +99.67] |
| year 2024 | −12.99 | [−57.53, +32.10] |

Absolute levels (run 1 / run 3): `static_proxy` 1598.2 / 1555.4 · `engine_msv` 1574.5 (seated
with `FastDraftPolicy`) / 1638.0 (native) · `vorp_adp` 1461.4 / 1464.4.

## 3. What the numbers say

**(a) The web tier's measured cost of having no per-pick simulation is, today, not
distinguishable from zero — and the sign is against the dynamic tier.** −23.7 pts/season on a
~1560-point base is −1.5 %, CI straddling zero. For scale, contrast 2 shows what a genuinely
worse rule costs: −136.9, −8.6 %, CI nowhere near zero. The static closed form is not a degraded
approximation of the dynamic tier; on this evidence it *is* the stronger of the two shipped
policies.

**(b) But the headroom for per-pick reasoning is real, and large.** Contrast 3 is the same
seats, the same grid, the same seed, with E5's own marginal-starter-value picker left in place:
**+82.7 [+43.1, +122.5]**. A per-pick decision rule *can* beat the closed form by ~5 %. So the
architecture's premise is sound; the current *implementation* of the dynamic tier is not
cashing it. The shipped `FastDraftPolicy` forfeits roughly **106 pts/season** of an edge that is
demonstrably on the table (+82.7 available, −23.7 delivered).

**(c) This independently confirms E11's diagnosis.** E11 found distillation *succeeding*
(MCTS agreement 0.357 → 0.643) while the metric got *worse*, and concluded the lever is the leaf
evaluator, not more search. Contrast 3 is the corroboration from the other side: when the
per-pick rule's evaluation *is* marginal starter value computed live, it wins big; when the
per-pick rule is a 4-feature linear copy of a search whose leaf is a static roster sum, it
loses. **The dynamic tier's defect is its evaluation function, not its lack of expressive
power** — and 4 features are not the binding constraint either (E11's fitted `equity` and `vona`
came out numerically identical, i.e. the 4 are already collinear on the real board; the policy
is not using the capacity it has).

**(d) Where the dynamic tier loses is where insurance lives.** The worst slice by far is
`t12-1qb-half-te0.5-b8-ir0` (−117.5, CI entirely below zero): 12 teams, **8 bench slots**, TE
premium — the deepest bench and the thinnest waiver wire on the grid. It wins (insignificantly)
on the 2QB/PPR row where the scarcity signal is loud and shallow. A leaf evaluator blind to
byes, inactives and waiver holes should fail exactly on the deep-bench, thin-wire config. It
does.

## 4. Proxy fidelity — how much does `static_proxy ≠ draftAI.ts` cost this argument?

This is the one honest weakness, named by E10 and unresolved here. It is **bounded**, not
hand-waved:

- E10 drove the **real** `draftAI.ts` over `frontend/scripts/draft-eval.mjs` on the 16 `smoke()`
  rows, season 2024, `n_seasons=8`, seed 20260825. Its incumbent (arm-B) `mae_without` ranges **1453.9–1456.4** across the six candidates
  → real-TS mean `started_points` = `CEILING(3000) − mae_without` = **1543.6–1546.1**
  (`engine/experiments/static/results.json`).
- The same rows/season/seasons/seed with E5's mix gives `static_proxy` = **1527.1**.
- Difference **≈ +16.5 to +19.0 pts/season (~1.1 %), in the real policy's favour.**

Confound stated plainly: E10's league is all-TS seats, E5's is the three-policy mix, so this is
an anchor, not an identity. But its *direction* is the one that matters — if the proxy
**understates** the static tier by ~1 %, contrast 1 (−23.7 for the dynamic tier) is if anything
**conservative** in the static tier's favour. The conclusion does not depend on closing this gap.
Closing it properly means seating the TS bridge per-pick, which §5 of the architecture forbids
on cost grounds; a cheaper route is listed in §7.

## 5. The E6 ↔ E10 tension: shape vs lever, and why both are right

E6 refuted a flat `byeStackPenalty` using a **derived roster-shape ablation** — it constructed
bye shapes directly over its own arm policies (cluster +18.9/+16.0/+12.4 on ≥7-slot benches,
−23.6/−15.3 reversal on 6-slot). E10 implemented that exact conditional rule as a **lever inside
the shipped `scoreBoard`** and measured it worse (−10.4, neutral, `no_regression` FAIL), with
dropping the penalty also worse (−9.0).

**These do not contradict each other; they measured different objects.** E6 answers *"is this
roster shape better?"* — it can place a roster in the target shape by construction. E10 answers
*"does moving this scalar knob reach that shape?"* — inside `scoreBoard` the penalty competes
with `emptyOffensiveStarterBonus`, overfill and the K/DST terms, and a knob that is right about
the destination can still be the wrong steering wheel. **A shape can be right while the lever
that reaches it is not.** Neither result licenses changing a weight, and E10 correctly shipped
the conservative read: `byeStackPenalty` stays flat 12, with the mechanism
(`byeStackDeepBenchSlots: 99` / `byeStackPenaltyDeepBench: 12`) shipped **inert and
bit-identical to E1**, so arming it later costs nothing.

E12 adds one piece of evidence: §3(d) shows the deep-bench config is also exactly where the
*dynamic* tier collapses. Two independent tiers failing on the same config is weak evidence that
**bench depth is a real conditioning variable and neither tier currently conditions on it
correctly** — but it is *not* evidence that `byeStackPenalty` is the right place to condition.
Settling it requires reporting both surfaces for one candidate: gate the conditional rule
through `scoreBoard` (E10's surface) **and** through E6's constructed-shape surface, in one run,
and show whether the lever moves the shape at all. That is a v6 item (§7) — the brief forbids
refitting here, and doing it half-way is how an unproven weight ships.

## 6. Decision, and the condition that overturns it

**Decision.** Two formulas, by design, unchanged. `frontend/lib/draftAI.ts` keeps its ~20-knob
closed form and remains the *stronger* shipped policy; `engine/blitz_engine/value/policy.py`
keeps `FEATURE_NAMES = ("equity","vona","run_prob","need")` and `DEFAULT_WEIGHTS`. **No
feature-vocabulary bridge is built.** No weight changed in this unit, so block-release is
satisfied trivially: nothing shipped needs an ablation receipt.

What connects the tiers is **not** a weight pipe. It is the two artefacts that already exist and
should be treated as the contract:

1. **The metric** — E5 `started_points` is the single yardstick both tiers are gated on. Any
   future transport must clear it on both sides.
2. **The evaluation bridge** — `frontend/scripts/draft-eval.mjs` + `static_fit.py` (E10). The
   web tier gets *offline* feedback from simulation, never online search. That is the correct
   shape of the relationship and it is already built.

**Falsifiable condition for Outcome A (unification becomes right).** Build the bridge when a
dynamic policy, seated by `evaluate_seated` on **this grid and this seed**, beats `static_proxy`
with a **CI95 lower bound strictly above 0** — i.e. reproduces something like contrast 3's
+82.7 [+43.1, +122.5] with a *learned* policy rather than E5's own picker. At that point the
dynamic tier holds value the web tier demonstrably lacks, and translating 4 features into 20
knobs is worth its complexity. Until then the seam stays open and unused, and that is the
cheap, correct state.

**What would *not* flip it:** a higher MCTS agreement score, more PPO steps, or more features.
E11 showed agreement rising while the metric fell; §3(c) shows capacity is not the binding
constraint. Agreement is not evidence about this decision.

## 7. v6 items this reconciliation surfaced (recorded, not done)

- **Swap the MCTS leaf evaluator** from the static `starter_value` roster sum to a
  simulation-priced leaf (E11's `equity_evaluator` / `p_champion`) on the real board. This is the
  single experiment both E11 and §3(c) point at. Everything else is downstream of it.
- **Variance-reduced RL reward** (common random numbers across rollouts, antithetic availability
  draws). E11's PPO got *worse* when scaled — the signature of reward noise, not of a bad
  objective.
- **Close the proxy gap cheaply:** rather than seating TS per-pick, run E10's bridge and an
  E5-mix league on an identical row/season/seed pair with matched seat composition, and publish
  a per-config `static_proxy → draftAI.ts` correction table. §4's ±1 % anchor becomes a
  calibrated offset.
- **Settle shape-vs-lever (§5)** by gating one bye candidate on *both* decision surfaces in a
  single run.
- **Back-test the remaining ~14 `DEFAULT_POLICY` knobs** plus `GENERAL_WEIGHTS` /
  `GENERAL_PENALTIES` / `SF_QB_WEIGHTS` — still hand-authored (E10's named gap), and `matrix.all()`
  (432 rows) has never been swept.

## 8. Reproducing every number in this document

Prerequisite: `pipeline/.venv` (Python 3.12). From a linked worktree, prefix
`PYTHONPATH=<worktree>/engine` or you will test the main checkout's code.

`§2 contrasts 1–2 and the per-config decomposition` — save as `xtier.py`, run
`cd engine && ../pipeline/.venv/bin/python xtier.py`:

```python
import json
import numpy as np
from blitz_engine.simulation import season_eval as se
from blitz_engine.testing import matrix
from blitz_engine.value.policy import FastDraftPolicy
from blitz_engine.value.rl.real_env import evaluate_seated, real_pool
from blitz_engine.value.rl.train import bootstrap_ci

ROWS = ["t8-1qb-std-te0.0-b4-ir0", "t12-1qb-half-te0.5-b8-ir0", "t10-2qb-ppr-te0.0-b8-ir1"]
YEARS = [2018, 2021, 2024]
SEED, NS = 20260825, 4
by_id = {r["id"]: r for r in matrix.all()}
acc, levels = {}, {}
for y in YEARS:
    for rid in ROWS:
        out = evaluate_seated(FastDraftPolicy(), y, by_id[rid],
                              config=se.EvalConfig(n_seasons=NS, seed=SEED),
                              players=real_pool(y, rid))
        ps, sp = np.asarray(out.result.per_season), out.result.seat_policy
        m = {lab: ps[:, [i for i, p in enumerate(sp) if p == lab]].mean(axis=1) for lab in set(sp)}
        for lab, v in m.items():
            levels.setdefault(lab, []).extend(float(x) for x in v)
        d = [float(a - b) for a, b in zip(m["engine_msv"], m["static_proxy"])]
        for k in ("dyn_minus_static", f"row:{rid}", f"year:{y}"):
            acc.setdefault(k, []).extend(d)
        acc.setdefault("vorp_minus_static", []).extend(
            float(a - b) for a, b in zip(m["vorp_adp"], m["static_proxy"]))
res = {k: {"n": len(v), "mean": round(float(np.mean(v)), 2),
           "ci95": [round(x, 2) for x in bootstrap_ci(v, seed=SEED)]} for k, v in acc.items()}
res["levels"] = {k: round(float(np.mean(v)), 1) for k, v in levels.items()}
print(json.dumps(res, indent=1))
```

`§2 contrast 3` — identical, but call
`se.evaluate_season(y, by_id[rid], config=se.EvalConfig(n_seasons=NS, seed=SEED), players=real_pool(y, rid))`
in place of `evaluate_seated(...)` (leaving `engine_msv` native) and read
`engine_msv − static_proxy` → `+82.68 [43.11, 122.51]`, levels `static_proxy 1555.4 /
engine_msv 1638.0 / vorp_adp 1464.4`.

`§4 proxy anchor` — `static_proxy = 1527.1` over `matrix.smoke()` (16 rows), season 2024,
`n_seasons=8`, seed 20260825:

```python
import numpy as np
from blitz_engine.simulation import season_eval as se
from blitz_engine.testing import matrix
vals = []
for row in matrix.smoke():
    r = se.evaluate_season(2024, row, config=se.EvalConfig(n_seasons=8, seed=20260825))
    cols = [i for i, p in enumerate(r.seat_policy) if p == "static_proxy"]
    vals.extend(np.asarray(r.per_season)[:, cols].ravel().tolist())
print(round(float(np.mean(vals)), 1), len(vals))
```

The real-TS side of §4 is E10's committed receipt, not re-run here:
`engine/experiments/static/results.json` → each arm's `mae_without` (1453.9–1456.4); level =
`static_fit.CEILING (3000) − mae_without`. Regenerate with
`cd engine && ../pipeline/.venv/bin/python -m blitz_engine.backtest.static_fit --all --seasons 8`
(needs `npm ci` in `frontend/`).

E11's own figures (−60.2 [−93.3, −25.7] distilled; −26.7 [−45.7, −7.2] PPO; agreement
0.357 → 0.643) are quoted from `engine/experiments/dynamic/` and reproduce via
`experiments/dynamic/run_dynamic_fit.py`, seed 20260825.
