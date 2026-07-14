"""Vegas context → a LEARNED nonlinear line→outcome mapping as a bounded opportunity factor.

The context seam over E1-core for game script: it implements the core's `FactorHook`
(model.py) so a team's betting line nudges its players' **opportunity** — but through a
*fitted* nonlinear map, NOT the raw spread. Blowout favorites bleed pass volume late (run
out the clock); trailing underdogs in high-total games throw more (more targets); a fair,
low-total game barely moves. Those are curves, so the mapping learns a basis regression on
(team spread, game total) rather than assuming a straight line.

GATED on `ODDS_API_KEY` (brief blocker): absent ⇒ the factor returns 1.0 for every player
(mapping OFF, projection unaffected — degrade-neutral). Unknown teams and an unfitted
mapping likewise return 1.0. The projector clamps the result to `FACTOR_BOUNDS`, so even a
mis-fit map can never blow up a projection.

Odds provenance: `team_lines_from_odds` consumes the pipeline `OddsAdapter`'s consensus
rows (reused via `data.sources.vegas_odds`), so there is one consensus-line source of truth.
"""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

__all__ = [
    "GameScriptMapping",
    "VegasGameScriptFactor",
    "team_lines_from_odds",
]

# Clamp on the learned LOG multiplier before exp — the map's own guard rail (the projector
# re-clamps to FACTOR_BOUNDS too; this keeps the fit's raw output sane in the first place).
_LOG_BOUND = (np.log(0.5), np.log(2.0))


def _basis(spread: np.ndarray, total_c: np.ndarray) -> np.ndarray:
    """Nonlinear feature basis: intercept + spread + spread² + total + total² + interaction.

    The squared and interaction terms are what make the map *nonlinear* in the line — a
    pure `[1, spread]` basis would collapse back to "raw spread", which the brief forbids.
    """
    s, t = np.asarray(spread, float), np.asarray(total_c, float)
    return np.stack([np.ones_like(s), s, s * s, t, t * t, s * t], axis=-1)


@dataclass(frozen=True)
class GameScriptMapping:
    """A fitted (or neutral) nonlinear map from a team's (spread, total) → opportunity ×.

    `coef` is the basis-regression weight vector on the LOG multiplier (so `predict` = exp).
    `neutral()` (coef=None) always returns 1.0 — the degrade default before any fit exists.
    """

    coef: np.ndarray | None = None
    total_mean: float = 44.0

    @classmethod
    def neutral(cls) -> GameScriptMapping:
        return cls(coef=None)

    @classmethod
    def fit(
        cls,
        spreads: Sequence[float],
        totals: Sequence[float],
        log_multiplier: Sequence[float],
        *,
        ridge: float = 1.0,
    ) -> GameScriptMapping:
        """Ridge least-squares fit of the log-multiplier on the nonlinear basis.

        `log_multiplier` is the observed log(team opportunity / its line-free baseline). Ridge
        (`λ`) keeps the higher-order terms from overfitting a thin slate. `ponytail:` a closed-
        form `(XᵀX+λI)⁻¹Xᵀy` is the whole "learned" step — numpy, no sklearn, no training loop.
        """
        s = np.asarray(spreads, float)
        t = np.asarray(totals, float)
        y = np.asarray(log_multiplier, float)
        tmean = float(t.mean()) if t.size else 44.0
        x = _basis(s, t - tmean)
        a = x.T @ x + ridge * np.eye(x.shape[1])
        coef = np.linalg.solve(a, x.T @ y)
        return cls(coef=coef, total_mean=tmean)

    def predict(self, spread: float, total: float) -> float:
        """Bounded opportunity multiplier for one team's line (1.0 if unfitted)."""
        if self.coef is None:
            return 1.0
        x = _basis(np.array([spread]), np.array([total - self.total_mean]))
        raw = float((x @ self.coef).reshape(-1)[0])
        return float(np.exp(np.clip(raw, _LOG_BOUND[0], _LOG_BOUND[1])))


def team_lines_from_odds(
    rows: Sequence[Mapping[str, object]], alias: Mapping[str, str] | None = None
) -> dict[str, tuple[float, float]]:
    """Consensus odds rows → `team_id → (signed spread, total)` (home + away both keyed).

    Home team keeps `home_spread` (negative = favored); the away team gets its negation; both
    share `total`. `alias` optionally maps a book's full team name → the engine's team id;
    unmapped names pass through (and later resolve to neutral if they don't match a team).
    """
    alias = alias or {}
    out: dict[str, tuple[float, float]] = {}
    for r in rows:
        home, away = r.get("home_team"), r.get("away_team")
        hs, total = r.get("home_spread"), r.get("total")
        if home is None or away is None or hs is None or total is None:
            continue
        hs_f, tot_f = float(hs), float(total)  # type: ignore[arg-type]
        out[alias.get(str(home), str(home))] = (hs_f, tot_f)
        out[alias.get(str(away), str(away))] = (-hs_f, tot_f)
    return out


class VegasGameScriptFactor:
    """`FactorHook`: per-player opportunity × from his team's learned game-script mapping.

    Key-gated (`ODDS_API_KEY`) and neutral by default: no key / no mapping / no lines / an
    unknown team ⇒ 1.0 (the projector's neutral factor). `team_lines` may also arrive via the
    `FactorContext.context["vegas_team_lines"]` passthrough the wiring supplies.
    """

    name = "vegas_game_script"
    requires_key = "ODDS_API_KEY"

    def __init__(
        self,
        team_lines: Mapping[str, tuple[float, float]] | None = None,
        mapping: GameScriptMapping | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        self.team_lines = dict(team_lines or {})
        self.mapping = mapping or GameScriptMapping.neutral()
        self.enabled = enabled if enabled is not None else bool(os.getenv(self.requires_key))

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        data = ctx.data
        out = np.ones(data.n_players)
        lines: Mapping[str, tuple[float, float]] = self.team_lines
        if not lines:
            passthrough = ctx.context.get("vegas_team_lines")
            if isinstance(passthrough, Mapping):
                lines = passthrough
        if not self.enabled or self.mapping.coef is None or not lines:
            return out  # degrade-neutral: mapping off, projection unaffected
        for i, team_idx in enumerate(data.team_of_player):
            team = data.teams[int(team_idx)]
            line = lines.get(team)
            if line is not None:
                out[i] = self.mapping.predict(float(line[0]), float(line[1]))
        return out
