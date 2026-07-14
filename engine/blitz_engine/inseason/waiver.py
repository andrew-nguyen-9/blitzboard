"""Thompson-sampling waiver bandit — exploit vs explore over ROS value posteriors (E5).

The weekly waiver claim is a bandit problem: each candidate is an *arm* whose true
rest-of-season (ROS) value you only know as a **posterior** — a mean plus an *epistemic*
spread (how unsure you are about the player's real talent, not week-to-week noise). A
breakout-candidate rookie has a modest mean but a wide posterior; a known veteran has a tight
one. Greedily claiming the highest posterior *mean* every week never gambles on the upside the
wide posteriors hide; always chasing the widest posterior burns claims on noise. Thompson
sampling resolves the exploit/explore tension exactly right: it claims each arm in proportion
to the probability that arm is actually the best.

`ponytail:` Thompson sampling here is literally "draw one sample from every candidate's
posterior (plus the incumbent you'd drop), take the argmax" repeated ``n_draws`` times — the
fraction of draws an arm wins is its claim priority. No bandit framework, no Beta/Gamma
conjugacy machinery; the posteriors are Gaussians (mean, epistemic sd) and the draw is one
vectorised ``rng.standard_normal``. The exploit-vs-flyer label is read straight off the gap
between an arm's expected-value rank and its Thompson rank: a sleeper that ranks better by
Thompson allocation than by mean is being lifted by uncertainty — a flyer.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WaiverCandidate:
    """One waiver/free-agent arm: a Gaussian posterior over the player's true ROS value.

    ``mean`` is the posterior mean ROS value (points·week⁻¹, the same units E4's value board
    uses); ``epistemic_sd`` is the posterior *uncertainty* about that true value — wide for
    unproven upside plays (flyers), tight for established producers. It is not the week-to-week
    scoring variance; it is how unsure the model is about the mean itself.
    """

    id: str
    position: str
    mean: float
    epistemic_sd: float = 0.0


@dataclass(frozen=True)
class WaiverRec:
    """A ranked waiver recommendation: its Thompson claim priority + exploit/flyer read."""

    id: str
    position: str
    mean: float
    epistemic_sd: float
    pick_prob: float          # Thompson allocation: P(this arm is the best available add)
    beats_incumbent: bool     # P(sample > the drop candidate's sample) > 0.5
    kind: str                 # "exploit" (top by expected value) | "flyer" (lifted by upside)
    reason: str


@dataclass(frozen=True)
class WaiverBoard:
    """The full waiver board for a week: arms ranked by Thompson claim priority."""

    ranked: tuple[WaiverRec, ...]
    incumbent_value: float
    n_draws: int
    seed: int

    def best(self) -> WaiverRec | None:
        """The top claim priority (None if there were no candidates)."""
        return self.ranked[0] if self.ranked else None

    def adds(self) -> tuple[WaiverRec, ...]:
        """Only the arms worth a claim — those beating the incumbent you'd drop."""
        return tuple(r for r in self.ranked if r.beats_incumbent)


def waiver_bandit(
    candidates: Sequence[WaiverCandidate],
    *,
    incumbent_value: float = 0.0,
    incumbent_sd: float = 0.0,
    n_draws: int = 4000,
    seed: int = 20240813,
) -> WaiverBoard:
    """Rank waiver candidates by Thompson sampling over their ROS value posteriors.

    Draws ``n_draws`` joint samples from every candidate's Gaussian posterior plus the
    incumbent (the player you would drop, ``incumbent_value`` ± ``incumbent_sd``), and takes the
    argmax each draw. A candidate's ``pick_prob`` is the fraction of draws it wins that argmax —
    its claim priority (and a natural FAAB-bid weight). High-``epistemic_sd`` arms win draws
    through their upper tail even at a lower mean, so they surface as *flyers* (explore) while
    the highest-expected-value arm is the *exploit* play.

    The draw is seeded, so the whole board is deterministic for a given ``seed``.

    Args:
        candidates: The available waiver/FA arms, each a posterior over ROS value.
        incumbent_value / incumbent_sd: The posterior of the roster player you'd drop; an arm
            must clear this to be worth a claim. Defaults model a truly empty slot (0 ± 0).
        n_draws: Thompson draws (more → tighter allocation estimates).
        seed: RNG seed — determinism.

    Returns:
        A `WaiverBoard`: candidates ranked by Thompson claim priority, each tagged
        exploit/flyer, with the arms that beat the incumbent exposed via `WaiverBoard.adds`.
    """
    if not candidates:
        return WaiverBoard(
            ranked=(), incumbent_value=float(incumbent_value), n_draws=n_draws, seed=seed
        )

    means = np.array([c.mean for c in candidates] + [incumbent_value], dtype=np.float64)
    sds = np.clip(
        np.array([c.epistemic_sd for c in candidates] + [incumbent_sd], dtype=np.float64),
        0.0,
        None,
    )
    rng = np.random.default_rng(seed)
    # One vectorised posterior draw for every arm (candidates + incumbent as the last column).
    samples = means + sds * rng.standard_normal((n_draws, means.size))
    winners = samples.argmax(axis=1)
    n = len(candidates)
    counts = np.bincount(winners, minlength=means.size)[:n]
    pick_prob = counts / float(n_draws)

    incumbent_col = samples[:, n]
    beats = (samples[:, :n] > incumbent_col[:, None]).mean(axis=0)

    # Exploit vs flyer: an arm whose Thompson rank is better than its expected-value (mean) rank
    # is being lifted by its posterior width — a flyer; otherwise it is carried by expected value.
    order_mean = sorted(range(n), key=lambda i: (candidates[i].mean, -i), reverse=True)
    order_ts = sorted(range(n), key=lambda i: (pick_prob[i], candidates[i].mean, -i), reverse=True)
    mean_rank = {i: r for r, i in enumerate(order_mean)}
    ts_rank = {i: r for r, i in enumerate(order_ts)}

    recs: list[WaiverRec] = []
    for i, c in enumerate(candidates):
        flyer = ts_rank[i] < mean_rank[i] and c.epistemic_sd > 0.0
        kind = "flyer" if flyer else "exploit"
        pp = float(pick_prob[i])
        if kind == "flyer":
            reason = (
                f"ROS {c.mean:.1f} ±{c.epistemic_sd:.1f}; wide posterior lifts it to "
                f"{pp:.0%} of Thompson claims (mean-rank {mean_rank[i] + 1} → "
                f"claim-rank {ts_rank[i] + 1}) — upside flyer."
            )
        else:
            reason = (
                f"ROS {c.mean:.1f} ±{c.epistemic_sd:.1f}; Thompson claims {pp:.0%} of draws "
                f"on expected value — exploit."
            )
        recs.append(
            WaiverRec(
                id=c.id,
                position=c.position,
                mean=c.mean,
                epistemic_sd=c.epistemic_sd,
                pick_prob=pp,
                beats_incumbent=bool(beats[i] > 0.5),
                kind=kind,
                reason=reason,
            )
        )

    recs.sort(key=lambda r: (r.pick_prob, r.mean, r.id), reverse=True)
    return WaiverBoard(
        ranked=tuple(recs),
        incumbent_value=float(incumbent_value),
        n_draws=n_draws,
        seed=seed,
    )
