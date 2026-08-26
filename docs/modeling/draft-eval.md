# The draft evaluation metric (v5)

**THE METRIC = `blitz_engine.simulation.season_eval.SeasonEvalResult.started_points`**
(league mean = `.metric`). Every weight fitted, gated or rejected in the v5 cycle was scored on
this and nothing else. Code: `engine/blitz_engine/simulation/season_eval.py`; tests:
`engine/tests/test_league_sim.py`. It **replaces** the perfect-hindsight metric documented in
`docs/modeling/backtest-report.md`, which is retired.

## 1. What it measures, in one sentence

**The fantasy points a team's LOCKED starting lineup actually scored, once you can no longer see
the future.** Higher is better.

Concretely: fewer slots left empty or zeroed by a bye, an injury or an inactive you did not know
about at lock time, and better start/sit calls from information available *before* the week.

It is **not** total roster production and **not** a projection-accuracy score. Adding a
high-scoring player who never fills a starting slot does not raise it.

## 2. How a score is produced

- **Population.** Every seat of one `fixtures/league_matrix.json` row, drafting from one
  `fixtures/seasons/<year>.json` corpus pool.
- **Horizon.** All *W* regular-season weeks of that corpus season (W=18 for 2024). **No playoff
  bracket** — `simulate_league` still owns playoff odds.
- **Averaging.** Over `EvalConfig.n_seasons` sampled availability/injury trajectories.
- **Entry point.**
  ```python
  from blitz_engine.simulation import season_eval as se
  res = se.evaluate_season(year, row, config=se.EvalConfig(...))   # row = an E7a matrix row dict
  res.metric            # league mean (float)
  res.started_points    # per seat
  res.per_season        # (n_seasons, teams) PAIRED matrix
  res.by_policy()       # per-policy read-out
  ```
  Feed `.per_season` **straight** to `backtest.ablation.paired_permutation_p`; do not re-derive it.
- **Cost.** One season × one config = **20.2 ms** warm (12 teams × 18 weeks). One mixed-policy
  draft = 47 ms; `build_players` = 80 ms. The 16-row `smoke()` sweep at `n_seasons=1` ≈ 5 s.
  `matrix.all()` (432 rows) is gated behind `BLITZ_EVAL_FULL=1` and has never been run.

## 3. The three design decisions that make it work

