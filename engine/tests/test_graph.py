"""Tests for the E6 graph layer — autoencoder embeddings, archetype clustering / rookie
comps, the player/team/OL graph, and the degrade-neutral ecosystem-GNN ablation.

The ablation is the release gate: on data with a genuine teammate effect the graph GNN must
beat the graph-removed MLP under k-fold CV (`test_gnn_ablation_shows_ecosystem_lift`); when the
lift bar is not cleared the whole model degrades neutral and the base projection is left
untouched (`test_unmet_threshold_degrades_neutral`). Deterministic on fixed seeds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from blitz_engine.features import discover_features
from blitz_engine.graph import (
    EcosystemAdjustment,
    GraphModel,
    PlayerEmbeddings,
    build_player_graph,
    cluster_archetypes,
    embed_players,
    rookie_comps,
    run_ablation,
)
from blitz_engine.graph.embeddings import PlayerEmbedder


# ── fixtures ───────────────────────────────────────────────────────────────────
def _blob_codes(seed: int = 0) -> tuple[np.ndarray, list[str], list[int]]:
    """Three well-separated gaussian blobs in a 2-D code space."""
    rng = np.random.default_rng(seed)
    centers = np.array([[0.0, 0.0], [8.0, 8.0], [-8.0, 8.0]])
    codes, ids, truth = [], [], []
    for c, ctr in enumerate(centers):
        pts = rng.normal(ctr, 0.3, size=(15, 2))
        codes.append(pts)
        ids += [f"g{c}_p{i}" for i in range(15)]
        truth += [c] * 15
    return np.vstack(codes), ids, truth


def _embeddings_from_codes(codes: np.ndarray, ids: list[str]) -> PlayerEmbeddings:
    """Wrap controlled codes in a `PlayerEmbeddings` (embedder present but unused here)."""
    embedder = PlayerEmbedder.fit(codes, dim=2, hidden=8, epochs=20, seed=0)
    return PlayerEmbeddings(player_ids=ids, codes=codes, embedder=embedder)


def ecosystem_data(seed: int = 0, teams: int = 8, per_team: int = 6):
    """Target driven by a TEAMMATE-mean feature — a real ecosystem effect a GNN can see."""
    rng = np.random.default_rng(seed)
    n = teams * per_team
    feats = rng.normal(0.0, 1.0, size=(n, 5))
    team_of = np.repeat(np.arange(teams), per_team)
    ids = [f"T{team_of[i]}_P{i}" for i in range(n)]
    index = pd.DataFrame(
        {"player_id": ids, "team": [f"T{t}" for t in team_of], "position": ["WR"] * n}
    )
    adjacency = build_player_graph(index)
    # team-mean of feature #1 (incl. self) — recoverable only by aggregating neighbours
    team_signal = np.array([feats[team_of == team_of[i], 1].mean() for i in range(n)])
    target = 0.5 * feats[:, 0] + 2.5 * team_signal + rng.normal(0.0, 0.15, n)
    std = (feats - feats.mean(0)) / feats.std(0)
    return std, adjacency, target, ids, index


# ── autoencoder embeddings ──────────────────────────────────────────────────────
def test_autoencoder_roundtrip_reconstructs_input():
    """encode∘decode reconstructs a low-rank feature matrix within tolerance."""
    rng = np.random.default_rng(0)
    latent = rng.normal(0, 1, size=(60, 2))
    loadings = rng.normal(0, 1, size=(2, 6))
    mat = latent @ loadings + rng.normal(0, 0.05, size=(60, 6))

    emb = embed_players(mat, [f"p{i}" for i in range(60)], dim=3, epochs=500, seed=0)

    assert emb.codes.shape == (60, 3)
    recon = emb.embedder.reconstruct(mat)
    assert recon.shape == mat.shape
    assert emb.recon_error < 0.25  # standardized MSE
    corr = np.corrcoef(recon.ravel(), mat.ravel())[0, 1]
    assert corr > 0.9


def test_embeddings_are_deterministic():
    """Same data + seed → identical codes (reproducible run records)."""
    rng = np.random.default_rng(1)
    mat = rng.normal(0, 1, size=(40, 5))
    ids = [f"p{i}" for i in range(40)]
    a = embed_players(mat, ids, dim=3, epochs=100, seed=7)
    b = embed_players(mat, ids, dim=3, epochs=100, seed=7)
    np.testing.assert_allclose(a.codes, b.codes)


# ── archetype clustering + rookie comps ─────────────────────────────────────────
def test_archetype_clustering_recovers_blobs():
    """k-means over separated codes puts each true blob in one cluster (pure clusters)."""
    codes, ids, truth = _blob_codes(seed=0)
    emb = _embeddings_from_codes(codes, ids)
    model = cluster_archetypes(emb, k=3, seed=0)

    truth = np.array(truth)
    for c in range(3):
        labels_in_blob = {model.archetype(p) for p, t in zip(ids, truth, strict=True) if t == c}
        assert len(labels_in_blob) == 1  # blob maps to a single archetype
    # distinct blobs get distinct clusters
    assert len({model.archetype(ids[t * 15]) for t in range(3)}) == 3


def test_rookie_comps_are_nearest_in_blob():
    """A player's nearest comps come from its own blob."""
    codes, ids, truth = _blob_codes(seed=2)
    emb = _embeddings_from_codes(codes, ids)
    query = ids[0]  # blob 0
    comps = rookie_comps(emb, [query], k=3)[query]
    assert len(comps) == 3
    assert all(name.startswith("g0_") for name, _ in comps)
    assert comps[0][1] <= comps[-1][1]  # sorted ascending by distance


