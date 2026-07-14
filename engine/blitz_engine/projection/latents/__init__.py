"""`blitz_engine.projection.latents` — OPTIONAL, degrade-neutral latent structures (E1-latents).

Plugs E1-core's `LatentHook` seam (`model.py`) with low-rank team/matchup/pairing structure
learned by hierarchical shrinkage — no fit, no sklearn, just closed-form empirical-Bayes
posterior means + a hard clip. Four latents, each additive on the log scale the core consumes:

    DefenseLatent    opponent-adjusted defensive strength per (team, position)  → efficiency
                     + a within-team position-differential opportunity (share) shift
    OLineLatent      per-team O-line / pass-pro → RB rush efficiency + the pass floor
    EcosystemLatent  per-team offensive ecosystem → a rising-tide ypo lift
    ChemistryLatent  QB–receiver chemistry, HARD-regularised + ABLATION-GATED (drops if noise)

`LatentModel.fit(history, matchups=...)` returns the ready-to-inject
``HierarchicalProjector(latent=...)`` hook. rel=DEGRADE: thin data / a failed self-check flips
the whole model neutral (all-zeros), and the chemistry latent drops itself unless significant —
so a latent can never make the base projection worse. Its learned effects are exposed for
**E3-correlation** and the **SOS** read.
"""
from __future__ import annotations

from blitz_engine.projection.latents.estimators import (
    ChemistryLatent,
    DefenseLatent,
    EcosystemLatent,
    OLineLatent,
    ResolveContext,
)
from blitz_engine.projection.latents.model import LatentModel
from blitz_engine.projection.latents.shrinkage import (
    clip_latent,
    grouped_shrunk_effect,
    opponent_adjust,
)

__all__ = [
    "ChemistryLatent",
    "DefenseLatent",
    "EcosystemLatent",
    "LatentModel",
    "OLineLatent",
    "ResolveContext",
    "clip_latent",
    "grouped_shrunk_effect",
    "opponent_adjust",
]
