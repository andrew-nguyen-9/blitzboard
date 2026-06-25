"""
ValueEngine — projections × LeagueRules → player value (ARCH §3 / D5).

Two implementations behind one interface; the UI toggles which cached set it reads:
  • VorpEngine        — deterministic value-over-replacement (shipped skeleton here)
  • MonteCarloEngine  — simulates N drafts/seasons (P7)

Both are batch-precomputed in the pipeline and written to `player_value` keyed by
(engine, scoring_profile). Draft/Trade/Waiver tools are thin consumers — they never
compute value themselves.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .league_rules import LeagueRules, BASE_POSITIONS
from .projector import Projection

# ── Value-shaping constants (#4: non-linear positional weighting + future value) ─
ELITE_PREMIUM = 0.65    # top-of-position convex bonus (elite RB ≫ mid RB)
ELITE_SCALE = 7.0       # how fast the premium decays down the position ranks
CLIFF_W = 0.45          # "tier cliff" bonus = separation over the next tier below
CLIFF_LOOKAHEAD = 4     # compare to the player N spots lower at the position
UPSIDE_W = 0.33         # reward ceiling over mean (boom = trade/league-winner equity)
YOUTH_W = 0.18          # future value: ascending youth up, aging down
CONSENSUS_W = 18.0      # consensus (Sleeper search_rank) nudge for the deep/bench pool
# rough positional peak ages (value-trajectory, not just this season)
PEAK_AGE = {"RB": 24, "WR": 26, "TE": 26, "QB": 29, "K": 30, "DST": 99}

# ── Predictability discount + streamer replacement (#3: K/DEF overvalued) ─────
DISCOUNT_K = 1.0                       # f(ρ)=ρ^k exponent; tuned by backtest (v2.4.3)
STREAMER_PCT = 0.60                    # K/DEF replacement = this points-percentile (upper-middle)
STREAMER_POSITIONS = ("K", "DST")     # positions everyone streams off waivers
MC_VOL_GAIN = 0.6                      # how much low ρ widens Monte Carlo σ (v2.2.3.1)


def f_predictability(rho: float | None, k: float) -> float:
    """The VORP discount f(ρ)=ρ^k. A missing ρ means no discount (1.0); a perfectly
    predictable player keeps all of its value, a volatile one is compressed toward
    replacement. Monotone-increasing in ρ, bounded in [0,1] for ρ∈[0,1], k≥0."""
    if rho is None:
        return 1.0
    rho = 0.0 if rho < 0 else 1.0 if rho > 1 else rho
    return rho ** k


def _replacement_index(pos: str, n: int, repl_rank: int, streamer_pct: float) -> int:
    """0-based, best-first index of a position's replacement player — shared by both
    engines so they price replacement identically. K/DEF use the upper-middle weekly-
    streamer percentile (everyone streams off waivers, SCORING.md §2); every other
    position uses league slot demand (superflex-aware). Clamped to [0, n-1]."""
    if n <= 0:
        return 0
    idx = round((1 - streamer_pct) * (n - 1)) if pos in STREAMER_POSITIONS else repl_rank - 1
    return max(0, min(idx, n - 1))


def _youth_factor(pos: str, age: int | None) -> float:
    if age is None:
        return 1.0
    peak = PEAK_AGE.get(pos, 27)
    # young (below peak) gets up to +, old gets down; clamped and gentle
    delta = (peak - age) / 8.0
    return 1.0 + YOUTH_W * max(-0.8, min(1.0, delta))


@dataclass
class PlayerValue:
    player_id: str
    engine: str                # 'vorp' | 'monte_carlo'
    value: float               # shaped DRAFT value (non-linear, future-aware) — ranks the board
    vor: float                 # raw value-over-replacement (linear, interpretable; used for lineup sums)
    replacement: float
    rank: int
    boom: float | None = None
    bust: float | None = None
    adp: float | None = None
    tier: int | None = None


class ValueEngine(ABC):
    name: str = "abstract"

    @abstractmethod
    def compute(
        self, projections: dict[str, Projection], positions: dict[str, str], rules: LeagueRules,
        meta: dict | None = None,
    ) -> list[PlayerValue]:
        """projections: player_id→Projection; positions: player_id→pos;
        meta: player_id→{age, years_exp, adp} (optional, drives future-value)."""
        ...


class VorpEngine(ValueEngine):
    """Value Over Replacement Player.

    Replacement baseline per position = the league-wide starter demand from
    LeagueRules.replacement_ranks() — which is SUPERFLEX-AWARE (D9): for Smores,
    QB replacement is set deep (~OP-inflated) so elite QBs price correctly.
    """

    name = "vorp"

    def __init__(self, discount_k: float = DISCOUNT_K, streamer_pct: float = STREAMER_PCT):
        self.discount_k = discount_k
        self.streamer_pct = streamer_pct

    def compute(self, projections, positions, rules, meta=None):
        meta = meta or {}
        repl_rank = rules.replacement_ranks()

        # group projected means by position, descending (with mean kept for cliffs)
        by_pos: dict[str, list[tuple[str, float]]] = {p: [] for p in BASE_POSITIONS}
        for pid, proj in projections.items():
            pos = positions.get(pid)
            if pos in by_pos:
                by_pos[pos].append((pid, proj.mean))
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: x[1], reverse=True)

        # replacement value = the Nth-ranked player's projection at that position
        replacement: dict[str, float] = {}
        pos_rank: dict[str, int] = {}        # player_id → 1-based rank within position
        pos_means: dict[str, list[float]] = {}
        for pos, ranked in by_pos.items():
            means_desc = [m for _, m in ranked]
            idx = _replacement_index(pos, len(means_desc), repl_rank.get(pos, 1), self.streamer_pct)
            replacement[pos] = means_desc[idx] if means_desc else 0.0
            pos_means[pos] = means_desc
            for i, (pid, _) in enumerate(ranked, 1):
                pos_rank[pid] = i

        out: list[PlayerValue] = []
        for pid, proj in projections.items():
            pos = positions.get(pid)
            if pos not in by_pos:
                continue
            repl = replacement.get(pos, 0.0)
            vor = proj.mean - repl                      # raw, linear, interpretable
            rk = pos_rank.get(pid, 999)
            m = meta.get(pid, {})

            # 1) convex ELITE premium — the top of a position towers over the middle
            elite = 1.0 + ELITE_PREMIUM * math.exp(-(rk - 1) / ELITE_SCALE)
            # 2) tier CLIFF bonus — separation over the player N spots below (scarcity of THIS tier)
            means = pos_means.get(pos, [])
            below = means[rk - 1 + CLIFF_LOOKAHEAD] if rk - 1 + CLIFF_LOOKAHEAD < len(means) else (means[-1] if means else proj.mean)
            cliff = max(0.0, proj.mean - below) * CLIFF_W
            # 3) UPSIDE — ceiling over mean = future trade equity / league-winner odds
            upside = max(0.0, proj.ceiling - proj.mean) * UPSIDE_W
            # 4) future-value YOUTH factor
            youth = _youth_factor(pos, m.get("age"))
            # 5) predictability discount f(ρ)=ρ^k — compresses unreproducible value
            #    (volatile K/DEF) toward replacement without special-casing position.
            disc = f_predictability(proj.predictability, self.discount_k)

            if vor > 0:
                shaped = (vor * elite + cliff + upside) * disc * youth
            else:
                # deep/bench pool: real projections are thin & nearly tied here, so
                # order by Sleeper's consensus rank (search_rank) + a little upside.
                sr = m.get("search_rank")
                consensus = CONSENSUS_W * (1 - min(sr, 800) / 800) if (sr and sr < 999) else 0.0
                shaped = (vor + upside * 0.5) * youth + consensus

            out.append(PlayerValue(
                player_id=pid, engine=self.name, value=round(shaped, 2), vor=round(vor, 2),
                replacement=repl, rank=0,
                boom=round(proj.ceiling - repl, 2), bust=round(proj.floor - repl, 2),
                adp=m.get("adp"),
            ))
        # rank by SHAPED value (so elite/upside/youth reorder the board)
        out.sort(key=lambda v: v.value, reverse=True)
        # assign overall rank + per-position tiers (gaps in shaped value = tier breaks)
        by_pos_vals: dict[str, list[PlayerValue]] = {}
        for i, v in enumerate(out, 1):
            v.rank = i
            by_pos_vals.setdefault(positions.get(v.player_id, "?"), []).append(v)
        for pos, vs in by_pos_vals.items():
            _assign_tiers(vs)
        return out


def _assign_tiers(vs: list[PlayerValue]) -> None:
    """Tier players within a position by gaps in shaped value. A big drop = a real
    tier break (the 'cliff' a drafter feels). vs must be sorted desc by value."""
    if not vs:
        return
    vals = [v.value for v in vs]
    gaps = [vals[i - 1] - vals[i] for i in range(1, len(vals))]
    avg = (sum(gaps) / len(gaps)) if gaps else 0.0
    tier = 1
    vs[0].tier = 1
    for i in range(1, len(vs)):
        if (vals[i - 1] - vals[i]) > max(6.0, avg * 1.6):
            tier += 1
        vs[i].tier = tier


class MonteCarloEngine(ValueEngine):
    """Simulate N seasons from projection distributions → percentile-based value.

    Unlike VORP's deterministic mean−replacement, MC samples the full
    distribution N times so variance becomes an explicit input to value:
      value = E[VOR] + UPSIDE_W × (P90_VOR − E[VOR]) × youth_factor
    boom/bust = P90/P10 VOR across simulations (not projection bounds).

    v2.2.3: the sampled σ is widened by low predictability (`1 + MC_VOL_GAIN·(1−ρ)`)
    so volatile players get correctly wider boom/bust. Replacement levels (incl. the
    K/DEF streamer level) are shared with VORP via `_replacement_index`, so the two
    engines price the board coherently. `seed` makes a run reproducible.
    """

    name = "monte_carlo"

    def __init__(self, n_sims: int = 10_000, streamer_pct: float = STREAMER_PCT, seed: int | None = None):
        self.n_sims = n_sims
        self.streamer_pct = streamer_pct
        self.seed = seed

    def compute(self, projections, positions, rules, meta=None):
        try:
            import numpy as np
        except ImportError:
            raise RuntimeError("MonteCarloEngine requires numpy (`pip install numpy`)")

        meta = meta or {}
        repl_rank = rules.replacement_ranks()

        # Score every position the board ranks (K/DST included — their value comes
        # from the streamer replacement + predictability-widened distribution).
        eligible = {
            pid: proj for pid, proj in projections.items()
            if positions.get(pid) in BASE_POSITIONS
        }
        pids = list(eligible.keys())
        if not pids:
            return []

        means = np.array([eligible[p].mean for p in pids], dtype=float)
        stdevs = np.array([eligible[p].stdev for p in pids], dtype=float)
        pos_arr = np.array([positions.get(p, "?") for p in pids])

        # Predictability-aware σ: a low-ρ player is sampled WIDER, so its boom/bust
        # honestly reflects how unreproducible the projection is (SCORING.md §3.1).
        rhos = np.array([eligible[p].predictability if eligible[p].predictability is not None else 1.0
                         for p in pids], dtype=float)
        eff_stdevs = stdevs * (1.0 + MC_VOL_GAIN * (1.0 - rhos))
        # Re-derive clip bounds from the EFFECTIVE σ, else widening is clipped away.
        floors = means - 1.28 * eff_stdevs
        ceilings = means + 1.28 * eff_stdevs

        # Draw n_sims season totals per player; clip approximates truncated normal
        # (bounds at ±1.28σ_eff ≈ 80th-pct). `seed` makes the run reproducible.
        rng = np.random.default_rng(self.seed)
        samples = np.clip(
            rng.normal(means, eff_stdevs, (self.n_sims, len(pids))),
            floors, ceilings,
        )  # shape: (n_sims, n_players)

        # Per-simulation replacement level per position
        repl_sim = np.zeros_like(samples)
        repl_scalar: dict[str, float] = {}
        sim_pos = [pos for pos in BASE_POSITIONS if pos in pos_arr]
        for pos in sim_pos:
            mask = pos_arr == pos
            pos_samp = samples[:, mask]                        # (n_sims, n_pos)
            sorted_desc = np.sort(pos_samp, axis=1)[:, ::-1]  # best-first per sim
            # same replacement index as VORP (incl. K/DEF streamer level)
            idx = _replacement_index(pos, sorted_desc.shape[1], repl_rank.get(pos, 1), self.streamer_pct)
            repl_sim[:, mask] = sorted_desc[:, idx : idx + 1]
            # scalar replacement (from means) for the PlayerValue.replacement field
            pos_means = sorted(means[mask].tolist(), reverse=True)
            repl_scalar[pos] = pos_means[idx] if pos_means else 0.0

        vor_sim = samples - repl_sim   # (n_sims, n_players)

        mean_vor = vor_sim.mean(axis=0)
        p10_vor = np.percentile(vor_sim, 10, axis=0)
        p90_vor = np.percentile(vor_sim, 90, axis=0)
        # Asymmetric upside: only the part of P90 above the mean is rewarded
        upside_spread = np.maximum(0.0, p90_vor - mean_vor)

        out: list[PlayerValue] = []
        for i, pid in enumerate(pids):
            pos = positions.get(pid)
            if pos not in BASE_POSITIONS:
                continue
            m = meta.get(pid, {})
            youth = _youth_factor(pos, m.get("age"))
            mc_val = (float(mean_vor[i]) + UPSIDE_W * float(upside_spread[i])) * youth
            out.append(PlayerValue(
                player_id=pid,
                engine=self.name,
                value=round(mc_val, 2),
                vor=round(float(mean_vor[i]), 2),
                replacement=round(repl_scalar.get(pos, 0.0), 2),
                rank=0,
                boom=round(float(p90_vor[i]), 2),
                bust=round(float(p10_vor[i]), 2),
                adp=m.get("adp"),
            ))

        out.sort(key=lambda v: v.value, reverse=True)
        for i, v in enumerate(out, 1):
            v.rank = i
        by_pos_vals: dict[str, list[PlayerValue]] = {}
        for v in out:
            by_pos_vals.setdefault(positions.get(v.player_id, "?"), []).append(v)
        for vs in by_pos_vals.values():
            _assign_tiers(vs)
        return out
