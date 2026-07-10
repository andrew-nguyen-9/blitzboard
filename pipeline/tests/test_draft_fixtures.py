"""
E1 golden fixtures — value/tuning + the two new projection factors.

Complements the frontend pick-logic fixtures (`frontend/lib/draftAI.fixtures.test.ts`,
categories 1–7). Here we prove the PIPELINE half of the E1 spec:

  * K/DEF cap (tuned value_engine): every real offensive starter (32 QB + ~64
    RB/WR/TE in a 12-team superflex) out-ranks the best K/DST — spec objective.
  * Tier cliffs (spec cat 6): the shaped value rewards separation over the next tier.
  * Injury factor (spec cat 5): a designation shaves availability-adjusted value, so
    an injured player prices below a healthy comparable through the value engine;
    absent/keyless data degrades to a true identity (zero regression).
  * Team-vs-team / schedule (spec cat 8, "feeds Monte Carlo"): a soft weekly matchup
    lifts a skill projection and a stout one shaves it, bounded; a season-long draft
    context (no opponent) and a data-less context are identities.

Plain pytest, no DB/network:  python -m pytest tests/test_draft_fixtures.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import LeagueRules, VorpEngine  # noqa: E402
from models.projector import Projection, apply_factors  # noqa: E402
from models.factors import FactorContext  # noqa: E402
from models.factors.injury import InjuryFactor  # noqa: E402
from models.factors.team_vs_team import TeamVsTeamFactor  # noqa: E402

SCORING = {"passing": {"pt_per_yd": 0.04, "td": 4, "int": -2},
           "rushing": {"pt_per_yd": 0.1, "td": 6},
           "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6}}
ROSTER = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1, "DST": 1, "K": 1, "_superflex": True}
RULES = LeagueRules(league_id="t", league_size=12, scoring=SCORING, roster_slots=ROSTER)


def _proj(pid, mean, rho=1.0, stdev_frac=0.35, season=2025, week=None):
    stdev = mean * stdev_frac
    return Projection(player_id=pid, season=season, source="ensemble", mean=mean, stdev=stdev,
                      floor=mean - 1.28 * stdev, ceiling=mean + 1.28 * stdev,
                      predictability=rho, week=week)


def _ctx(position="WR", *, injury=None, opponent=None, week=None, metadata=None):
    return FactorContext(player_id="p1", position=position, nfl_team="KC", season=2025,
                         injury_status=injury, opponent=opponent, week=week,
                         metadata=metadata or {})


# ── K/DEF cap: real starters out-rank K/DEF (tuned value_engine, defaults) ──────

def _realistic_board():
    """A full superflex board: deep, high-ρ offense + shallow, low-ρ K/DST."""
    proj, pos = {}, {}
    for p, count, top, bot in (("QB", 40, 380, 150), ("RB", 60, 300, 40),
                               ("WR", 60, 290, 30), ("TE", 30, 210, 50)):
        for i in range(count):
            pid = f"{p}{i}"
            proj[pid] = _proj(pid, top - (top - bot) * i / (count - 1), rho=0.8)
            pos[pid] = p
    for p, base, sf in (("K", 165, 0.22), ("DST", 150, 0.38)):
        for i in range(30):
            pid = f"{p}{i}"
            proj[pid] = _proj(pid, base - i * 1.6, rho=0.22, stdev_frac=sf)
            pos[pid] = p
    return proj, pos


def test_real_starters_outrank_kdef():
    """32 QB + ~64 RB/WR/TE startable offensive players all out-rank the best K/DST."""
    proj, pos = _realistic_board()
    res = {v.player_id: v for v in VorpEngine().compute(proj, pos, RULES)}
    best_kdef_rank = min(res[p].rank for p in res if pos[p] in ("K", "DST"))
    # 32 superflex QB slots + 64 RB/WR/TE starters = 96 real starters must all be ahead
    assert best_kdef_rank > 96, f"a K/DST cracked the top 96 at rank {best_kdef_rank}"
    print(f"✓ best K/DST overall rank = {best_kdef_rank} (behind all 96 real starters)")


def test_best_kdef_value_below_worst_real_starter():
    """The 96th-best offensive player still out-VALUES the single best K/DST."""
    proj, pos = _realistic_board()
    res = {v.player_id: v for v in VorpEngine().compute(proj, pos, RULES)}
    off = sorted((res[p] for p in res if pos[p] in ("QB", "RB", "WR", "TE")),
                 key=lambda v: v.value, reverse=True)
    best_kdef = max((res[p] for p in res if pos[p] in ("K", "DST")), key=lambda v: v.value)
    assert off[95].value > best_kdef.value, (off[95].value, best_kdef.value)
    print(f"✓ 96th offensive value {off[95].value:.1f} > best K/DST {best_kdef.value:.1f}")


def test_tuned_discount_widens_kdef_gap_vs_pretune():
    """The v4/E1 tune (k=1.2) suppresses K/DEF value harder than the pre-tune k=1.0."""
    proj, pos = _realistic_board()
    tuned = {v.player_id: v for v in VorpEngine(discount_k=1.2).compute(proj, pos, RULES)}
    pre = {v.player_id: v for v in VorpEngine(discount_k=1.0).compute(proj, pos, RULES)}
    best_k = max((p for p in proj if pos[p] == "K"), key=lambda p: tuned[p].value)
    assert tuned[best_k].value <= pre[best_k].value, (tuned[best_k].value, pre[best_k].value)
    print(f"✓ tuned K value {tuned[best_k].value:.1f} ≤ pre-tune {pre[best_k].value:.1f}")


# ── Tier cliffs (spec cat 6) ────────────────────────────────────────────────────

def test_tier_cliff_rewards_separation():
    """A big gap below a player (a real tier cliff) lifts its shaped value over a
    same-rank peer that sits atop a smooth, gap-less position."""
    proj, pos = {}, {}
    # RB with a cliff: RB2 is elite, then a sharp drop-off below it
    proj["cliff"] = _proj("cliff", 250, rho=0.8)
    for i, m in enumerate([248, 150, 148, 146, 144, 142]):   # steep drop after the top
        proj[f"rbfill{i}"] = _proj(f"rbfill{i}", m, rho=0.8); pos[f"rbfill{i}"] = "RB"
    pos["cliff"] = "RB"
    # WR with no cliff: a smooth ladder at the same top value
    for i, m in enumerate([250, 248, 246, 244, 242, 240, 238]):
        proj[f"wr{i}"] = _proj(f"wr{i}", m, rho=0.8); pos[f"wr{i}"] = "WR"
    res = {v.player_id: v for v in VorpEngine().compute(proj, pos, RULES)}
    assert res["cliff"].value > res["wr1"].value, (res["cliff"].value, res["wr1"].value)
    print(f"✓ tier-cliff RB value {res['cliff'].value:.1f} > smooth WR {res['wr1'].value:.1f}")


# ── Injury factor (spec cat 5) ──────────────────────────────────────────────────

def test_injury_healthy_and_absent_are_identity():
    f = InjuryFactor()
    for tag in (None, "", "Active", "ACT", "Healthy", "Probable"):
        assert f.value_for(_ctx(injury=tag)) == 1.0, tag
    print("✓ injury factor: healthy/absent designations are a true identity (degrade-safe)")


def test_injury_designations_are_graded():
    f = InjuryFactor()
    q = f.value_for(_ctx(injury="Questionable"))
    d = f.value_for(_ctx(injury="Doubtful"))
    out = f.value_for(_ctx(injury="Out"))
    ir = f.value_for(_ctx(injury="IR"))
    assert 1.0 > q > d > out > ir, (q, d, out, ir)
    print(f"✓ injury grading: Q {q} > D {d} > Out {out} > IR {ir}")


def test_injury_unknown_tag_is_conservative():
    """A present-but-unrecognised designation shaves only a little (never boosts)."""
    v = InjuryFactor().value_for(_ctx(injury="tweaked-hamstring-tbd"))
    assert 0.9 < v < 1.0, v
    print(f"✓ unknown injury tag → conservative {v}")


def test_injured_prices_below_healthy_through_value_engine():
    """Two identical WRs; the questionable one's availability-adjusted projection
    lands BELOW the healthy comparable after the value engine — spec cat 5."""
    healthy = _proj("healthy", 220, rho=0.8)
    injured = apply_factors(_proj("injured", 220, rho=0.8), _ctx("WR", injury="Doubtful"), [InjuryFactor()])
    proj = {"healthy": healthy, "injured": injured}
    pos = {"healthy": "WR", "injured": "WR"}
    # filler so replacement is defined
    for i in range(6):
        proj[f"wr{i}"] = _proj(f"wr{i}", 120 - i, rho=0.8); pos[f"wr{i}"] = "WR"
    res = {v.player_id: v for v in VorpEngine().compute(proj, pos, RULES)}
    assert res["injured"].value < res["healthy"].value, (res["injured"].value, res["healthy"].value)
    assert res["injured"].rank > res["healthy"].rank
    print(f"✓ injured value {res['injured'].value:.1f} < healthy {res['healthy'].value:.1f}")


def test_injury_feeds_monte_carlo_mean():
    """apply_factors reshapes the mean the MonteCarloEngine samples — the factor
    reaches the MC path, not just VORP (spec: feeds Monte Carlo)."""
    base = _proj("p", 200, rho=0.8)
    out = apply_factors(base, _ctx("RB", injury="IR"), [InjuryFactor()])
    assert out.mean < base.mean and abs(out.mean - base.mean * 0.55) < 0.5
    # shape preserved: floor/ceiling scaled by the same multiplier
    assert abs(out.ceiling / base.ceiling - out.mean / base.mean) < 1e-6
    print(f"✓ injury reshapes the sampled mean 200→{out.mean} (MC-visible), shape preserved")


# ── Team-vs-team / schedule (spec cat 8) ────────────────────────────────────────

def test_team_vs_team_season_long_is_identity():
    """A draft (season-long) context has no opponent → identity, so the factor never
    perturbs the offline draft board."""
    f = TeamVsTeamFactor()
    assert f.value_for(_ctx("WR", opponent=None, week=None)) == 1.0
    assert f.value_for(_ctx("WR", metadata={"opp_def_rank": 30})) == 1.0  # no opponent/week
    print("✓ team-vs-team is identity for the season-long draft context")


def test_team_vs_team_soft_matchup_boosts():
    f = TeamVsTeamFactor()
    soft = f.value_for(_ctx("WR", opponent="NYG", week=5, metadata={"opp_def_rank": 32}))
    tough = f.value_for(_ctx("WR", opponent="SF", week=5, metadata={"opp_def_rank": 1}))
    assert soft > 1.0 > tough, (soft, tough)
    assert abs(soft - 1.08) < 1e-6 and abs(tough - 0.92) < 1e-6  # bounded ±8%
    print(f"✓ matchup swing bounded: softest ×{soft:.3f}, toughest ×{tough:.3f}")


def test_team_vs_team_direct_softness_and_degrade():
    f = TeamVsTeamFactor()
    direct = f.value_for(_ctx("RB", opponent="LV", week=3, metadata={"opp_def_vs_pos": 0.75}))
    assert direct > 1.0
    # no rating available → identity even with an opponent+week
    assert f.value_for(_ctx("RB", opponent="LV", week=3, metadata={})) == 1.0
    # gated off non-skill positions
    assert f.value_for(_ctx("K", opponent="LV", week=3, metadata={"opp_def_rank": 32})) == 1.0
    print("✓ team-vs-team: direct softness applies; no data / non-skill → identity")


def test_team_vs_team_feeds_value_engine():
    """A soft weekly matchup lifts a projection so it out-values its neutral twin
    through the value engine (the matchup reaches MC/VORP, spec cat 8)."""
    neutral = _proj("neutral", 180, rho=0.8, week=5)
    boosted = apply_factors(_proj("boosted", 180, rho=0.8, week=5),
                            _ctx("WR", opponent="NYG", week=5, metadata={"opp_def_rank": 32}),
                            [TeamVsTeamFactor()])
    proj = {"neutral": neutral, "boosted": boosted}
    pos = {"neutral": "WR", "boosted": "WR"}
    for i in range(6):
        proj[f"wr{i}"] = _proj(f"wr{i}", 100 - i, rho=0.8, week=5); pos[f"wr{i}"] = "WR"
    res = {v.player_id: v for v in VorpEngine().compute(proj, pos, RULES)}
    assert res["boosted"].value > res["neutral"].value
    print(f"✓ soft-matchup value {res['boosted'].value:.1f} > neutral {res['neutral'].value:.1f}")


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL E1 DRAFT-FIXTURE TESTS PASSED ✅")


if __name__ == "__main__":
    main()
