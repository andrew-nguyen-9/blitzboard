"""`AvailabilityModel` — fuse the hazard base rate with the live injury report + suspensions.

Weekly P(available) per player = the base survival hazard (`DiscreteTimeHazard`), OVERRIDDEN
by hard live signals when present:

    suspension            ⇒ P(available) = 0   (a suspended player cannot play, full stop)
    injury-report status  ⇒ P(available) = STATUS_P[status]   (OUT→0, DOUBTFUL→0.1, …)
    healthy / no status   ⇒ the fitted hazard's P(available)  (or the neutral degrade value)

Precedence is deliberate: suspension > report status > model. The report is a *human* signal
that dominates the statistical prior for the week it covers (game-time decisions), and a
suspension is certainty. Everything else falls back to the hazard, which itself degrades to
`neutral_p` (default 1.0 = no-op) when injury history is absent — so a league with zero
injury data gets untouched projections rather than a silently shrunk board.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from blitz_engine.survival.hazard import DiscreteTimeHazard

__all__ = [
    "STATUS_P",
    "AvailabilityModel",
    "resolve_status_p",
]

#: Injury-report designation → P(available) that week. Missing/blank ⇒ defer to the hazard.
#: Keys are upper-cased on lookup so "Out"/"out"/"OUT" all resolve.
STATUS_P: dict[str, float] = {
    "ACTIVE": 1.0,
    "HEALTHY": 1.0,
    "PROBABLE": 0.95,
    "QUESTIONABLE": 0.5,
    "DOUBTFUL": 0.10,
    "OUT": 0.0,
    "INACTIVE": 0.0,
    "DNP": 0.0,
    "IR": 0.0,
    "PUP": 0.0,
    "NFI": 0.0,
    "SUSP": 0.0,
    "SUSPENDED": 0.0,
}


def resolve_status_p(status: object, table: Mapping[str, float] = STATUS_P) -> float | None:
    """Map a raw report status to P(available), or ``None`` to defer to the hazard model."""
    if status is None:
        return None
    s = str(status).strip().upper()
    if not s or s in {"NAN", "NA", "NONE"}:
        return None
    return table.get(s)


@dataclass
class AvailabilityModel:
    """Player-week availability = hazard ∘ live-report ∘ suspension, degrade-safe throughout.

    ``fit(history)`` trains the underlying `DiscreteTimeHazard`; ``p_available(frame)`` returns
    a `player_id → P(available)` Series combining the base rate with any `status`/`suspended`
    columns on `frame`. With neither injury history nor live columns the whole layer collapses
    to `neutral_p` (1.0), i.e. a pure no-op — the projection passes through unchanged.
    """

    neutral_p: float = 1.0
    status_table: Mapping[str, float] = field(default_factory=lambda: dict(STATUS_P))
    hazard: DiscreteTimeHazard = field(default_factory=DiscreteTimeHazard)

    def fit(self, history: pd.DataFrame, **kw: object) -> AvailabilityModel:
        """Fit the base hazard on injury history (person-period `out` events)."""
        self.hazard.fit(history, **kw)
        return self

    def _base(self, frame: pd.DataFrame) -> np.ndarray:
        """Hazard-derived P(available) per row, or the neutral value when unfitted."""
        if self.hazard.fitted:
            return np.clip(self.hazard.predict_available(frame), 0.0, 1.0)
        return np.full(len(frame), self.neutral_p, dtype=float)

    def p_available(
        self,
        frame: pd.DataFrame,
        *,
        status_col: str = "status",
        suspended_col: str = "suspended",
        player_col: str = "player_id",
    ) -> pd.Series:
        """`player_id → P(available)` for the given current player-week frame.

        Base hazard first, then override row-wise: an explicit report `status` wins over the
        model, and a truthy `suspended` flag forces 0 (highest precedence).
        """
        p = self._base(frame)
        if status_col in frame.columns:
            for i, raw in enumerate(frame[status_col].to_numpy()):
                override = resolve_status_p(raw, self.status_table)
                if override is not None:
                    p[i] = override
        if suspended_col in frame.columns:
            susp = frame[suspended_col].fillna(False).astype(bool).to_numpy()
            p = np.where(susp, 0.0, p)
        return pd.Series(
            np.clip(p, 0.0, 1.0),
            index=frame[player_col].astype(str).to_numpy(),
            name="p_available",
        )
