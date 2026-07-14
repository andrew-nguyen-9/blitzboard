"""`blitz_engine.survival` — injury/availability survival model → weekly P(available).

E2 on the v4 engine spine. A discrete-time logistic hazard turns age / workload / injury
history / a time-varying **recurrence** covariate into a weekly P(available) per player; the
live injury report and suspensions override it; that probability then (a) **multiplies into
every projection** and (b) **redistributes the Dirichlet workload share to backups** the
moment a starter is ruled out — the usage shift predicted BEFORE the box score. Public surface:

    DiscreteTimeHazard   fit person-period `out` events → P(available); no NUTS, no lifelines
    AvailabilityModel    hazard ∘ injury-report status ∘ suspension → player_id → P(available)
    STATUS_P             injury-report designation → P(available) (OUT→0, QUESTIONABLE→0.5, …)
    apply_availability   fold P(available) into a Projection (scale numbers + redistribute)
    redistribute_shares  continuous α-reweight + within-team renormalise (E1 Dirichlet)
    scale_quantiles      multiply P(available) into the publishable distribution columns

Degrade-safe throughout: no injury history ⇒ the hazard stays unfitted and P defaults to 1.0,
and any player missing from the availability map passes through unscaled — a missing signal
can never worsen the base projection (mirrors E1-core's seam guarantee).
"""
from __future__ import annotations

from blitz_engine.survival.availability import (
    STATUS_P,
    AvailabilityModel,
    resolve_status_p,
)
from blitz_engine.survival.hazard import DiscreteTimeHazard, build_person_periods
from blitz_engine.survival.redistribution import (
    SCALED_COLUMNS,
    apply_availability,
    redistribute_shares,
    scale_quantiles,
)

__all__ = [
    "SCALED_COLUMNS",
    "STATUS_P",
    "AvailabilityModel",
    "DiscreteTimeHazard",
    "apply_availability",
    "build_person_periods",
    "redistribute_shares",
    "resolve_status_p",
    "scale_quantiles",
]
