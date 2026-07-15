# v4 Bench Scoring — formula reconstruction & signal mapping

Durable design record for cycle **v4/bench-optimization**. Source of truth for the
two bench-scoring formulas is `.orchestrator/spec.md` (E4), transcribed lossily from
the wishlist. Some weight terms were dropped in transcription; Session B reconstructed
them so every formula's positive weights sum to 100. This doc records **what was
recovered and why** — it outlives the cycle (E4/E5 read it; future cycles cite it).

## Why reconstruction was needed

The wishlist → spec transcription dropped ~15-weight terms from three formulas and one
positional multiplier. The rule: recover the *intended* term (do not invent new
mechanics), make positives sum to 100, keep penalties/multipliers applied after.

## 1. General BenchScore — dropped ~15 term

```
BenchScore = 25·Upside + 20·OpportunityTrend + 15·HandcuffValue + 15·PositionalScarcity
           + 10·PlayoffSchedule + 5·WeeklyFlexValue + 5·ByeCoverage + 5·ReplacementDifficulty
           − 10·DuplicatePositionPenalty − 5·DeadRosterSpotPenalty
```

- Transcribed positives summed to **85**; one ~15 term was dropped between
  OpportunityTrend and PositionalScarcity.
- **Recovered: `15·HandcuffValue`** = contingent value of a backup who inherits a
  startable role if the starter is lost = `starterInjuryRisk × backupStandaloneUpside`.
- **Rationale.** P1 "Elite Handcuffs" is the **#1 priority rule** and is otherwise
  unrepresented: `Upside` = standalone ceiling, `OpportunityTrend` = current usage trend,
  neither captures "one injury from a feature role." A ceiling term (P3) was rejected —
  it double-counts `Upside` and would leave the top-priority rule with no formula weight.
- New positive sum: 25+20+15+15+10+5+5+5 = **100 ✓**. Penalties apply after.

## 2. Superflex per-position RB — dropped ~15 term

```
RB = 35·Upside + 25·Opportunity + 15·Injury + 15·StartingProbability + 10·TradeValue
```

- Transcribed positives summed to **85**. The spec was also unsure whether the present
  `15` term is Injury *or* Efficiency.
- **Decision: keep `15·Injury`** (durability / return-timeline value, per P5) and
  **recover the dropped term as `15·StartingProbability`** = feature-back vs committee
  role security.
- **Rationale.** Parallels QB's `25·StartingProbability` and WR's `25·RouteParticipation`
  (each position's "role" term). RB bench value hinges on lead-back vs committee — the
  single most-repeated RB theme in the rules (P1 "↓ if committee", P4 "feature-RB
  backups", P9 "three committee RBs" penalty). Rejected `15·Schedule` (QB/WR carry
  Schedule at only 10, and role dominates RB value).
- Signal: `depth_chart_order` (RB1 = high) + committee detection. New sum: **100 ✓**.

## 3. Superflex positional multipliers — dropped TE

`QB×2.25 · RB×1.20 · WR×1.10 · TE×1.00`

- **Recovered: `TE×1.00`** (neutral). TE is the lowest bench priority in superflex
  (spec: "0-1 TE… streaming/elite backup only"), so its multiplier sits at or below WR's
  1.10; the A-NOTE estimate was ~1.0. Neutral is the honest floor.

## Signal mapping (E4 — map every term to a real signal or neutral+coverage)

Missing signal → **neutral value + add the term to the returned `coverage` list**.
Sources available after E1/E2/E3 land:

| Formula term | Signal source |
|---|---|
| Upside / ceiling | `PlayerWithValue.value.boom` (types.ts) |
| OpportunityTrend | `player_trends.opportunity_trend` (E1) |
| TargetShare | `player_trends.target_share_trend` + base `target_share` (stats) |
| RouteParticipation | `player_trends.routes_run` / `routes_trend` (E1←E2) |
| StartingProbability (QB) | `player_trends.starting_prob` (E1) |
| StartingProbability (RB) | `Player.value.depth_chart_order` |
| JobSecurity | `player_trends.job_security` (E1) |
| HandcuffValue | `depth_chart_order` (backup) × starter `injury_status` → contingent; else neutral |
| PositionalScarcity | existing `tiers.ts` / positional strength |
| PlayoffSchedule / Schedule | E3 `playoffSchedule(player)` / `scheduleStrength(team, weeks)` |
| WeeklyFlexValue / WeeklyProjection | `draftAI.proj()` |
| ByeCoverage | `byeWeeks.ts` `BYE_WEEKS_2026` |
| ReplacementDifficulty / WaiverReplaceability | `tiers.ts` / VORP replacement level |
| TradeValue | `PlayerValue.value` / `trade.ts` |
| Injury | `Player.injury_status` |
| DuplicatePositionPenalty | count same-pos bench players |
| DeadRosterSpotPenalty | backup K / backup DST / backup QB (1QB league) |

## Shared pipeline column contract (E1 ↔ E2, same wave)

E2 extends `history_ingest.STAT_COLS`; E1's `trends_compute.py` reads the additions.
**B fixes the exact keys so the two units run in the same wave without a hard dep:**

- `offense_snap_pct` — offensive snap share (0-1), nflverse NGS/pfr.
- `routes_run` — routes run (count), nflverse NGS/pfr.

E1 computes `routes_trend` from `routes_run`. Missing/absent column → E1 falls back to
neutral 0.5 (cascade-safe), so contract drift degrades a signal, never breaks the build.
