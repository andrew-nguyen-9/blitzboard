"""The RL draft policy net + its instant-inference wrapper (E4-rl-policy).

The distilled `FastDraftPolicy` (`value/policy.py`) is a *linear* model over the four scarcity
features (`FEATURE_NAMES` = equity, vona, run_prob, need). This module lifts that to a tiny
**non-linear** policy net trained by PPO self-play (`train.py`) whose reward is roster equity.
The net scores each open position exactly like the linear policy — one forward pass over a
``[n_positions, 4]`` feature matrix the live board already produces — so it is a drop-in for the
distilled policy on the clock (`RLDraftPolicy.pick` mirrors `FastDraftPolicy.pick`).

* `DraftPolicyNet` — MLP ``4 → hidden → 1`` scoring a position's feature vector.
* `RLDraftPolicy` — the live wrapper: reuses `policy.position_features`, argmaxes the net over
  legal positions, takes that position's best remaining player. Instant inference (no sim, no
  search) under ``torch.no_grad``.
* `warm_start_net` — behaviour-clone the net to the distilled linear policy so training *starts*
  scarcity-aware (never worse than the shipped cold policy) instead of from noise.

`ponytail:` the net eats the *same* four features and the *same* `position_features` extractor as
the linear policy, so the only new surface is one `nn.Module`; warm-start is one MSE fit to the
distilled weights — no bespoke feature stack, no new board math.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from blitz_engine.value.equity import LiveBoard, live_draft_value
from blitz_engine.value.opponent import OpponentField, TeamState
from blitz_engine.value.policy import (
    FEATURE_NAMES,
    PolicyWeights,
    position_features,
)

N_FEATURES = len(FEATURE_NAMES)


class DraftPolicyNet(nn.Module):
    """Scores a single position's scarcity-feature vector; a draft is an argmax/softmax over these.

    Input is ``[..., N_FEATURES]`` (the `FEATURE_NAMES` order), output ``[...]`` scalar scores.
    Deliberately small (one hidden layer, ``float32``, CPU) — the whole point is instant live
    inference, and PPO self-play only has four inputs to bend.
    """

    def __init__(self, hidden: int = 16) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(N_FEATURES, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # noqa: D102
        return self.net(x.float()).squeeze(-1)

    def score_positions(self, feats: Mapping[str, np.ndarray]) -> dict[str, float]:
        """Per-position scalar score for a `position_features` map (no grad, eval mode)."""
        if not feats:
            return {}
        positions = list(feats)
        x = torch.from_numpy(np.stack([feats[p] for p in positions])).float()
        with torch.no_grad():
            scores = self(x)
        return {p: float(s) for p, s in zip(positions, scores.tolist(), strict=True)}


@dataclass
class RLDraftPolicy:
    """Instant-inference live policy backed by a `DraftPolicyNet` — a drop-in for `FastDraftPolicy`.

    ``pick``/``action_scores``/``pick_live`` share the distilled policy's signatures so the draft
    room can swap this in when it beats the distilled baseline (and fall back otherwise). Scoring
    is one forward pass per open position over the board the room already computed.
    """

    net: DraftPolicyNet

    def action_scores(
        self, board: LiveBoard, slots_left: Sequence[str], positions: Mapping[str, str]
    ) -> dict[str, float]:
        """Net score for each legal open position (higher = draft here)."""
        return self.net.score_positions(position_features(board, slots_left, positions))

    def pick(
        self, board: LiveBoard, slots_left: Sequence[str], positions: Mapping[str, str]
    ) -> tuple[str, str] | None:
        """Fast live lookup → ``(player_id, position)`` to draft, or None if nothing legal."""
        scores = self.action_scores(board, slots_left, positions)
        if not scores:
            return None
        pos = max(scores, key=lambda p: scores[p])
        top = _best_available(board, pos, positions)
        return (top, pos) if top is not None else None

    def pick_live(
        self,
        players_by_position: Mapping[str, Sequence[tuple[str, float]]],
        opponent_field: OpponentField,
        slots_left: Sequence[str],
        *,
        opponent_counts: Sequence[TeamState] | None = None,
        sensitivity: float = 1.0,
    ) -> tuple[str, str] | None:
        """Full live path: build the equity board then pick (mirrors `FastDraftPolicy`)."""
        board = live_draft_value(
            players_by_position, opponent_field,
            opponent_counts=opponent_counts, sensitivity=sensitivity,
        )
        positions = {pid: pos for pos, lst in players_by_position.items() for pid, _ in lst}
        return self.pick(board, slots_left, positions)


def _best_available(
    board: LiveBoard, position: str, positions: Mapping[str, str]
) -> str | None:
    """Highest-equity available player at ``position`` (value-greedy within it)."""
    best_pid, best_ev = None, -math.inf
    for pid, ev in board.equity_value.items():
        if positions.get(pid) == position and ev > best_ev:
            best_pid, best_ev = pid, ev
    return best_pid


# --- warm start ----------------------------------------------------------------------------
# Plausible ranges for each scarcity feature, used to sample a behaviour-cloning box that spans
# the boards the net will see live (equity/VONA in points·week⁻¹, run_prob & need in [0, 1]).
_FEATURE_RANGES: tuple[tuple[float, float], ...] = (
    (-5.0, 30.0),  # equity (scarcity-adjusted VORP)
    (0.0, 20.0),   # vona
    (0.0, 1.0),    # run_prob
    (0.0, 1.0),    # need
)


def warm_start_net(
    weights: PolicyWeights | None = None,
    *,
    hidden: int = 16,
    n_samples: int = 4096,
    n_steps: int = 300,
    lr: float = 0.01,
    seed: int = 0,
) -> DraftPolicyNet:
    """Behaviour-clone a fresh net to the distilled linear policy so training starts informed.

    Samples feature vectors across `_FEATURE_RANGES`, regresses the net onto the distilled
    linear score ``weights·x`` (standardised) by Adam+MSE. The result argmax-matches the distilled
    policy on realistic boards, giving PPO a scarcity-aware — hence degrade-neutral — start rather
    than random init. `ponytail:` the target is just the shipped `PolicyWeights`, no relabelling.
    """
    w = (weights or PolicyWeights.default()).coef.astype(np.float32)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    lo = np.array([r[0] for r in _FEATURE_RANGES], dtype=np.float32)
    hi = np.array([r[1] for r in _FEATURE_RANGES], dtype=np.float32)
    x_np = lo + (hi - lo) * rng.random((n_samples, N_FEATURES), dtype=np.float32)
    y_np = x_np @ w
    # Standardise the linear target so MSE is scale-free (argmax is invariant to affine y).
    y_np = (y_np - y_np.mean()) / (y_np.std() or 1.0)

    x = torch.from_numpy(x_np)
    y = torch.from_numpy(y_np)
    net = DraftPolicyNet(hidden=hidden)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    for _ in range(n_steps):
        opt.zero_grad()
        loss = loss_fn(net(x), y)
        loss.backward()
        opt.step()
    return net
