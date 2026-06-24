# Value Engine (v2)

Two engines behind the `ValueEngine` interface, both batch-precomputed and cached, selected
by a UI toggle. v2 upgrades both implementations; the contract is unchanged.

```
value(players, league_rules) -> { player_id: { value, vor, replacement, boom, bust, rank, predictability } }
```

## `VorpEngine` — predictability-discounted, demand-derived

- **Replacement from league slot demand**, never hardcoded per-position. Superflex/OP makes
  QB replacement ~24th (see `docs/archive/v1/LEAGUE_RULES.md`); FLEX/OP also lifts RB/WR/TE.
  K/DEF replacement = weekly streamer level (`SCORING.md`).
- **Predictability discount**: `adj_value = replacement + raw_VORP * f(ρ)` where `ρ` is the
  player's predictability and `f` is tuned by backtest. Compresses volatile positions
  (K/DEF) toward replacement without special-casing them.
- Fast, transparent, explainable — the default engine.

## `MonteCarloEngine` — vectorized (shipped v1 P7)

- Simulates N-thousand seasons/drafts from projection **distributions** + opponent behavior +
  ADP noise → expected value + boom/bust range. Already vectorized (v1 P7).
- v2: feed it the **predictability-aware distributions** so volatile players get correctly
  wide ranges; surface boom/bust prominently (league has Bonus Wins/Losses → ceiling matters).
- The engine toggle morphs the player-card viz from dial (point) to ridgeline (distribution).

## Shared inputs

- `Projector` ensemble (regression + heuristic + consensus; superflex-aware) emitting
  `{mean, floor, ceiling, stdev, by_stat, predictability}`.
- `LeagueRules` (per user-league in v2) for scoring + slot demand.

## Caching & toggle

Both engines write to `player_value` keyed by `(engine, scoring_profile)` and are published
into the CDN snapshots (`DATA_TRANSFER.md`). The UI toggle just selects which precomputed set
to read — instant, no client compute. Draft/Trade/Waiver tools remain **thin consumers** of
this layer.

## Open knobs (tuned in backtest, v2.2/v2.4)

- `k` exponent in `f(ρ)=ρ^k` (discount aggressiveness).
- Ensemble weights across the three projector inputs.
- Streamer-replacement percentile for K/DEF.
- Monte Carlo N and opponent-model QB-greediness (superflex).