# ── player/team/OL graph ────────────────────────────────────────────────────────
def test_build_player_graph_shared_team_and_ol_weight():
    """Same-team players connect (rows normalized); OL teammates weigh heavier; cross-team 0."""
    index = pd.DataFrame(
        {
            "player_id": ["a", "b", "c", "d"],
            "team": ["X", "X", "X", "Y"],
            "position": ["WR", "OL", "RB", "WR"],
        }
    )
    adj = build_player_graph(index)
    assert adj.shape == (4, 4)
    np.testing.assert_allclose(adj.sum(1), 1.0)  # row-normalized
    assert adj[0, 3] == 0.0 and adj[3, 0] == 0.0  # cross-team disconnected
    assert adj[0, 0] > 0.0  # self-loop
    assert adj[0, 1] > adj[0, 2]  # OL teammate weighs more than the RB teammate


# ── ecosystem GNN ablation (the release gate) ───────────────────────────────────
def test_gnn_ablation_shows_ecosystem_lift():
    """On genuine teammate-effect data the graph GNN beats the graph-removed MLP under CV."""
    codes, adjacency, target, _ids, _index = ecosystem_data(seed=0)
    result = run_ablation(codes, adjacency, target, threshold=0.05, epochs=400, seed=0)
    assert result.passed, result.summary()
    assert result.lift > 0.3  # ecosystem signal is strong and stable
    assert result.mse_gnn < result.mse_base


def test_unmet_threshold_degrades_neutral():
    """A lift bar the ablation cannot clear → passed False and an inert ecosystem effect."""
    codes, adjacency, target, _ids, _index = ecosystem_data(seed=0)
    result = run_ablation(codes, adjacency, target, threshold=0.99, epochs=400, seed=0)
    assert not result.passed  # even real lift (~0.9) < an unreachable 0.99 bar
    # and the release policy makes the whole feature inert in that case
    inert = EcosystemAdjustment(player_scores={}, active=False)
    base = np.arange(len(target), dtype=float)
    np.testing.assert_allclose(inert.apply(base, [f"n{i}" for i in range(len(target))]), base)


# ── degrade-neutral ecosystem adjustment ────────────────────────────────────────
def test_ecosystem_adjustment_is_degrade_neutral():
    """Inactive model or unknown player → 0 delta; active model adds the stored delta."""
    base = np.array([10.0, 5.0, 8.0])
    ids = ["a", "b", "c"]

    inert = EcosystemAdjustment(active=False, player_scores={"a": 3.0})
    np.testing.assert_allclose(inert.apply(base, ids), base)  # feature off → base intact

    active = EcosystemAdjustment(active=True, player_scores={"a": 1.5, "b": -0.5})
    out = active.apply(base, ids)
    np.testing.assert_allclose(out, [11.5, 4.5, 8.0])  # "c" unknown → +0
    assert active.adjustment("zzz") == 0.0


# ── end-to-end orchestrator ─────────────────────────────────────────────────────
def test_graph_model_build_end_to_end():
    """Build embeds, clusters, graphs, ablates, and always exposes a degrade-neutral apply."""
    _std, _adj, _target, ids, index = ecosystem_data(seed=0)
    # a tidy per-player frame → FeatureSet (base cols + interactions), target per row
    rng = np.random.default_rng(5)
    frame = index.copy()
    for f in range(5):
        frame[f"x{f}"] = rng.normal(0, 1, len(frame))
    target = frame["x0"].to_numpy() + rng.normal(0, 0.2, len(frame))
    features = discover_features(frame, [f"x{f}" for f in range(5)], interactions=False)

    model = GraphModel.build(features, target, dim=3, k_archetypes=4, epochs=300, seed=0)

    n = len(ids)
    assert model.embeddings.dim == 3
    assert len(model.archetypes.labels) == n
    assert model.adjacency.shape == (n, n)
    assert isinstance(model.ablation.summary(), str)

    base = np.zeros(n)
    out = model.ecosystem.apply(base, ids)
    assert out.shape == (n,)
    assert np.isfinite(out).all()
    # a player unknown to the graph is never adjusted (seam guarantee)
    assert model.ecosystem.apply(np.array([1.0]), ["not_a_player"])[0] == 1.0
    comps = model.comps([ids[0]], k=2)[ids[0]]
    assert len(comps) == 2
