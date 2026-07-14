"""Archetype autoencoder — compress player feature vectors into a low-dim embedding.

The embedding space is (a) the GNN's node-feature input and (b) where rookie comps and
archetype clusters are found. A tiny symmetric MLP autoencoder in plain torch (no sklearn,
no torch-geometric) trained full-batch; ``encode∘decode`` reconstructs the standardized input
within tolerance so the latent code is information-preserving — the round-trip DoD gate.

`ponytail:` the whole model is two 2-layer MLPs; standardization is numpy, training is one
Adam loop. DEGRADE-NEUTRAL upstream: every consumer that reads a code also has a neutral
fallback, so a poorly-fit embedder never harms the base projection.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

__all__ = ["Autoencoder", "PlayerEmbedder", "PlayerEmbeddings", "embed_players"]


def _standardize(mat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Column z-score; zero-variance columns collapse to 0 (never divide by 0)."""
    mu = mat.mean(axis=0)
    sd = mat.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    return (mat - mu) / sd, mu, sd


class Autoencoder(nn.Module):
    """Symmetric MLP autoencoder: ``F → hidden → dim → hidden → F``."""

    def __init__(self, n_features: int, dim: int, hidden: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden), nn.ReLU(), nn.Linear(hidden, dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(dim, hidden), nn.ReLU(), nn.Linear(hidden, n_features)
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        z = self.encoder(x)
        return self.decoder(z), z


@dataclass
class PlayerEmbedder:
    """A fitted autoencoder plus its input standardization — the encode/decode seam."""

    model: Autoencoder
    mean: np.ndarray
    scale: np.ndarray
    recon_error: float

    @classmethod
    def fit(
        cls,
        matrix: np.ndarray,
        *,
        dim: int = 4,
        hidden: int = 16,
        epochs: int = 300,
        lr: float = 1e-2,
        seed: int = 0,
    ) -> PlayerEmbedder:
        """Train the autoencoder on `matrix` (rows = players) and record recon error."""
        torch.manual_seed(seed)
        mat = np.asarray(matrix, dtype=float)
        std, mu, sd = _standardize(mat)
        x = torch.tensor(std, dtype=torch.float32)
        model = Autoencoder(x.shape[1], min(dim, x.shape[1]), hidden)
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        loss_fn = nn.MSELoss()
        model.train()
        for _ in range(epochs):
            opt.zero_grad()
            recon, _ = model(x)
            loss = loss_fn(recon, x)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            recon, _ = model(x)
            err = float(loss_fn(recon, x))
        return cls(model=model, mean=mu, scale=sd, recon_error=err)

    def _std(self, matrix: np.ndarray) -> np.ndarray:
        return (np.asarray(matrix, dtype=float) - self.mean) / self.scale

    def encode(self, matrix: np.ndarray) -> np.ndarray:
        """`(N, F)` original-scale features → `(N, dim)` latent codes."""
        self.model.eval()
        with torch.no_grad():
            x = torch.tensor(self._std(matrix), dtype=torch.float32)
            return self.model.encoder(x).numpy()

    def decode(self, codes: np.ndarray) -> np.ndarray:
        """`(N, dim)` codes → reconstructed original-scale features."""
        self.model.eval()
        with torch.no_grad():
            z = torch.tensor(np.asarray(codes, dtype=float), dtype=torch.float32)
            std = self.model.decoder(z).numpy()
        return std * self.scale + self.mean

    def reconstruct(self, matrix: np.ndarray) -> np.ndarray:
        """Round-trip: ``decode(encode(matrix))`` back on the original feature scale."""
        return self.decode(self.encode(matrix))


@dataclass(frozen=True)
class PlayerEmbeddings:
    """Per-player latent codes plus the embedder that produced them.

    `codes` is ``(N, dim)`` aligned to `player_ids`; `embedder` keeps encode/decode so
    rookies (new rows) can be projected into the same space and round-trips can be checked.
    """

    player_ids: list[str]
    codes: np.ndarray  # (N, dim)
    embedder: PlayerEmbedder

    @property
    def dim(self) -> int:
        return int(self.codes.shape[1])

    @property
    def recon_error(self) -> float:
        return self.embedder.recon_error

    def embedding(self, player_id: str) -> np.ndarray:
        """The latent code of one player."""
        return self.codes[self.player_ids.index(str(player_id))]


def embed_players(
    matrix: np.ndarray,
    player_ids: list[str],
    *,
    dim: int = 4,
    hidden: int = 16,
    epochs: int = 300,
    lr: float = 1e-2,
    seed: int = 0,
) -> PlayerEmbeddings:
    """Fit an autoencoder on `matrix` and return the players' latent embeddings."""
    embedder = PlayerEmbedder.fit(
        matrix, dim=dim, hidden=hidden, epochs=epochs, lr=lr, seed=seed
    )
    codes = embedder.encode(matrix)
    return PlayerEmbeddings(player_ids=[str(p) for p in player_ids], codes=codes, embedder=embedder)
