"""`blitz_engine.graph` — E6 graph/embedding layer (OPTIONAL, degrade-neutral).

Sits over the E6 feature layer and the E1 projection core. Three jobs the brief names:

    embed_players / PlayerEmbeddings   autoencoder → low-dim player codes (round-trippable)
    cluster_archetypes / rookie_comps  archetypes + statistical comps in the code space
    EcosystemGNN / run_ablation        message-passing GNN for teammate/OL ecosystem effects

`GraphModel.build` orchestrates all of it: aggregate a feature frame to one node per player,
embed, cluster, build the player/team/OL graph, run the ablation, and — ONLY if the ablation
shows held-out ecosystem lift — expose a bounded `EcosystemAdjustment`. rel=degrade (release
policy): no lift ⇒ the adjustment is inert (every player → 0), so the base projection is
returned unchanged and a non-converging graph never harms the fit. No sklearn / no
torch-geometric: a plain-torch autoencoder + GraphSAGE layer, numpy k-means.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from blitz_engine.features.discovery import FeatureSet
from blitz_engine.graph.ablation import AblationResult, run_ablation
from blitz_engine.graph.archetypes import ArchetypeModel, cluster_archetypes, rookie_comps
from blitz_engine.graph.embeddings import (
    Autoencoder,
    PlayerEmbedder,
    PlayerEmbeddings,
    embed_players,
)
from blitz_engine.graph.gnn import (
    EcosystemAdjustment,
    EcosystemGNN,
    GraphSAGELayer,
    build_player_graph,
    fit_gnn_node_regression,
)

__all__ = [
    "AblationResult",
    "ArchetypeModel",
    "Autoencoder",
    "EcosystemAdjustment",
    "EcosystemGNN",
    "GraphModel",
    "GraphSAGELayer",
    "PlayerEmbedder",
    "PlayerEmbeddings",
    "build_player_graph",
    "cluster_archetypes",
    "embed_players",
    "fit_gnn_node_regression",
    "rookie_comps",
    "run_ablation",
]


def _aggregate_nodes(
    features: FeatureSet, target: np.ndarray
) -> tuple[list[str], np.ndarray, np.ndarray, pd.DataFrame]:
    """Collapse a (possibly player-week) feature frame to one node per player.

    Feature columns and the target are averaged per player; team/position are taken as the
    player's first value. Preserves first-appearance order so codes/adjacency stay aligned.
    """
    idx = features.index.reset_index(drop=True)
    if "player_id" not in idx.columns:
        raise ValueError("feature index needs a 'player_id' column to build a player graph")
    df = pd.DataFrame({"player_id": idx["player_id"].astype(str).to_numpy()})
    df["team"] = idx["team"].astype(str).to_numpy() if "team" in idx.columns else "_"
    df["position"] = idx["position"].astype(str).to_numpy() if "position" in idx.columns else ""
    feat_cols = [f"_f{i}" for i in range(features.n_features)]
    df[feat_cols] = features.matrix
    df["_target"] = np.asarray(target, dtype=float)

    grp = df.groupby("player_id", sort=False)
    node_ids = [str(p) for p in grp.groups]
    meta = grp[["team", "position"]].first().loc[node_ids]
    node_mat = grp[feat_cols].mean().loc[node_ids].to_numpy()
    node_target = grp["_target"].mean().loc[node_ids].to_numpy()
    node_index = pd.DataFrame(
        {
            "player_id": node_ids,
            "team": meta["team"].to_numpy(),
            "position": meta["position"].to_numpy(),
        }
    )
    return node_ids, node_mat, node_target, node_index


@dataclass
class GraphModel:
    """The assembled E6 graph model: embeddings + archetypes + validated ecosystem effect."""

    embeddings: PlayerEmbeddings
    archetypes: ArchetypeModel
    adjacency: np.ndarray
    ablation: AblationResult
    ecosystem: EcosystemAdjustment

    @property
    def active(self) -> bool:
        """Whether the ecosystem effect survived the ablation (else degrade-neutral)."""
        return self.ecosystem.active

    def comps(self, query_ids: list[str], *, k: int = 3) -> dict[str, list[tuple[str, float]]]:
        """Nearest embedding comps for the given players (rookie-comp lookup)."""
        return rookie_comps(self.embeddings, query_ids, k=k)

    @classmethod
    def build(
        cls,
        features: FeatureSet,
        target: np.ndarray,
        *,
        dim: int = 4,
        k_archetypes: int = 4,
        threshold: float = 0.05,
        epochs: int = 400,
        seed: int = 0,
    ) -> GraphModel:
        """Embed → cluster → graph → ablate; expose the ecosystem effect only if it lifts."""
        node_ids, node_mat, node_target, node_index = _aggregate_nodes(features, target)
        embeddings = embed_players(node_mat, node_ids, dim=dim, epochs=epochs, seed=seed)
        archetypes = cluster_archetypes(embeddings, k=k_archetypes, seed=seed)
        adjacency = build_player_graph(node_index)
        ablation = run_ablation(
            embeddings.codes, adjacency, node_target,
            threshold=threshold, epochs=epochs, seed=seed,
        )
        if ablation.passed:
            delta = ablation.gnn_pred - ablation.base_pred
            delta = delta - delta.mean()
            scores = {p: float(d) for p, d in zip(node_ids, delta, strict=True)}
            ecosystem = EcosystemAdjustment(player_scores=scores, active=True)
        else:
            ecosystem = EcosystemAdjustment(player_scores={}, active=False)
        return cls(
            embeddings=embeddings,
            archetypes=archetypes,
            adjacency=adjacency,
            ablation=ablation,
            ecosystem=ecosystem,
        )
