"""The four latent structures E1-latents fits, each a frozen record + a resolve method.

All four are learned as *shrunk residuals on the log-efficiency scale* (yards-per-opportunity)
so their contribution is additive exactly where the core consumes it (`lat_eff`, added to
``log_ypo``; `lat_opp`, added to ``appeal``). rel=DEGRADE — every lookup misses to 0, so an
unmodelled team/matchup/pairing is projected by the plain hierarchy.

    DefenseLatent    per (opponent, position), opponent-adjusted → efficiency + a *within-team
                     position-differential* opportunity shift (a tough run-D moves share off
                     the RB toward the pass-catchers). Team-constant part is intentionally
                     dropped: it CANCELS in the Dirichlet share renormalisation and is a no-op.
    OLineLatent      per team, from RB rush efficiency + QB dropback efficiency → RB rush
                     efficiency (full weight) and the pass floor (a fraction, to QB/WR/TE).
    EcosystemLatent  per team, whole-offense efficiency residual → a rising-tide ypo lift.
    ChemistryLatent  per (QB, receiver) pairing, regularised HARD and ABLATION-GATED — the
                     receiver's ypo lift *beyond his solo baseline* when caught by his QB;
                     dropped wholesale unless the pairing signal beats a permutation test.

`ponytail:` the identifiable structure is dictated by the Dirichlet share (opportunity latents
must vary *within* a team or they vanish) and by thin data (shrinkage + a hard clip, no fit).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from blitz_engine.projection.latents.shrinkage import (
    grouped_shrunk_effect,
    opponent_adjust,
)

__all__ = [
    "ChemistryLatent",
    "DefenseLatent",
    "EcosystemLatent",
    "OLineLatent",
    "ResolveContext",
]

_RECEIVERS = ("WR", "TE")
_EPS = 1e-3

# shrinkage strengths (k = prior/noise ratio; larger ⇒ harder) + hard clips (log scale)
_DEF_OFF_K, _DEF_K, _DEF_BOUND = 4.0, 6.0, 0.30
_DEF_OPP_SCALE = 0.5  # matchup moves efficiency fully, share half as hard
_OLINE_K, _OLINE_BOUND = 8.0, 0.25
_OLINE_PASS_FRAC = 0.4  # pass floor gets a fraction of the run-block signal
_ECO_K, _ECO_BOUND = 10.0, 0.20
_CHEM_K, _CHEM_BOUND = 20.0, 0.15  # HARD regularised — thin pairing data


@dataclass(frozen=True)
class ResolveContext:
    """The current-roster facts a latent needs to place its learned effects on players."""

    player_ids: list[str]
    positions: list[str]
    teams: list[str]
    matchups: dict[str, str] = field(default_factory=dict)  # team → opponent team
    qb_of_team: dict[str, str] = field(default_factory=dict)  # team → primary passer id

    @property
    def n(self) -> int:
        return len(self.player_ids)


def _log_ypo(yards: np.ndarray, opp: np.ndarray) -> np.ndarray:
    """Per-row log yards-per-opportunity (the shared efficiency signal)."""
    return np.log((np.asarray(yards, float) + _EPS) / (np.asarray(opp, float) + _EPS))


@dataclass(frozen=True)
class DefenseLatent:
    """Opponent-adjusted defensive strength per (team, position); >0 ⇒ generous defense."""

    strength: dict[tuple[str, str], float]

    @classmethod
    def fit(
        cls, team: np.ndarray, opp: np.ndarray | None, pos: np.ndarray, log_ypo: np.ndarray
    ) -> DefenseLatent:
        if opp is None:
            return cls(strength={})
        resid = opponent_adjust(log_ypo, list(team), k=_DEF_OFF_K)
        keys = list(zip([str(o) for o in opp], [str(p) for p in pos], strict=True))
        return cls(strength=grouped_shrunk_effect(keys, resid, k=_DEF_K, bound=_DEF_BOUND))

    def contribution(self, ctx: ResolveContext) -> tuple[np.ndarray, np.ndarray]:
        eff = np.zeros(ctx.n)
        for i, (team, pos) in enumerate(zip(ctx.teams, ctx.positions, strict=True)):
            opp = ctx.matchups.get(team)
            if opp is not None:
                eff[i] = self.strength.get((opp, pos), 0.0)
        # opportunity = the WITHIN-TEAM-DIFFERENTIAL part only (team mean cancels in the share)
        opp_raw = np.zeros(ctx.n)
        teams = np.asarray(ctx.teams)
        for t in np.unique(teams):
            m = teams == t
            opp_raw[m] = _DEF_OPP_SCALE * (eff[m] - eff[m].mean())
        return opp_raw, eff


@dataclass(frozen=True)
class OLineLatent:
    """Per-team offensive-line effect → RB rush efficiency + a partial pass floor."""

    strength: dict[str, float]

    @classmethod
    def fit(cls, team: np.ndarray, pos: np.ndarray, log_ypo: np.ndarray) -> OLineLatent:
        pos = np.asarray([str(p) for p in pos])
        block_mask = pos == "RB"  # RB rush efficiency is the cleanest identifiable O-line signal
        if not block_mask.any():
            return cls(strength={})
        team = np.asarray([str(t) for t in team])
        resid = log_ypo[block_mask] - float(np.nanmean(log_ypo[block_mask]))
        keys = [str(t) for t in team[block_mask]]
        return cls(strength=grouped_shrunk_effect(keys, resid, k=_OLINE_K, bound=_OLINE_BOUND))

    def contribution(self, ctx: ResolveContext) -> tuple[np.ndarray, np.ndarray]:
        eff = np.zeros(ctx.n)
        for i, (team, pos) in enumerate(zip(ctx.teams, ctx.positions, strict=True)):
            s = self.strength.get(team, 0.0)
            eff[i] = s if pos == "RB" else _OLINE_PASS_FRAC * s
        return np.zeros(ctx.n), eff  # team-level ⇒ opportunity share is a no-op


@dataclass(frozen=True)
class EcosystemLatent:
    """Per-team whole-offense efficiency residual — the rising-tide ecosystem lift."""

    strength: dict[str, float]

    @classmethod
    def fit(cls, team: np.ndarray, log_ypo: np.ndarray) -> EcosystemLatent:
        resid = log_ypo - float(np.nanmean(log_ypo))
        keys = [str(t) for t in team]
        return cls(strength=grouped_shrunk_effect(keys, resid, k=_ECO_K, bound=_ECO_BOUND))

    def contribution(self, ctx: ResolveContext) -> tuple[np.ndarray, np.ndarray]:
        eff = np.array([self.strength.get(t, 0.0) for t in ctx.teams])
        return np.zeros(ctx.n), eff


@dataclass(frozen=True)
class ChemistryLatent:
    """QB–receiver pairing lift, HARD-regularised and ABLATION-GATED (drops if not significant)."""

    pair: dict[tuple[str, str], float]
    significant: bool

    @classmethod
    def fit(
        cls,
        passer: np.ndarray | None,
        receiver: np.ndarray,
        pos: np.ndarray,
        log_ypo: np.ndarray,
        *,
        alpha: float = 0.05,
    ) -> ChemistryLatent:
        if passer is None:
            return cls(pair={}, significant=False)
        pos = np.asarray([str(p) for p in pos])
        rcv = np.asarray([str(r) for r in receiver])
        psr = np.asarray([str(p) for p in passer])
        mask = np.isin(pos, _RECEIVERS) & (psr != "nan") & (psr != "None") & (psr != "")
        if mask.sum() < 4:
            return cls(pair={}, significant=False)
        # residual = receiver ypo minus the receiver's OWN (lightly-shrunk) mean, so what is
        # left is WITHIN-receiver variation — the only place a QB pairing can be identified
        # apart from the receiver's own skill. A receiver caught by one QB has ~0 residual
        # spread ⇒ no chemistry claim; a receiver split across QBs reveals the pairing.
        ypo = log_ypo[mask]
        rcv_m = [str(r) for r in rcv[mask]]
        psr_m = [str(p) for p in psr[mask]]
        pos_mean = float(np.nanmean(ypo))
        dev = grouped_shrunk_effect(rcv_m, ypo - pos_mean, k=4.0, bound=np.inf)
        baseline = pos_mean + np.array([dev.get(r, 0.0) for r in rcv_m])
        resid = ypo - baseline
        pair_keys = list(zip(psr_m, rcv_m, strict=True))
        pair = grouped_shrunk_effect(pair_keys, resid, k=_CHEM_K, bound=_CHEM_BOUND)
        # ABLATION GATE: a one-way permutation (ANOVA) test on the pairing DESIGN. The
        # pairing grouping is fixed; the residuals are shuffled. If which QB caught the ball
        # genuinely separates a receiver's efficiency, the true arrangement concentrates
        # residuals in repeated pairs far more than a shuffle — else the pairing is noise and
        # the whole latent is dropped. (Correlating a residual-derived signal against those
        # same residuals would be circular; permuting the outcome against a fixed design is not.)
        sig = _pairing_significant(pair_keys, resid, alpha)
        return cls(pair=pair if sig else {}, significant=sig)

    def contribution(self, ctx: ResolveContext) -> tuple[np.ndarray, np.ndarray]:
        eff = np.zeros(ctx.n)
        if not self.significant:
            return np.zeros(ctx.n), eff  # dropped by the ablation gate
        for i, (team, pos, pid) in enumerate(
            zip(ctx.teams, ctx.positions, ctx.player_ids, strict=True)
        ):
            qb = ctx.qb_of_team.get(team)
            if qb is not None and pos in _RECEIVERS:
                eff[i] = self.pair.get((qb, pid), 0.0)
        return np.zeros(ctx.n), eff


def _pairing_significant(
    pair_keys: list[tuple[str, str]],
    resid: np.ndarray,
    alpha: float,
    *,
    n_perm: int = 1000,
    seed: int = 0,
) -> bool:
    """Permutation ANOVA: does the (QB, receiver) pairing separate residuals beyond chance?

    Statistic = the between-repeated-pair sum of squares (Σ over pairs with ≥2 rows of
    ``sum²/n``) with the pairing design held FIXED; the null shuffles the residuals across
    rows. Degrades to False (⇒ chemistry dropped) whenever there is nothing repeatable to
    test. Deterministic under `seed`.
    """
    resid = np.asarray(resid, dtype=np.float64).ravel()
    codes, counts = _factorize([f"{p}|{r}" for p, r in pair_keys])
    qualify = counts >= 2
    if not qualify.any() or int(counts[qualify].sum()) < 4:
        return False

    def between_ss(vals: np.ndarray) -> float:
        gsum = np.zeros(counts.size)
        np.add.at(gsum, codes, vals)
        ss = np.where(counts > 0, gsum * gsum / np.where(counts > 0, counts, 1), 0.0)
        return float(ss[qualify].sum())

    observed = between_ss(resid)
    rng = np.random.default_rng(seed)
    perm = resid.copy()
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(perm)
        if between_ss(perm) >= observed:
            hits += 1
    return (hits + 1) / (n_perm + 1) <= alpha


def _factorize(keys: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Integer-code the keys and return (per-row code, per-code count) — no pandas needed."""
    index: dict[str, int] = {}
    codes = np.empty(len(keys), dtype=np.int64)
    for i, key in enumerate(keys):
        codes[i] = index.setdefault(key, len(index))
    counts = np.bincount(codes, minlength=len(index)).astype(np.int64)
    return codes, counts
