"""GNN ablation — does the ecosystem graph actually lift prediction?

rel=degrade (release policy): the graph model earns its place only if message passing over the
real player/team/OL graph beats the SAME network with the graph removed — an identical-capacity
MLP on the node features (``use_graph=False``), the standard GNN ablation. `run_ablation` scores
both with k-fold node cross-validation (out-of-fold predictions over every node, so the estimate
is low-variance) and reports ``lift = (mse_base − mse_gnn) / mse_base``. `passed = lift ≥
threshold`; otherwise the caller degrades neutral — feature off, base projection intact, no fake
green. The out-of-fold predictions also give the per-player ecosystem delta the graph adds.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from blitz_engine.graph.gnn import fit_gnn_node_regression

__all__ = ["AblationResult", "run_ablation"]


@dataclass(frozen=True)
class AblationResult:
    """Cross-validated comparison of the ecosystem GNN against a graph-blind MLP baseline."""

    mse_base: float
    mse_gnn: float
    lift: float
    threshold: float
    passed: bool
    gnn_pred: np.ndarray = field(default_factory=lambda: np.empty(0), repr=False)
    base_pred: np.ndarray = field(default_factory=lambda: np.empty(0), repr=False)

    def summary(self) -> str:
        verdict = "LIFT" if self.passed else "DROPPED (degrade-neutral)"
        return (
            f"ecosystem lift={self.lift:+.1%} "
            f"(mlp_mse={self.mse_base:.4f} gnn_mse={self.mse_gnn:.4f}) → {verdict}"
        )


def run_ablation(
    codes: np.ndarray,
    adjacency: np.ndarray,
    target: np.ndarray,
    *,
    threshold: float = 0.05,
    folds: int = 5,
    hidden: int = 8,
    epochs: int = 400,
    lr: float = 1e-2,
    seed: int = 0,
) -> AblationResult:
    """K-fold node CV of the graph GNN vs a graph-blind MLP; scores the ecosystem lift.

    Every node is held out in exactly one fold; the graph model and the graph-removed model
    are trained identically (same width / epochs / seed) on each fold's training nodes and
    predict the held-out nodes. Out-of-fold MSE over all nodes drives the lift.
    """
    codes = np.asarray(codes, dtype=float)
    target = np.asarray(target, dtype=float)
    n = len(target)
    k = int(min(max(folds, 2), n))
    rng = np.random.default_rng(seed + 99)
    perm = rng.permutation(n)

    gnn_pred = np.zeros(n)
    base_pred = np.zeros(n)
    for fi in range(k):
        test = perm[fi::k]
        train_mask = np.ones(n, dtype=bool)
        train_mask[test] = False
        _, g_full = fit_gnn_node_regression(
            codes, adjacency, target, train_mask=train_mask,
            use_graph=True, hidden=hidden, epochs=epochs, lr=lr, seed=seed,
        )
        _, b_full = fit_gnn_node_regression(
            codes, adjacency, target, train_mask=train_mask,
            use_graph=False, hidden=hidden, epochs=epochs, lr=lr, seed=seed,
        )
        gnn_pred[test] = g_full[test]
        base_pred[test] = b_full[test]

    mse_gnn = float(np.mean((gnn_pred - target) ** 2))
    mse_base = float(np.mean((base_pred - target) ** 2))
    lift = (mse_base - mse_gnn) / mse_base if mse_base > 0 else 0.0
    return AblationResult(
        mse_base=mse_base,
        mse_gnn=mse_gnn,
        lift=lift,
        threshold=threshold,
        passed=lift >= threshold,
        gnn_pred=gnn_pred,
        base_pred=base_pred,
    )
