# BENCH_MODEL — what a fantasy-football bench is *for*

The v5 yardstick. E6 derives positional counts from §2, E8 turns §4 into property assertions,
E10/E11 fit weights toward §3. Companion: `docs/design/v5-architecture.md` (layering, the 432-row
config matrix), `docs/design/v4-bench-scoring.md` (the hand-authored tables this cycle backtests).

Every number here is either **cited**, **derived** from a cited number (arithmetic shown), or
explicitly labelled **guess — test in E6/E10**. Nothing else is asserted.

---

## 0. The frame

A bench is not "the next-best players." It is a **portfolio of options on future starting-lineup
weeks**, priced against what the waiver wire would have given you for free in that same week.

```
BenchValue(b) = Σ_{w=1..17}  P(b starts in week w) · E[ PF(b,w) − PF(waiver_best(pos,w)) | b starts ]
```

Two consequences the current code does not encode:

1. **The baseline is the in-season waiver player, not the draft-day replacement.** This is why every
   count below is a function of league config: waiver quality falls as `teams × rostered_depth`
   rises past the NFL's supply of startable players at that position. Value-based drafting sets the
   replacement baseline by exactly this product
   (<https://www.fantasypros.com/2025/06/fantasy-football-draft-strategy-value-based-drafting-vorp-vols-vona/>:
   "the replacement threshold is league size × roster spots at that position").
2. **`P(b starts)` decomposes by cause**, and the causes are the roles. Bye (scheduled, known),
   absence (hazard), promotion (role change), matchup (streaming). The roles in §1 partition that
   probability; they are not a taxonomy for its own sake.

### 0.1 Notation used throughout

| symbol | meaning |
|---|---|
| `T` | `teams` (8/10/12/14) |
| `S(pos)` | starting slots at `pos`, derived per v5-architecture §3 |
| `b(pos)` | bench players held at `pos` |
| `B` | `bench_slots` (4/6/8) — the budget the whole allocation spends |
| `IR` | `ir_slots` (0/1) |
| `N(pos)` | NFL supply of *startable* players: QB 32, TE 32, K 32, DST 32, RB ≈ 36, WR ≈ 96 |
| `R(pos)` | replacement rank = `T·(S(pos)+b(pos)) + 1` |
| `σ(pos)` | **waiver scarcity** = `R(pos) / N(pos)`. `σ > 1` ⇒ the wire cannot supply a starter |
| `h(pos)` | expected fraction of the season a starter at `pos` misses (the `injuryRate` table) |

