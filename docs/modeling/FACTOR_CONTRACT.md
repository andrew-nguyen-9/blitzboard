# Factor Contract (F3)

The **projection-factor framework** lets the Projector be extended *without editing
it*. Each downstream unit (E1/E2/E3/E5) adds a DISJOINT factor as **one new file**;
`projector.py` never changes. This document is the contract those units build on.

## What a factor is

A **factor** is a pure, deterministic, side-effect-free adjustment to a player's
point projection:

```
factor(player, context) -> multiplier (identity 1.0)  OR  delta (identity 0.0)
```

- A **multiplier** *scales* the projection (e.g. a 0.85 injury-risk haircut).
- A **delta** *shifts* it in points (e.g. +6 for a plum matchup).

Factors are **orthogonal to the predictability discount** `f(ρ)`: that discount is
applied *later* by the `ValueEngine` on **value**, not here on the **projection**. A
factor reshapes the point projection; predictability then compresses unreproducible
*value* on top. The two never touch the same number.

## The protocol

`pipeline/models/factors/base.py`:

```python
class Factor(ABC):
    kind: str = MULTIPLIER          # MULTIPLIER | DELTA
    positions: tuple[str, ...] | None = None   # whitelist; None = all positions
    enabled: bool = True            # False → discoverable but DORMANT (not applied)

    @property
    def name(self) -> str: ...      # defaults to the class name

    def applies(self, ctx: FactorContext) -> bool: ...   # override for richer gating
    def compute(self, ctx: FactorContext) -> float: ...  # <-- implement this (pure)
```

You implement **`compute(ctx)`** only. Return a multiplier (kind `MULTIPLIER`) or a
points delta (kind `DELTA`). Override `applies(ctx)` when a positional whitelist is
not enough (e.g. gate on `ctx.week` or an injury status).

### The `context` shape (`FactorContext`)

Everything a factor may need. Typed core fields cover today's needs; the
`metadata` dict is the escape hatch so **injury / bye / team-vs-team / college /
weather / scheme / betting** all fit **without any protocol change**.

| field | type | notes |
|-------|------|-------|
| `player_id` | `str` | identity |
| `full_name` | `str \| None` | |
| `position` | `str \| None` | primary position |
| `positions` | `tuple[str, ...]` | multi-position eligibility (`fantasy_positions`) |
| `nfl_team` | `str \| None` | **canonical** code (post roster-fix, see below) |
| `season` | `int` | |
| `week` | `int \| None` | `None` → season-long projection |
| `opponent` | `str \| None` | team-vs-team / weekly matchup |
| `bye_week` | `int \| None` | |
| `injury_status` | `str \| None` | |
| `age`, `years_exp` | `int \| None` | |
| `college` | `str \| None` | |
| `metadata` | `dict` | depth chart, weather, betting lines, scheme, snap share… |
| `store` | `HistoryStore` | a player's historical season lines |
| `rules` | `LeagueRules` | league scoring / roster |

Build one from a `players` row with
`FactorContext.from_player(player, season, store=?, rules=?, week=?, opponent=?)`.

## Where factor files live & how to add one

Directory: **`pipeline/models/factors/`** — one factor (or a small cohesive set)
per file. To add a factor:

1. Create `pipeline/models/factors/<your_factor>.py`.
2. Subclass `Factor`, set `kind`/`positions`, implement `compute(ctx)`.
3. That's it. `loader.discover_factors()` globs the package and picks it up — **no
   edit to `projector.py`, no registry**. Ship it `enabled = False` to stage it
   dormant.

```python
from .base import Factor, FactorContext, MULTIPLIER

class MatchupFactor(Factor):          # E3, illustrative
    kind = MULTIPLIER
    positions = ("RB", "WR", "TE")
    def compute(self, ctx: FactorContext) -> float:
        vs = (ctx.metadata.get("def_rank_vs_pos") or {}).get(ctx.position)
        return 1.0 if vs is None else 0.90 + 0.20 * (vs / 32)
```

See `pipeline/models/factors/reference.py` for the shipped identity template.

## Composition

`projector.apply_factors(projection, ctx, factors)` composes them:

```
mean'    = mean * ∏(multipliers) + Σ(deltas)
stdev'   = stdev * ∏(multipliers)
floor'   = floor * ∏(multipliers) + Σ(deltas)
ceiling' = ceiling * ∏(multipliers) + Σ(deltas)
```

Scaling by the product and shifting by the sum **preserves the ±1.28σ distribution
shape exactly**, so Monte-Carlo/VORP downstream stay coherent. A net-identity set
(the shipped `ReferenceFactor`) returns the projection unchanged → **zero
regression**. Applied non-identity factors are recorded in `projection.by_stat["factors"]`
for traceability.

`EnsembleProjector(projectors, factors=None)` **auto-discovers** factors by default
(so adding a file flows straight through). Pass `factors=[]` to opt out (backtests /
isolation tests).

## How a factor is backtested

The backtest harness (`pipeline/backtest/**`) is frozen — **extend it via NEW
`test_*.py` files only** (pytest auto-discovers). To validate a factor:

- Add unit assertions in a new `pipeline/tests/test_<factor>.py` (composition math,
  gating, identity when data is missing).
- For value impact, the models backtest runs the projector→VORP chain across
  historical seasons; a factor that improves rank-correlation should not regress
  `test_models_backtest`. Ship a factor `enabled = False` until its backtest clears,
  then flip it on.

## Roster source of truth (why `nfl_team` is trustworthy)

`ctx.nfl_team` is a **canonical** NFL code because `player_ingest.normalize_team()`
now maps every Sleeper team value to one of the 32 canonical codes (or `None`):

- legacy/relocated/variant abbreviations resolve (e.g. `OAK→LV`, `SD→LAC`,
  `STL/LA→LAR`, `WSH→WAS`, `JAC→JAX`);
- free agents / retired / unrecognized codes → `None` (never a *wrong* team).

Verify with `cd pipeline && python -m pytest tests/test_roster_mapping.py` (the live
check self-skips when Supabase is unconfigured).
