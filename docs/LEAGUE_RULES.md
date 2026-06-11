# League Rules — "Smores 2025" (the v1 league)

Encoded in [../db/seed_league_smores.sql](../db/seed_league_smores.sql) as the `LeagueRules`
config. This is the single source of truth that drives every value computation. Source:
ESPN league settings (2025 season).

## Snapshot
- **12 teams**, Head-to-Head Points, **0.5 PPR (half-PPR)**, ESPN platform.
- **Snake draft**, Aug 23 2025 8:15 PM CDT, 45s/pick, manual order, **no pick trading**.
- **FAAB waivers** — $100 budget, $0 min, 1-day waiver, tiebreaker = move-to-last.
- 14 regular-season matchups · 6 playoff teams · 1 week/round · +1 playoff home-field pt.
- No keepers. ESPN undroppable list observed. 1 IR slot. Trade deadline Nov 26 2025.

## Roster — 10 starters, 6 bench (1 IR), size 16
| Slot | Count | Eligible |
|------|-------|----------|
| QB | 1 | QB |
| RB | 2 | RB |
| WR | 2 | WR |
| TE | 1 | TE |
| **FLEX** | 1 | RB / WR / TE |
| **OP** | 1 | **QB / RB / WR / TE** ← superflex |
| D/ST | 1 | D/ST |
| K | 1 | K |
| Bench | 6 | any |
Position maximums: QB 4, RB 8, WR 8, TE 3, D/ST 3, K 3.

## ⚠ The single most important modeling fact: OP = superflex
The **OP (Offensive Player Utility)** slot accepts a QB. So a rational 12-team field will
roster up to **~24 starting-caliber QBs** (one in QB + one in OP per team), not 12.

**Implications the value engine MUST encode:**
- **QB replacement level** is set around the **~24th QB**, not the ~12th → QB VORP rises sharply; elite QBs become genuinely premium, and there's a real run on QBs.
- `roster_slots._superflex = true` and `_op_eligible` includes `QB` — the `ValueEngine`
  computes replacement baselines from *slot demand across the league*, not fixed per-position
  assumptions. Don't hardcode 1-QB baselines.
- Monte Carlo opponent models should reflect QB-hungry drafting (earlier QB runs).
- Two-QB-eligible slots also lift the value of having a QB on the bench (bye/injury cover).

## Scoring cheat-sheet (full detail in the seed SQL)
- **Pass:** 0.04/yd (25 yds/pt), TD 4, INT −2, 2PC 2.
- **Rush/Rec:** 0.1/yd, TD 6, 2pt 2. **Reception 0.5 (half-PPR).** Fumble lost −2.
- **K (distance-based):** PAT 1 / miss −2, FG miss −1, FG 0–39 = 3, 40–49 = 4, 50–59 = 5, 60+ = 6.
  → Kickers who attempt long FGs carry meaningfully more value here than flat-3-per-FG leagues.
- **D/ST:** sack 1, INT/FR/safety/blocked-kick 2, any TD 6, 1pt-safety 1.
  - Points allowed: 0 → 5, 1–6 → 4, 7–13 → 3, 14–17 → 1, **18–27 → 0**, 28–34 → −1, 35–45 → −3, 46+ → −5.
  - Yards allowed: <100 → 5, 100–199 → 3, 200–299 → 2, **300–349 → 0**, 350–399 → −1, 400–449 → −3, 450–499 → −5, 500–549 → −6, 550+ → −7.
  → D/ST has a **yardage-allowed component** (uncommon) → favors stout, low-yardage defenses, not just turnover/TD variance. Worth a dedicated D/ST projection treatment.

## Notes that touch strategy (not scoring math)
- **Bonus Wins and Losses = Yes** → weekly ceiling/consistency matters a touch more than pure expected points; surface boom/bust (Monte Carlo) prominently.
- **45s/pick, snake, no pick trading** → the live/offline draft board's recompute speed and
  best-available clarity matter; no need to model draft-pick-trade logic.
- **FAAB (not rolling waivers)** → the waiver tool should recommend **bid amounts** (% of remaining budget), not just priority order. Blend with the trending/sentiment signal.

## Multi-tenant note
This is one row in `league_rules`. The same structure (superflex flag, slot eligibility,
distance-based K, yardage D/ST) generalizes — when the tool opens to others, their settings
populate the same JSONB shape, and the engine reads slot demand to derive replacement levels.