`R(pos)` as a linear function of `T` is empirically confirmed: published replacement ranks are
QB13/TE13/RB25/WR37 at 12 teams, QB11/TE11/RB21/WR31 at 10, QB15/TE15/RB29/WR43 at 14
(<https://sticktothemodel.com/blog/fantasy-football-vorp-explained-2025>) — i.e. slopes of
1·T for QB and TE, 2·T for RB, 3·T for WR, plus one. Our `R(pos)` reproduces these exactly when
`b(RB)=b(WR)=0` and flex is charged to RB/WR.

---

## 1. The roles

### R1 — Bye cover

- **signal.** `BYE_WEEKS_2026[team]` of the *incumbent* at the slot, joined to `σ(pos)`. A bye is
  only a *role* when `σ(pos) > 1` in the bye week; below that, the wire covers it for free.
- **value.** One week of `(starter − waiver_best)` at that slot ≈ `VOR_weekly(pos)`. Bounded and
  small: one week out of 17.
- **count-vs-config.** `b_bye(pos) = 1 if σ(pos) > 1 else 0`. In practice: 0 for every position in
  `1qb`; 1 (QB) in `superflex`; 1–2 (QB) in `2qb`. Byes are *known at draft time*, which makes this
  the cheapest role to fill and the one least deserving of draft capital.

**Our model — we depart from consensus here.** Consensus says spread your byes. A 50,000-season
Monte Carlo says the opposite: clustering all eight starters onto one bye week produced 501,247
wins vs 361,972 (moderate clustering) and 336,781 (spread), because you concede one week to run at
full strength in the other seven (<https://www.4for4.com/fantasy-football-bye-week-management>).
That simulation assumes **no bench**. With `B ≥ 6` a bench absorbs a stack, so the correct penalty
is not "spread" or "cluster" but *a function of whether the bench can cover the stack*:
`byePenalty ≈ max(0, starters_on_bye − coverable_by_bench(B, σ))`. Current code applies a flat
`byeStackPenalty: 12` per stacked starter — unconditional in `B`. This is the constant we believe
is most likely wrong. → prediction P1.

### R2 — Injury / absence cover (depth)

- **signal.** `resolve_status_p` / `AvailabilityModel` (`engine/blitz_engine/survival/availability.py`) for the
  incumbent, plus the positional base hazard `h(pos)`, plus current `injury_status`.
- **value.** `Σ_w P(incumbent out in w) · (bench − waiver_best)`. Unlike a bye this is *unscheduled*,
  so the wire has already been picked over by the time you need it — the waiver baseline is lower
  and the role is worth more per week than R1.
- **derived hazards.** From per-game injury rate × mean games missed, 2015 NFL season
  (<https://www.profootballlogic.com/articles/nfl-injury-rate-analysis/>: RB 5.2%/game, 3.9 games;
  WR 4.5%/3.2; TE 4.9%/2.6; QB 2.5%/3.1; league mean 4.1%/game):

  | pos | injuries/season = rate·17 | × mean games | = games missed | `h(pos)` = /17 | current `injuryRate` |
  |---|---|---|---|---|---|
  | RB | 0.88 | 3.9 | 3.44 | **0.20** | 0.18 |
  | WR | 0.77 | 3.2 | 2.45 | **0.144** | 0.12 |
  | TE | 0.83 | 2.6 | 2.17 | **0.127** | 0.12 |
  | QB | 0.43 | 3.1 | 1.32 | **0.078** | 0.08 |
  | K | — | — | — | ~0.02 (guess) | 0.03 |
  | DST | n/a (a unit, not a player) | — | — | **0.0** | 0.0 |

  Independently corroborated over 2021–2025: top-100-ADP RBs miss ~3.3 games/yr, WRs ~2.8, and
  "any player picked at random misses ~3 games per year"
  (<https://rotobanter.beehiiv.com/p/are-running-backs-more-injury-prone-than-receivers>).
- **the missing conditioning.** The same source splits by ADP: top-24 RB/WR miss 2.4/2.2 games;
  rounds 3–5 miss 3.3/2.8; rounds 6–8 miss 3.8/3.3. A **flat per-position rate over-penalises elite
  starters and under-penalises late-round depth** by ~50% at the tails. `injuryRate` should be
  `f(pos, adp_tier)`. → prediction P8.
- **count-vs-config.** `b_inj(pos) = ceil(S(pos) · h(pos) · σ(pos) · 17)` weeks-of-coverage,
  rounded to slots. At `T=12, 1qb`: RB `2.5·0.20·0.86` ⇒ ~2; WR `3·0.144·0.39` ⇒ ~1; TE/QB ⇒ 0.

### R3 — Upside / lottery stash

- **signal.** `opportunity_trend`, `target_share_trend`, `routes_run` / `routes_trend`,
  `offense_snap_pct` trend, and the ADP-vs-projection gap. Depth-chart rank is *not* the signal —
  usage trend is.
- **value.** `P(convert to weekly starter) · (starter − waiver) · weeks_remaining`. Measured: of 25
  late-drafted team-WR1s over 2020–2025, 9 broke out (**36%**), ~2 per season, averaging **191
  half-PPR points ≈ a WR15 finish**
  (<https://www.thefantasyfootballers.com/analysis/the-late-round-wrs-nobody-wants-but-should-fantasy-football/>).
  Against a ~120-point replacement WR that is ~70 points of surplus, so
  **EV ≈ 0.36 × 70 ≈ 25 points per stash per season**. This number recurs below — it is the
  opportunity cost of every non-stash bench slot.
- **count-vs-config.** This is the **residual**: `L = B − Σ_pos (b_bye + b_inj + b_stream)`. The
  marginal bench slot always goes here once coverage is satisfied. `L` grows with `B` and shrinks
  with `T` (deeper leagues spend more of the budget on coverage).

### R4 — Handcuff

- **signal.** Same NFL team as an owned RB **and** share of early-down carries — not
  `depth_chart_order`. The split is the whole story.
- **value.** Nine seasons, 283 team-seasons: primary backups finished RB24+ **13.8%** of the time vs
  **10.5%** for a random bench back — an edge of "roughly three extra percentage points"
  (<https://www.fantasyfootballblueprint.com/2026/08/06/10-handcuffing-running-backs/>). The same
  study: starters miss 6+ games in only **15.2%** of team-seasons, and even then the backup hits
  RB24+ just **23.3%** of the time. Longer view: of 71 backups to first-round RBs since 2010, only
  **8 (11.3%)** produced top-24 seasons
  (<https://www.sharpfootballanalysis.com/fantasy/fantasy-football-handcuff-history-cheap-rb1s-and-ambiguous-backfields/>).
- **the committee inversion.** Conditional on the starter missing 3+ games, a *clean* backup
  (<35% early-down carries) hit RB24+ **6.5%** of the time; a back already at ≥35% hit **29.3%**
  (blueprint, above). **The cleaner the handcuff, the worse it performs.** A single
  `handcuffAmplify` scalar cannot express this: the correct multipliers relative to a random bench
  back are `29.3/10.5 = 2.8` for committee backs and `6.5/10.5 = 0.62` for clean backups.
- **Our model — handcuffing is variance reduction, not EV.** Academic play-by-play of 100k+ drafts
  found handcuffing teams won **51.04%** of games vs **50.56%** for non-handcuffing teams, a Bayes
  factor of 4.2 *favouring no difference*
  (<https://sjdm.org/~baron/journal/22/220318/jdm220318.html>). We therefore treat handcuff value as
  insurance on a top-2-round investment, conditional on the incumbent's draft cost, not as a flat
  15/100 weight. At a measured 13.8% hit rate it is strictly dominated by the 36% lottery stash of
  R3 whenever the incumbent was cheap. → prediction P3.
- **count-vs-config.** `b_hc ≤ 1`, and only when an owned RB was taken inside round 2 **and** the
  backup already holds ≥35% early-down share. Rises slightly in `std` scoring (TD-dependent, so
  role consolidation matters more), falls in `ppr` (pass-catching backs are startable standalone).

### R5 — Streaming slot (K / DST / TE / QB-in-1QB)

- **signal.** `σ(pos) ≪ 1` — the wire holds startable bodies all season — combined with high weekly
  variance. Weekly matchup input: our `scheduleStrength(team, weeks)` / `defRatings`.
- **value.** ≈ **0 above replacement by construction.** The top kicker outscored K12 by 30 points
  over a season, **1.7 points per game**
  (<https://www.si.com/onsi/fantasy/nfl/fantasy-football-strategy-guide-when-draft-kicker-defense>).
  Only ~5 defenses and ~7 kickers form a "top tier," and a lowest-total-game DST stream is startable
  roughly **50%** of the time
  (<https://www.basementbrewedff.com/post/defenses-and-kickers-you-re-drafting-them-wrong-but-its-not-your-fault>).
  Kickers are not pure noise — 10 of the top 15 in 2025 came from top-half passing-volume offenses,
  and ~half of top-10 kickers over 2022–2025 played for top-15 third-down offenses
  (<https://www.4for4.com/2026/preseason/debunking-randomness-kickers-fantasy-football>) — but the
  same source still advocates streaming in redraft. Where they disagree we take 4for4's *mechanism*
  (K scoring is a function of team scoring, so it is projectable) and SI's *conclusion* (the
  projectable spread is 1.7 pts/game, less than the ~25-point stash EV of R3).
- **count-vs-config.** Exactly `S(K)` kickers and `S(DST)` defenses, **never a backup**. Invariant
  across all 432 rows. → prediction P6/P10. TE: `b(TE) = 1` only under `te_premium > 0` *and* no
  top-6 TE rostered (a two-TE stream hedge); 0 otherwise.

### R6 — Playoff-schedule stash

- **signal.** `playoffSchedule(player, defRatings)` over weeks 15–17: opponent defensive rating
  *against that position*.
- **value.** Real but bounded — three weeks × a small per-week delta. Season-long SOS is
  "one of the weaker predictive tools in fantasy football," useful only for playoff-week planning
  and in-season streaming; it is "a legitimate tiebreaker in the middle rounds. It is not a reason
  to reach two rounds early"
  (<https://www.fantasyfootballblueprint.com/2026/08/07/strength-of-schedule/>). That source is
  explicit that it offers no correlations or R² — so we treat the *direction* as sourced and the
  *magnitude* as a guess to be fit.
- **count-vs-config.** **0 dedicated slots, in every config.** R6 is a tie-break weight applied to
  R2/R3 candidates, never a role that earns a bench spot of its own. This is our argument that
  `PlayoffSchedule: 10` in `GENERAL_WEIGHTS` is too large. → §3.

### R7 — Trade asset

- **signal.** Surplus at a position where league-wide demand exceeds NFL supply: `σ(pos) > 1` while
  you hold more than `S(pos) + b_bye + b_inj`. Canonically the superflex QB3.
- **value.** Option value on *another manager's* injury. A high-quality backup QB in superflex is
  among the most tradeable assets in the format
  (<https://www.fantasypros.com/2026/06/a-beginners-guide-to-understanding-superflex-leagues/>).
- **count-vs-config.** 0–1, and only when `qb_mode ≠ 1qb`.
- **Our model — this role is deliberately unmodelled.** E5 does not simulate trades, so R7 has **no
  measurable value under our metric**. `SF_RB_WEIGHTS.TradeValue: 10` and
  `SF_WR_WEIGHTS.TradeValue: 10` are therefore *unfittable*: E10 must either ablate them to 0 or
  pin them and record that they are unvalidated. A fit that assigns them non-zero free weight is
  fitting a proxy. → prediction P11.

### R8 — Dead weight

- **signal.** `P(start any week) ≈ 0`: a backup K, a backup DST, a QB2 in `1qb` where `σ(QB) < 0.5`,
  a third TE, any player past `S(pos) + b(pos)` from §2.
- **value.** **Negative, and quantifiable**: `−EV(best alternative use of the slot)` = the R3 stash
  EV ≈ **−25 points per season**. This is not a free parameter — it is the R3 number with a sign
  flip, and it is the theoretical target for `overfillPenaltyPerExtra` and `DeadRosterSpotPenalty`.
- **count-vs-config.** 0, always.

### R9 — IR-slot arbitrage (`ir_slots = 1` only)

- **signal.** An NFL designation the platform accepts into the IR slot. Eligibility differs by
  platform: ESPN takes O and IR (not suspended); Yahoo takes IR, NFI-R, NFI-A, O, PUP; NFL.com adds
  suspended and exempt
  (<https://www.footballnationusa.com/post/what-does-ir-mean-in-fantasy-football-injured-reserve-rules-explained>).
  An IR player **does not occupy a bench slot** — that is the whole mechanism.
- **value.** With `IR=1`, a known-injured high-upside player costs draft capital but ~0 roster
  capital after week 1. Effective budget becomes `B_eff = B + IR·P(you hold an eligible player)`,
  worth ≈ one extra R3 stash ≈ 25 points × that probability.
- **count-vs-config.** `b_ir = IR`. And critically: **`injuryDiscount` must be a function of
  `ir_slots`.** Current values (`ir: 0.35`, `pup/nfi: 0.40`) price the full roster cost of the
  absence; at `ir_slots = 1` that cost largely vanishes and the discount should be far shallower.
  → prediction P5.

---

## 2. Count-vs-config — the allocation function

**Our model.** Given a config row `(T, qb_mode, scoring, te_premium, B, IR)`:

```
1.  S(pos)  ← derived from qb_mode (v5-architecture §3)
2.  σ(pos)  ← (T·(S(pos)+b(pos)) + 1) / N(pos)          # solve by one fixed-point pass, b init 0
3.  b_cover(pos) = ceil( S(pos) · h(pos) · σ(pos) · 17 / 17 )   # injury cover, R2
                 + [σ(pos) > 1]                                  # bye cover, R1
4.  b_stream    = 0 for K/DST always; TE per R5
5.  L (stashes) = max(0, B + IR − Σ_pos b_cover(pos))            # R3 residual
6.  b(pos)      = b_cover(pos), plus L allocated to the highest-EV R3 candidates
```

Worked rows (all derived from the formula above; **E6 must reproduce these or disprove them**):

| config | σ(QB) | σ(RB) | σ(WR) | b(QB) | b(RB) | b(WR) | b(TE) | b(K/DST) | stashes |
|---|---|---|---|---|---|---|---|---|---|
| T=12 `1qb` B=6 | 0.41 | 0.86 | 0.39 | 0–1 | 2 | 1 | 0–1 | 0 | 2–3 |
| T=12 `superflex` B=6 | **1.16** | 0.86 | 0.39 | **1–2** | 1–2 | 1 | 0 | 0 | 1–2 |
| T=12 `2qb` B=6 | **1.16** | 0.86 | 0.39 | **2** | 1 | 1 | 0 | 0 | 1–2 |
| T=8 `1qb` B=6 | 0.28 | 0.58 | 0.26 | 0 | 1 | 1 | 0 | 0 | 4 |
| T=14 `1qb` B=6 | 0.47 | **1.00** | 0.45 | 0–1 | 3 | 1 | 0–1 | 0 | 1–2 |
| any, B=4 | — | — | — | coverage only | | | | 0 | **0** |
| any, B=8 | — | — | — | coverage + | | | | 0 | **+2** |

**Factor-by-factor effects:**

- **`teams`.** The only factor that moves `σ` for every position at once. `T=14` pushes
  `σ(RB) → 1.0` — RB depth stops being optional. `T=8` collapses coverage needs and the bench
  becomes almost all R3.
- **`qb_mode`.** The discontinuity. `1qb` at T=12: `σ(QB) = 13/32 = 0.41`, the wire holds a starting
  NFL quarterback — stream. `superflex` doubles the slots: `σ(QB) = 25/32 = 0.78` with zero bench
  QBs, and once each team holds a third, demand is 36 against a supply of 32, `σ = 1.16 > 1`. This
  is exactly the published guidance — "in leagues of 10 teams or more, aim to roster at least three
  quarterbacks, and four if possible," because a 12-team superflex has 24 starting QB spots against
  32 NFL starters (fantasypros, above); "snag at least three quarterbacks … bye weeks, injuries,
  benchings"
  (<https://www.cbssports.com/fantasy/football/news/superflex-fantasy-football-strategy-quarterbacks-drafting/>).
  Our contribution is that the count *falls out of σ* rather than being asserted.
  `2qb` has the same σ but no flex substitute for a missing QB, so its bye-cover term is strictly
  binding where superflex's is soft.
- **`scoring`.** Does not change `N(pos)` but changes the *shape* of the curve. PPR/half-PPR raise
  the floor of pass-catching RBs and back-end WRs, flattening both curves ⇒ effective `σ(WR)` falls
  ⇒ fewer WR coverage slots, more stashes. `std` steepens RB (TD-dependent) ⇒ role consolidation
  matters more ⇒ R4 handcuff value rises.
- **`te_premium`.** Sources disagree and we split them. 4for4 (2015–2023) reports the TE1−TE12 gap
  at **148.7 points** under TE premium, near the WR1−WR24 gap of **159.1**
  (<https://www.4for4.com/2024/preseason/understanding-tight-end-value-te-premium-fantasy-leagues-ffpc>).
  The counter-argument is that a bonus applied to every TE only widens the gap *within* the
  position and leaves TE-vs-WR value unchanged
  (<https://www.fantasyfootballblueprint.com/2025/08/20/the-myth-of-te-premium-scoring/>).
  **Our model:** 4for4 is right about *weights* — VOR measures the gap over the last startable TE,
  and that gap is precisely what widens — and Blueprint is right about *counts*: a wider intra-
  position gap raises the price of the elite TE, it does not raise how many TEs you roster.
  So `te_premium` scales TE weights and leaves `b(TE)` at 0, with the single R5 exception.
- **`bench_slots`.** The budget, not a modifier. `B=4` ⇒ coverage only, `L=0`. `B=8` ⇒ `L+2`.
  Consensus lands at 5–7 bench for a 12-team league, ~one third of a 15–16 man roster, with the
  explicit reasoning that deeper benches let owners hoard handcuffs and drain the wire while
  shallower ones "punish bye weeks harder than they punish bad management"
  (<https://www.cheatsheetwarroom.com/blog/fantasy-football/leagues/best-settings>). Note that this
  is a *league-design* argument, not a *drafting* argument — it constrains what `B` values are worth
  optimising for, not how to spend a given `B`.
- **`ir_slots`.** `B_eff = B + IR·P(eligible player held)`. Changes `injuryDiscount`, not counts.

Formal framing note: roster selection under slot + budget constraints is a mixed-integer program,
and published treatments of the fantasy analogue solve exactly that shape
(<https://arxiv.org/abs/2505.02170>). We are not solving the MIP — E5's simulator scores rosters and
E6 searches — but the constraint structure above is that MIP's feasible region, which is why the
bounds must be config-parameterised rather than constant.

---

## 3. Reconciliation to the current constants

Hypotheses only. **No code changes in this unit.** "Plausible?" is our prior for E6/E10 to test.

| constant | current | theory says it is a function of | plausible? |
|---|---|---|---|
| `GENERAL_WEIGHTS.Upside` | 25 | `P(convert) · (starter − waiver)`; measured 36% hit, ~25 pts EV (R3) | plausible, possibly **low** |
| `GENERAL_WEIGHTS.OpportunityTrend` | 20 | it is the *signal for* Upside, not a separate value term | **double-count** — test merging |
| `GENERAL_WEIGHTS.HandcuffValue` | 15 | `P(role consolidation) · early-down share` (R4) | **too high**; aggregate handcuff win-edge ≈ 0 |
| `GENERAL_WEIGHTS.PositionalScarcity` | 15 | should be `σ(pos)` — a *config* function, not a player tier | **mis-specified** (reads `tiers`) |
| `GENERAL_WEIGHTS.PlayoffSchedule` | 10 | 3 weeks × small delta; SOS is a weak tool (R6) | **too high**; expect ≤5 |
| `GENERAL_WEIGHTS.WeeklyFlexValue` | 5 | `S(FLEX)/S(total)`, higher in PPR | plausible |
| `GENERAL_WEIGHTS.ByeCoverage` | 5 | `[σ(pos) > 1]` — a conditional, not a flat weight (R1) | right size, **wrong form** |
| `GENERAL_WEIGHTS.ReplacementDifficulty` | 5 | this *is* `σ` — duplicates PositionalScarcity | **merge candidate** |
| `GENERAL_PENALTIES.DuplicatePositionPenalty` | 10 | opportunity cost of the marginal stash | plausible |
| `GENERAL_PENALTIES.DeadRosterSpotPenalty` | 5 | same quantity (R8) ⇒ should be **≥** duplicate, not half | **ordering suspect** |
| `SF_MULTIPLIER.QB` | 2.25 | `σ(QB,SF)/σ(QB,1QB) = 1.16/0.41 = 2.8` | plausible, maybe **low** — and now *derived* |
| `SF_MULTIPLIER.RB / WR` | 1.2 / 1.1 | superflex does not change `N(RB)`/`N(WR)`; it *drains* capital from them ⇒ σ falls | **sign may be wrong**; expect ≤1.0 |
| `SF_MULTIPLIER.TE` | 1.0 | neutral floor | plausible |
| `overfillDepth` | `{QB3 RB5 WR5 TE2 K1 DST1}` | `S(pos)+b(pos)` from §2 — config-dependent | `K1/DST1` ✓; `QB3` right only for SF/2QB (should be 2 in `1qb`); RB/WR 5 assumes T=12,B=6 |
| `overfillPenaltyPerExtra` | 25 | R8 = R3 stash EV = `0.36 × 70 ≈ 25` pts/season | **lands on the theory value** ✓ |
| `byeStackPenalty` | 12 | `max(0, starters_on_bye − coverable(B, σ))`; clustering may be *positive* | **most suspect constant in the file** |
| `injuryRate` | `{QB .08 RB .18 WR .12 TE .12 K .03 DST 0}` | hazard × duration, §R2: QB .078 RB .20 WR .144 TE .127 DST 0 | QB/TE/DST ✓; RB low; **WR ~20% low**; should be ADP-tier conditional |
| `injuryDiscount` | flat status→multiplier | `f(expected weeks missed, ir_slots, B)` | **mis-specified**: `ir/pup/nfi` far too steep when `ir_slots=1` |
| `faPenalty` | 1000 | a true FA's σ-adjusted value ≈ 0 — this is a sort sentinel, not a value | works, but hides the quantity; E2's `AvailabilityModel` should replace it |
| `kdstCapRoundsFromEnd` | 2 | `S(K)+S(DST) = 2`, both at replacement level; K1−K12 = 1.7 pts/g | plausible, **directly supported** |
| `kdstSoftPenalty` | 20 | ≈ K/DST season VOR (~30) − stash EV (~25) ⇒ a 5–30 band | plausible, inside the band |
| `handcuffAmplify` | 1.6 | committee `29.3/10.5 = 2.8`; clean backup `6.5/10.5 = 0.62` | **a single scalar cannot express it** |
| `emptyOffensiveStarterBonus` | 140 | season points of the best available at the empty slot (~120–200) | plausible |
| `availabilityPrior` | 0.9 | `1 − mean(h) ≈ 1 − 3/17 = 0.82` | **slightly high** |
| `benchByeWeight / benchInjuryWeight / benchCeilingWeight` | 1 / 1 / 1 | should be `σ`- and `h`-scaled per position, not all equal | **suspect** — R1 ≠ R2 ≠ R3 in value |
| `boomWeight / maxCeilingWeeks / ceilingScale` | 0.5 / 4 / 6 | R3 conversion shape | unsourced guesses — E10 free params |
| `benchQualityWeight` | 1 | the ablation handle | theory-neutral, keep |
| `runDepletion / runThresholdMult` | 2.2 / 1.4 | herding is real: copycat drafting is strong for QB early and K/DST throughout — but confers **no** win edge (51.22% vs 50.12%, sjdm) | **detection supported**; expect strongest signal at QB-early and K/DST-late |

---

## 4. Falsifiable predictions

Each is stated so E5's imperfect-information simulator can disprove it. Tagged with the unit.

- **P1 — bye stacking (E5, E8b).** Setting `byeStackPenalty = 0` will **not** reduce simulated win
  rate at `bench_slots ≥ 6`; it *will* at `bench_slots = 4`. If the penalty helps at every bench
  depth, our reading of the 4for4 clustering result does not transfer and R1 is wrong.
- **P2 — superflex QB2 (E5, E10).** In `superflex`/`2qb` with `T ≥ 10`, the second rostered QB adds
  more expected wins than the third RB or the third WR below ADP rank `3T`. Disproved by an ablation
  that drops `SF_MULTIPLIER.QB` to 1.0 and wins more.
- **P3 — handcuff vs stash (E5, E10).** A bench slot on a same-team backup RB with **<35%** early-
  down share is worth less than a slot on the highest-`opportunity_trend` WR available. Concretely:
  the fitted `HandcuffValue` weight lands **below 15 and below `Upside`**.
- **P4 — SF RB/WR multipliers (E6, E10).** Fitting `SF_MULTIPLIER` freely pushes RB and WR to
  **≤ 1.0**, not 1.2/1.1. A free fit that keeps them above 1.1 disproves the σ argument in §2.
- **P5 — IR interaction (E5, E10).** `injuryDiscount` for `ir`/`pup`/`nfi` conditioned on
  `ir_slots` will exceed **0.6** in `ir_slots = 1` rows while staying **≤ 0.45** in `ir_slots = 0`
  rows. A fit that finds no `ir_slots` interaction disproves R9.
- **P6 — K/DST count bound (E6).** **No row** of the 432-row matrix has an optimal roster holding
  more than one K or more than one DST. One counterexample disproves `overfillDepth {K:1, DST:1}`.
- **P7 — redundant scarcity terms (E10).** `PositionalScarcity` and `ReplacementDifficulty` measure
  the same quantity; a fit merging them into one `σ` term will **not** regress against the
  two-term fit.
- **P8 — WR injury rate (E5, E10).** Raising `injuryRate.WR` from 0.12 toward **0.145** improves or
  leaves flat the walk-forward metric; lowering it hurts. Same directionally for RB → 0.20.
- **P9 — allocation monotonicity (E6).** `b(RB)` is non-decreasing in `teams` and non-increasing in
  the PPR-ness of `scoring`. A derived allocation violating either disproves the σ formula in §2.
- **P10 — dead weight (E8b).** No optimal roster in any matrix row holds a second K, a second DST,
  or — at `qb_mode = 1qb` — a third QB.
- **P11 — TradeValue is unfittable (E10).** Because E5 simulates no trades, freeing the SF
  `TradeValue` weights drives them to ~0. A fit assigning them meaningful non-zero weight is
  capturing a proxy and should be read as an overfit signal, not as validation of R7.
- **P12 — playoff schedule is a tiebreak (E10).** The fitted `PlayoffSchedule` weight lands
  **below 10**, and ablating it entirely costs less than ablating `Upside`.

---

## 5. Explicit non-claims

This model covers **redraft, snake-draft, weekly head-to-head, 17-game NFL seasons**. It does not
cover, and downstream units must not apply it to:

- **Dynasty and keeper.** Multi-year asset value, rookie picks, and age curves invert R3 and R7
  entirely; a "dead weight" R8 player can be a legitimate dynasty hold.
- **Auction / salary cap.** There is no budget term anywhere above. Every count is a slot count.
- **Best-ball.** No in-season waivers ⇒ R1/R2/R5 collapse (there is nothing to stream *to*) and the
  bench becomes almost entirely R3. Counts from §2 are wrong for best-ball by construction.
- **DFS.** Single-week, no roster continuity, no bench.
- **IDP, 2-QB-plus-superflex hybrids, non-standard K/DST scoring**, and any `teams` outside 8–14.
- **In-season management.** Waiver priority, FAAB bidding, start/sit, trade execution, and playoff
  seeding/tanking are all out of scope. This is a *draft-time* allocation model.
- **Player identification.** This is a model of **roles and counts**, never of which specific player
  fills one. Rankings live in the Projector/ValueEngine, not here.

---

## Sources

All accessed **2026-08-25**; every URL was fetched and confirmed to contain the claim it supports.

1. <https://www.fantasyfootballblueprint.com/2026/08/06/10-handcuffing-running-backs/> — 9-season, 283-team-season handcuff study: 13.8% vs 10.5% RB24+; 15.2% of starters miss 6+ games; clean 6.5% vs committee 29.3%.
2. <https://www.sharpfootballanalysis.com/fantasy/fantasy-football-handcuff-history-cheap-rb1s-and-ambiguous-backfields/> — 8 of 71 (11.3%) backups to first-round RBs since 2010 hit top-24.
3. <https://sjdm.org/~baron/journal/22/220318/jdm220318.html> — *Drafting strategies in fantasy football* (J. Judgment & Decision Making): handcuffing 51.04% vs 50.56% (BF 4.2 for the null); herding strongest at QB-early and K/DST-throughout, 51.22% vs 50.12%.
4. <https://www.profootballlogic.com/articles/nfl-injury-rate-analysis/> — per-game injury rate × mean games missed by position (2015); source of the derived `h(pos)` table.
5. <https://rotobanter.beehiiv.com/p/are-running-backs-more-injury-prone-than-receivers> — 2021–25 games missed by position and ADP tier: RB 3.3 / WR 2.8; top-24 2.4 / 2.2; rounds 6–8 3.8 / 3.3.
6. <https://www.thefantasyfootballers.com/analysis/the-late-round-wrs-nobody-wants-but-should-fantasy-football/> — 25 late-drafted team-WR1s 2020–25, 9 breakouts (36%), ~2/season, avg 191 half-PPR pts.
7. <https://www.4for4.com/fantasy-football-bye-week-management> — 50,000-season Monte Carlo: clustered byes 501,247 wins vs 361,972 (moderate) vs 336,781 (spread).
8. <https://www.fantasyfootballblueprint.com/2026/08/07/strength-of-schedule/> — season-long SOS is a weak predictive tool; useful only for playoff-week planning and in-season streaming; offers no correlations (hence magnitude is a fit parameter for us).
9. <https://www.si.com/onsi/fantasy/nfl/fantasy-football-strategy-guide-when-draft-kicker-defense> — draft K/DST in the final two rounds; top K beat K12 by 30 pts, 1.7 pts/game.
10. <https://www.basementbrewedff.com/post/defenses-and-kickers-you-re-drafting-them-wrong-but-its-not-your-fault> — ~5 top-tier DSTs, ~7 top-tier Ks; lowest-total-game DST stream startable ~50% of weeks.
11. <https://www.4for4.com/2026/preseason/debunking-randomness-kickers-fantasy-football> — K scoring tracks team passing volume and 3rd-down rate (10 of top-15 in 2025); still advocates streaming in redraft.
12. <https://www.fantasypros.com/2025/06/fantasy-football-draft-strategy-value-based-drafting-vorp-vols-vona/> — VORP/VOLS/VONA baselines; replacement threshold = league size × roster spots at the position.
13. <https://sticktothemodel.com/blog/fantasy-football-vorp-explained-2025> — published replacement ranks at 10/12/14 teams; the empirical check on our linear `R(pos)`.
14. <https://www.fantasypros.com/2026/06/a-beginners-guide-to-understanding-superflex-leagues/> — roster ≥3 QBs (4 if possible) at 10+ teams; 12-team superflex = 24 starting QB spots; backup QB is a top trade asset.
15. <https://www.cbssports.com/fantasy/football/news/superflex-fantasy-football-strategy-quarterbacks-drafting/> — "at least three quarterbacks … bye weeks, injuries, benchings"; one early + one after round 4.
16. <https://www.4for4.com/2024/preseason/understanding-tight-end-value-te-premium-fantasy-leagues-ffpc> — 2015–23: TE1−TE12 gap 148.7 pts under TE premium vs a WR1−WR24 gap of 159.1.
17. <https://www.fantasyfootballblueprint.com/2025/08/20/the-myth-of-te-premium-scoring/> — counter-position: TE premium widens the intra-TE gap only; TE-vs-WR positional value unchanged.
18. <https://www.footballnationusa.com/post/what-does-ir-mean-in-fantasy-football-injured-reserve-rules-explained> — IR eligibility by platform (ESPN O/IR; Yahoo IR/NFI-R/NFI-A/O/PUP; NFL.com adds suspended, exempt); an IR player frees the active-roster spot.
19. <https://www.cheatsheetwarroom.com/blog/fantasy-football/leagues/best-settings> — 15–16 roster spots at 12 teams, ~⅓ bench (6–7); deeper benches enable handcuff hoarding, shallower over-punish byes.
20. <https://arxiv.org/abs/2505.02170> — MILP for fantasy squad selection under budget/formation/quota constraints; the formal shape of the roster problem §2 parameterises.
