"""Ecosystem GNN — teammate/OL effects via message passing over the player graph.

Nodes are players (features = autoencoder embeddings); edges connect players who share a
team (the "ecosystem"), with heavier weight onto the OL group, encoding that a skill
player's output depends on his QB/line context, not only his own history. One GraphSAGE-style
mean-aggregation layer in PLAIN torch (no torch-geometric):

    h' = σ(W_self · h + W_neigh · (Â h))          Â = row-normalized adjacency (self-loop)

The head predicts a per-player target; the *ecosystem adjustment* is what the graph model
adds over an identical graph-blind baseline. DEGRADE-NEUTRAL (rel=degrade / release policy):
the adjustment is additive and mean-centered, and an unknown player — or a model the ablation
could not validate — yields 0, so a non-converging graph never changes the base projection.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import torch
from torch import nn

__all__ = [
    "EcosystemAdjustment",
    "EcosystemGNN",
    "GraphSAGELayer",
    "build_player_graph",
    "fit_gnn_node_regression",
]

#: offensive-line position tokens that get the heavier ecosystem edge weight.
_OL_POSITIONS = ("OL", "C", "G", "T", "OT", "OG")


def build_player_graph(
    index: pd.DataFrame,
    *,
    ol_positions: tuple[str, ...] = _OL_POSITIONS,
    ol_weight: float = 2.0,
    self_weight: float = 1.0,
) -> np.ndarray:
    """Row-normalized adjacency `(N, N)` linking same-team players (+ self-loop).

    Teammates get weight 1, teammates in an OL position get `ol_weight` (the line lifts the
    whole offense), the diagonal gets `self_weight`. Rows are normalized so ``Â h`` is a
    convex neighbour-mean the message-passing layer can aggregate. Missing `team`/`position`
    columns degrade to a self-loop-only graph (no ecosystem signal, still valid).
    """
    n = len(index)
    teams = (
        index["team"].astype(str).to_numpy() if "team" in index.columns else np.array(["_"] * n)
    )
    pos = (
        index["position"].astype(str).to_numpy()
        if "position" in index.columns
        else np.array([""] * n)
    )
    adj = np.zeros((n, n), dtype=float)
    for i in range(n):
        adj[i, i] = self_weight
        for j in range(n):
            if i == j or teams[i] != teams[j]:
                continue
            adj[i, j] = ol_weight if pos[j] in ol_positions else 1.0
    row = adj.sum(axis=1, keepdims=True)
    return adj / np.where(row > 0, row, 1.0)


class GraphSAGELayer(nn.Module):
    """Mean-aggregation message passing: ``ReLU(W_self·h + W_neigh·(adj·h))``."""

    def __init__(self, in_dim: int, out_dim: int) -> None:
        super().__init__()
        self.self_lin = nn.Linear(in_dim, out_dim)
        self.neigh_lin = nn.Linear(in_dim, out_dim)

    def forward(self, h: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        return torch.relu(self.self_lin(h) + self.neigh_lin(adj @ h))


class EcosystemGNN(nn.Module):
    """One message-passing layer + a linear head → per-player scalar prediction.

    `use_graph=False` replaces the adjacency with the identity, collapsing the model to a
    graph-blind MLP of identical width — the honest ablation baseline (same capacity, no
    neighbour information).
    """

    def __init__(self, in_dim: int, *, hidden: int = 8, use_graph: bool = True) -> None:
        super().__init__()
        self.use_graph = use_graph
        self.layer = GraphSAGELayer(in_dim, hidden)
        self.head = nn.Linear(hidden, 1)

    def forward(self, h: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        a = adj if self.use_graph else torch.eye(adj.shape[0], dtype=adj.dtype)
        return self.head(self.layer(h, a)).squeeze(-1)


def fit_gnn_node_regression(
    codes: np.ndarray,
    adjacency: np.ndarray,
    target: np.ndarray,
    *,
    train_mask: np.ndarray | None = None,
    use_graph: bool = True,
    hidden: int = 8,
    epochs: int = 400,
    lr: float = 1e-2,
    seed: int = 0,
) -> tuple[EcosystemGNN, np.ndarray]:
    """Train an `EcosystemGNN` node regressor; returns (model, full-graph predictions).

    Transductive: all nodes sit in the graph, but the MSE loss is taken only over
    `train_mask` (all nodes if None), so held-out nodes measure genuine generalization.
    """
    torch.manual_seed(seed)
    h = torch.tensor(np.asarray(codes, dtype=float), dtype=torch.float32)
    adj = torch.tensor(np.asarray(adjacency, dtype=float), dtype=torch.float32)
    y = torch.tensor(np.asarray(target, dtype=float), dtype=torch.float32)
    if train_mask is None:
        tm = torch.ones(len(y), dtype=torch.bool)
    else:
        tm = torch.tensor(np.asarray(train_mask, dtype=bool))
    model = EcosystemGNN(h.shape[1], hidden=hidden, use_graph=use_graph)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        pred = model(h, adj)
        loss = loss_fn(pred[tm], y[tm])
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        full = model(h, adj).numpy()
    return model, full


@dataclass
class EcosystemAdjustment:
    """Degrade-neutral per-player additive ecosystem delta on a base projection.

    `player_scores` are mean-centered adjustments the validated GNN adds beyond the base;
    `active=False` (ablation showed no lift) makes every adjustment 0. An unknown player also
    yields 0 — so applying this can never worsen the base projection (the E1 seam guarantee).
    """

    player_scores: dict[str, float] = field(default_factory=dict)
    active: bool = True

    def adjustment(self, player_id: str) -> float:
        if not self.active:
            return 0.0
        return self.player_scores.get(str(player_id), 0.0)

    def apply(self, base: np.ndarray, player_ids: list[str]) -> np.ndarray:
        """Add each player's ecosystem delta to their base projection value."""
        base = np.asarray(base, dtype=float)
        return base + np.array([self.adjustment(p) for p in player_ids], dtype=float)
