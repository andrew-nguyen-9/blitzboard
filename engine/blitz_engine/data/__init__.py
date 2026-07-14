"""Engine data layer — source ingestion, reconciliation, and publish gating.

Subpackages land per unit. `reconcile/` (E4fix-team-reconcile) resolves each
player's current NFL team across disagreeing sources and gates publish when too
many players are unassigned or sources conflict.
"""
from __future__ import annotations
