"""Archetype clustering + rookie comps over the autoencoder embedding space.

k-means (numpy, fixed seed — no sklearn) partitions players into archetypes in the latent
space; `rookie_comps` returns each query player's nearest veterans by embedding distance —
the "who does this rookie play like" lookup that the same embedder makes possible for
players with no NFL history. Both are pure numpy over the codes `embed_players` produces.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from blitz_engine.graph.embeddings import PlayerEmbeddings

__all__ = ["ArchetypeModel", "cluster_archetypes", "rookie_comps"]


def _kmeanspp_init(x: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """k-means++ seeding: farther points are likelier centers → avoids blob collapse."""
    centroids = [x[rng.integers(len(x))]]
    for _ in range(1, k):
        d2 = np.min([((x - c) ** 2).sum(1) for c in centroids], axis=0)
        total = d2.sum()
        probs = d2 / total if total > 0 else np.full(len(x), 1.0 / len(x))
        centroids.append(x[rng.choice(len(x), p=probs)])
    return np.array(centroids)


def _kmeans(
    x: np.ndarray, k: int, *, seed: int = 0, iters: int = 100
) -> tuple[np.ndarray, np.ndarray]:
    """Lloyd's k-means with k-means++ seeding; returns (labels, centroids)."""
    rng = np.random.default_rng(seed)
    centroids = _kmeanspp_init(x, k, rng).copy()
    labels = np.full(len(x), -1, dtype=int)
    for _ in range(iters):
        dist = ((x[:, None, :] - centroids[None, :, :]) ** 2).sum(-1)
        new = dist.argmin(1)
        if np.array_equal(new, labels):
            break
        labels = new
        for c in range(k):
            members = labels == c
            if members.any():
                centroids[c] = x[members].mean(0)
    return labels, centroids


@dataclass(frozen=True)
class ArchetypeModel:
    """Player → archetype-cluster assignment in embedding space."""

    player_ids: list[str]
    labels: np.ndarray  # (N,) int cluster id
    centroids: np.ndarray  # (k, dim)

    @property
    def k(self) -> int:
        return int(self.centroids.shape[0])

    def archetype(self, player_id: str) -> int:
        """The cluster id a player belongs to."""
        return int(self.labels[self.player_ids.index(str(player_id))])

    def members(self, cluster: int) -> list[str]:
        """All player ids in one archetype cluster."""
        return [p for p, lab in zip(self.player_ids, self.labels, strict=True) if lab == cluster]


def cluster_archetypes(
    embeddings: PlayerEmbeddings, *, k: int = 4, seed: int = 0
) -> ArchetypeModel:
    """Cluster players into `k` archetypes over their latent codes (k clamped to N)."""
    x = np.asarray(embeddings.codes, dtype=float)
    kk = int(min(max(k, 1), len(x)))
    labels, centroids = _kmeans(x, kk, seed=seed)
    return ArchetypeModel(
        player_ids=list(embeddings.player_ids), labels=labels, centroids=centroids
    )


def rookie_comps(
    embeddings: PlayerEmbeddings,
    query_ids: list[str],
    *,
    k: int = 3,
    pool_ids: list[str] | None = None,
) -> dict[str, list[tuple[str, float]]]:
    """Nearest `k` embedding neighbours for each query player (their statistical comps).

    `pool_ids` restricts who a rookie may be compared against (e.g. veterans only); default
    is every embedded player. Distance is Euclidean in the latent space; the query itself is
    always excluded.
    """
    ids = embeddings.player_ids
    codes = np.asarray(embeddings.codes, dtype=float)
    pool = [str(p) for p in (pool_ids if pool_ids is not None else ids)]
    out: dict[str, list[tuple[str, float]]] = {}
    for q in query_ids:
        qi = ids.index(str(q))
        cand = [
            (p, float(np.linalg.norm(codes[qi] - codes[ids.index(p)])))
            for p in pool
            if p != str(q)
        ]
        cand.sort(key=lambda kv: kv[1])
        out[str(q)] = cand[:k]
    return out