**(a) Production and availability are FACTORISED.** The corpus's realised week is read as *"what
he scores if he plays"* (a `null` week → his own realised median game); **whether he plays is
sampled** — E2a's `AvailabilityModel().p_startable` on `depth_rank`, × E3's clinical-injury chain
(E4's `InjuryDynamics.sample_weight`), × bye. History's own absences therefore never leak into the
manager's decision. Because E3's event carries **zero snap-presence signal**, the two draws do not
double-count; a test asserts `"clinical" in dyn.event` so a future refit toward a snap proxy fails
loudly rather than silently squaring the same signal.

**(b) What the manager knows at lock time is bounded, and the bound is tested.** Known: weeks `< w`
actuals, the pre-season projection, byes, and last week's injury report (chain state at `w−1`).
**New-onset injury at `w` and the availability draw resolve AFTER lock.** That is the entire
imperfect-information seam and the only thing a bench can insure against.
`backtest.harness.detect_leakage` runs on `(decision, week-w)` every week of every season;
`evaluate_rosters(..., leak={"week": 5})` is the test hook that proves the guard is live.

**(c) Seats play a MIX of policies, so H2H is not 50 % by construction.**
`DEFAULT_POLICY_MIX = ("static_proxy", "vorp_adp", "engine_msv")`, assigned by a seed-shuffled
round robin. Measured at `n_seasons=4`: engine_msv .59 / static_proxy .52 / vorp_adp .39.
`test_mixed_policy_h2h_is_non_degenerate` asserts the leader beats .52 with p<0.05 across 4 seeds.
The v2.4 harness ran all 12 teams on the *same* policy, which is why every H2H row in
`backtest-report.md` reads exactly 50.0 %.

**Seeding.** One seed (`EvalConfig.seed`, default `SEASON_EVAL_SEED = 20260825`) drives everything:
draft seating `seed+303`, injury paths `seed+101+s`, availability `seed+202+s`, waivers from
standings. Same seed ⇒ bit-identical `per_season` (asserted with `array_equal`, not `allclose`).
No global RNG anywhere.

## 4. How it differs from the retired metric — and the proof it matters

The retired metric (`hindsight_points`, v2.4 "season points-for") scored a **perfect-hindsight
weekly-optimal lineup**: you start whoever actually scored. Depth therefore pays off far less than
in a real season, because you never start the wrong guy and never leave a slot empty by surprise.

| | retired (`hindsight_points`) | current (`started_points`) |
|---|---|---|
| lineup | weekly-optimal *ex post* | **locked** from pre-week information |
| availability | realised history, implicitly | **sampled** (E2a × E3 × bye) |
| leakage | unguarded | `detect_leakage` every week |
| opponents | 12 identical policies | 3-policy mix |
| waivers | none | contested, reverse-standings priority |
| bench insurance | structurally invisible | **visible** |

**The acceptance test — run it, it is the whole argument:**

```sh
cd engine
../pipeline/.venv/bin/python -m pytest tests/test_league_sim.py -k bench_insurance
```

On the **same two rosters**, the bench-insurance ablation moves:

- the **new** metric **+19.5 pts/season (+1.35 %), p=0.0055** — significant;
- the **retired** metric **+43.9, p=0.2295** — not significant. `starts_lost` 32.5 vs 34.0.

The eval moved; hindsight stayed blind. This is why every negative result in the v5 cycle is
informative: a "did not help" verdict is only meaningful from a metric that can see the effect
when it is there.

`hindsight_points(players, rosters, row)` is **kept in the codebase for this contrast only.**
Never tune against it.

## 5. Known limitations — read before quoting a number

1. **Absolute levels are league-composition artefacts. The board is zero-sum.** `static_proxy`
   reads 1598.2 when a weak policy holds the other seats and 1555.4 when a strong one does, purely
   because better players fall to it. **Only within-league paired gaps are meaningful.** Never
   compare absolute levels across runs.
2. **`static_proxy` is a PROXY, not `frontend/lib/draftAI.ts`.** It is a Python VORP + need +
   injury-cover opponent model (its injury weights read from `fixtures/injury_rates.json`, nothing
   hard-coded). Porting the real TS policy into Python was rejected as the two-copies-drift failure
   `v5-architecture.md` §5 exists to prevent. E10 swapped it for the real policy over the node
   bridge for its own fit; E5's simulator still seats the proxy. E12 §4 **bounds** the gap at
   ~1.1 % in the static tier's favour but does not close it.
3. **Deliberate omissions:** no playoff bracket, **no trades**, no FAAB, no speculative stashes, no
   handcuffing, no non-hole-driven waiver add. The trade omission is load-bearing: `TradeValue` has
   **zero gradient** under this metric, so it must be pinned or ablated, **never free-fit** — a
   free fit on a zero-gradient knob produces a confident meaningless number.
4. **No K/DST streaming.** Waivers fill only genuinely unfillable slots, so the metric
   over-rewards locking in a good kicker early. 6 of E6's 16 K/DST timing rows are flagged
   `confidence="low"` for exactly this reason.
5. **Waivers are load-bearing when tuning bench value.** `EvalConfig(waivers=False)` roughly
   *doubles* the bench effect (+36 pts) — waivers are what price a bench's opportunity cost. Leave
   them on.
6. **Only 16 of 432 configs are ever simulated.** Every fit in the cycle ran `matrix.smoke()`.
7. **The upstream models carry their own residuals** — notably E3's under-prediction of week-1
   absences (~8 predicted vs ~22 actual WRs), because training-camp injuries have no preseason
   exposure anywhere in the store.

## 6. The semantic trap this metric exposed

`DEFAULT_POLICY.injuryRate` is documented as *"the expected fraction of a season a starter at pos
misses"* — an **availability-like** quantity. E3's fitted rates are **clinical incidence**. These
are **different quantities** and they must not be conflated.

Swapping E3's numbers into the knob was measured and **HURTS: −14.0 pts, p=0.0015**
(`exp e10-injury_rate_clinical`). Availability is E2a's `p_startable`, published to
`player_availability` and multiplied in `scoreBoard` separately — which is exactly why
`faPenalty` and `injuryDiscount` were deleted from `PolicyParams` rather than re-fitted.

`fixtures/injury_rates.json` carries an explicit `"event"` string naming its semantics. Read it
before baking.

## 7. Related

- `docs/modeling/experiments.md` — every fit, seed and command.
- `docs/modeling/backtest-report.md` — the retired metric, kept and marked superseded.
- `docs/design/v5-static-dynamic.md` — E12's cross-tier measurement built on this metric.
- `docs/decisions/2026-08-25-v5-perfect-the-draft.md` — what the cycle decided and reversed.
