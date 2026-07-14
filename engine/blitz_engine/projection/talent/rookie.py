"""Rookie prior: wide by default, sharpened by draft capital + archetype + college.

A rookie has no NFL career arc, so the prior must be **wide** (high epistemic) yet not
context-free — draft capital is the market's strongest talent signal. The loc stacks three
degrade-safe layers, each optional:

    draft-capital   earlier overall pick ⇒ higher expected usage (a smooth monotone map)
    archetype       position baseline comp (a rookie WR ≠ a rookie K), from history
    college (CFBD)  athleticism (RAS) + college production, **only when `CFBD_API_KEY` set**

The whole thing is degrade-neutral by construction: with no draft frame the loc falls back
to the archetype baseline (still no crash, still wide); with no CFBD key the college layer
is simply absent (the brief's blocker path). A rookie we know nothing about ⇒ loc 0, wide
scale — a plain widened partial-pool, exactly the seam's neutral contract.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["RookiePrior", "RookiePriors"]

_ROOKIE_WIDEN = 1.8  # scale multiplier on the default → high epistemic for rookies
_DRAFT_MAX = 0.8  # top-pick loc boost on the log-opportunity scale (bounded)
_COLLEGE_MAX = 0.3  # extra college/athleticism nudge when CFBD present


@dataclass(frozen=True)
class RookiePrior:
    """One rookie's talent prior + the inputs that produced it (audit / E2)."""

    loc: float
    scale: float
    draft_overall: float | None
    archetype: str
    college_used: bool


class RookiePriors:
    """Builds rookie priors from an optional draft/combine frame + archetype baselines.

    `draft` is the E0 `combine_draft` table (player_id, position, draft_overall, ras, …) or
    None. When it is None *or* lacks CFBD-derived college columns, the college layer is
    skipped — that is the `CFBD_API_KEY`-absent degrade path.
    """

    def __init__(
        self,
        draft: pd.DataFrame | None,
        archetype_loc: dict[str, float],
        default_scale: float,
    ) -> None:
        self._arch = archetype_loc
        self._scale = default_scale
        self._by_id: dict[str, RookiePrior] = {}
        self._has_college = bool(
            draft is not None and "ras" in draft.columns and draft["ras"].notna().any()
        )
        if draft is not None:
            self._build(draft)

    def _build(self, draft: pd.DataFrame) -> None:
        d = draft.copy()
        d["player_id"] = d["player_id"].astype(str)
        overall = pd.to_numeric(d.get("draft_overall"), errors="coerce")
        for row, ov in zip(d.itertuples(index=False), overall, strict=False):
            pid = str(row.player_id)
            pos = str(getattr(row, "position", "") or "")
            arch = self._arch.get(pos, 0.0)
            draft_loc = _draft_capital_loc(ov)
            college_loc = self._college_loc(row) if self._has_college else 0.0
            loc = float(np.clip(arch + draft_loc + college_loc, -1.5, 1.5))
            self._by_id[pid] = RookiePrior(
                loc=loc,
                scale=self._scale * _ROOKIE_WIDEN,
                draft_overall=None if pd.isna(ov) else float(ov),
                archetype=pos or "UNK",
                college_used=self._has_college and college_loc != 0.0,
            )

    def _college_loc(self, row: object) -> float:
        ras = pd.to_numeric(getattr(row, "ras", np.nan), errors="coerce")
        if pd.isna(ras):
            return 0.0
        # RAS is 0–10; centre at 5 and map into a small bounded nudge
        return float(np.clip((float(ras) - 5.0) / 5.0, -1.0, 1.0) * _COLLEGE_MAX)

    def get(self, player_id: str, position: str) -> RookiePrior:
        """Rookie prior for a player; unknown rookie ⇒ archetype baseline + wide scale."""
        hit = self._by_id.get(str(player_id))
        if hit is not None:
            return hit
        return RookiePrior(
            loc=float(np.clip(self._arch.get(position, 0.0), -1.5, 1.5)),
            scale=self._scale * _ROOKIE_WIDEN,
            draft_overall=None,
            archetype=position or "UNK",
            college_used=False,
        )

    @property
    def college_available(self) -> bool:
        """True iff CFBD-derived college columns were present (key was set upstream)."""
        return self._has_college


def _draft_capital_loc(overall: float | None) -> float:
    """Map an overall draft pick to a bounded talent-loc boost (pick 1 ≈ +max, UDFA ≈ 0)."""
    if overall is None or pd.isna(overall) or overall <= 0:
        return 0.0
    # smooth decay: full boost early, ~0 by the late rounds (~pick 260)
    return float(_DRAFT_MAX * np.exp(-(float(overall) - 1.0) / 90.0))
