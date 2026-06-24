# Scoring & Player Valuation Upgrade

> Requirement: kickers and defenses are still overvalued. This doc specifies the fix and the
> research behind it. Implementation is phase **v2.2**. Companion: `VALUE_ENGINE.md`.

## Research grounding (why K/DEF are overvalued)

External consensus and our own league context agree:

- **K and D/ST have the highest week-to-week *and* year-to-year variance and the lowest
  predictability** of any position. The top-10 at both positions turns over almost completely
  year to year. ([Fantasy Points](https://www.fantasypoints.com/nfl/articles/2025/week-12-streaming-dsts-and-kickers),
  [FantasyPros VORP](https://www.fantasypros.com/nfl/rankings/vorp-dst.php))
- Because they're **freely streamable off waivers**, their true *value over replacement*
  collapses — the replacement-level K/DEF is nearly as good in expectation as the "elite" one.
  Accepted practice: draft them last, stream all season.
- Projection models **overestimate busts and underestimate booms**, and TD/turnover-dependent
  scoring (exactly what K/DEF are) is the most variable. A point projection treats a volatile
  D/ST like a stable WR — that's the bug.
  ([ParlaySavant](https://www.parlaysavant.com/insights/how-to-build-a-linear-regression-model-for-fantasy-points-half-ppr),
  [FF Analytics](https://fantasyfootballanalytics.net/2014/07/weekly-variability-simulation.html))

**Diagnosis:** v1 ranks K/DEF on projected *point total* with a per-position replacement
baseline that's too generous. It rewards a high mean without penalizing (a) low predictability
and (b) the trivially-available replacement. So elite-projected K/DEF float up the board.

## The fix — three coordinated changes

### 1. Predictability-discounted value
Each player gets a **predictability score** `ρ ∈ [0,1]` from the `Projector`: how
reproducible is this projection? Derived from historical year-over-year rank stability for the
position + this player's own variance + share of points from high-variance sources (TDs,
turnovers, return/defensive TDs). Value is discounted toward replacement by low predictability:

```
adj_value = replacement + (raw_VORP) * f(ρ)        # f(ρ) ≈ ρ^k, k tuned by backtest
```

K and D/ST have structurally low `ρ` → their VORP is heavily compressed toward 0. Stable
RB/WR/QB keep most of their VORP. This is **position-agnostic** — it just happens to hit
K/DEF hardest because the data says it should.

### 2. Replacement level from real waiver availability
Set K/DEF replacement at **streamer level**, not "12th-best." Because every team streams,
the realistically-available K/DEF each week is close to the positional median, not the
worst starter. Concretely: replacement baseline = the expected points of a *matchup-optimized
streamer* (top-of-waiver each week), which sits near the position's upper-middle — crushing
the gap between "elite" and "replacement."

### 3. League-specific signal kept (but bounded)
Our league has **distance-based kicker scoring** (50+ = 5, 60+ = 6) and a **yardage-allowed
D/ST component** (uncommon) — so *some* differentiation is real: kickers with big legs / on
high-scoring offenses, and genuinely stout low-yardage defenses do carry more value. The
model keeps a `KickerProjector`/`DefenseProjector` that captures this, but the predictability
discount + streamer replacement **bound** how high it can lift them. Net effect: the best
K/DEF are a modest edge, not a mid-round pick.

## Position treatment summary

| Pos | Replacement basis | Predictability ρ | Net v2 effect |
|-----|-------------------|------------------|---------------|
| QB | league slot demand (superflex ⇒ ~24th) | high | unchanged (correctly premium) |
| RB/WR | slot demand incl. FLEX/OP | med–high | unchanged |
| TE | slot demand | medium | unchanged |
| **K** | weekly streamer (≈ upper-median) | **low** | **strongly compressed** |
| **D/ST** | weekly streamer (≈ upper-median), bounded by yardage signal | **low** | **strongly compressed** |

## Validation

- **Backtest 2021–2025** (shared harness with `DRAFT_LOGIC.md`): does v2 value, used to draft,
  beat v1 value on season points-for, *and* stop spending early picks on K/DEF?
- **Calibration check**: do realized boom/bust frequencies match the emitted distributions
  (reliability diagram)? Especially for K/DEF.
- **Sanity**: no K or D/ST should rank above a startable offensive player in superflex draft
  value except in extreme, well-justified cases.

## Acceptance (v2.2)

- K/DEF draft value compressed to "last few rounds" range across 2021–2025 backtests.
- Predictability score surfaced in the UI (the player-card "predictability meter") so the
  *why* is legible.
- No regression to QB/RB/WR/TE valuations vs. v1 on backtest.
