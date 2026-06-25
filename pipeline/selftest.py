"""
Offline end-to-end self-test for the modeling chain — NO DB, NO network.

Builds a synthetic multi-season HistoryStore, runs the projectors + ensemble +
VORP engine, and asserts the pipeline produces sane, superflex-aware output.

Run:  python selftest.py
"""
from __future__ import annotations

import random

from models import (
    LeagueRules, HistoryStore, HeuristicProjector, RegressionProjector,
    EnsembleProjector, KickerProjector, DefenseProjector, VorpEngine,
    Predictability,
    score_stats, score_kicking, score_defense,
    VaderScorer, PlayerMatcher,
)

# Smores 2025 rules (subset needed for offense scoring + superflex roster).
SCORING = {
    "passing": {"pt_per_yd": 0.04, "td": 4, "int": -2, "two_pt": 2},
    "rushing": {"pt_per_yd": 0.1, "td": 6, "two_pt": 2},
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6, "two_pt": 2},
    "misc": {"fumble_lost": -2},
}
SCORING["kicking"] = {"pat": 1, "pat_miss": -2, "fg_miss": -1,
                      "fg_0_39": 3, "fg_40_49": 4, "fg_50_59": 5, "fg_60_plus": 6}
SCORING["dst"] = {"sack": 1, "int": 2, "fumble_rec": 2, "safety": 2, "blocked_kick": 2,
                  "td_any": 6, "two_pt_return": 2, "one_pt_safety": 1,
                  "points_allowed": {"0": 5, "1_6": 4, "7_13": 3, "14_17": 1, "18_27": 0,
                                     "28_34": -1, "35_45": -3, "46_plus": -5},
                  "yards_allowed": {"lt_100": 5, "100_199": 3, "200_299": 2, "300_349": 0,
                                    "350_399": -1, "400_449": -3, "450_499": -5,
                                    "500_549": -6, "550_plus": -7}}
ROSTER = {
    "QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1, "DST": 1, "K": 1,
    "_superflex": True, "_op_eligible": ["QB", "RB", "WR", "TE"],
}
RULES = LeagueRules(league_id="test", league_size=12, scoring=SCORING, roster_slots=ROSTER)


def _line(pos: str, quality: float) -> dict:
    """Synthetic season stat line scaled by a 0..1 quality knob."""
    if pos == "QB":
        return {"games": 16, "passing_yards": 3200 + 1600 * quality,
                "passing_tds": 18 + 22 * quality, "interceptions": 14 - 6 * quality,
                "rushing_yards": 150 + 400 * quality, "rushing_tds": 1 + 5 * quality}
    if pos == "RB":
        return {"games": 16, "rushing_yards": 500 + 900 * quality,
                "rushing_tds": 3 + 9 * quality, "receptions": 20 + 50 * quality,
                "receiving_yards": 150 + 450 * quality, "receiving_tds": 1 + 3 * quality}
    if pos == "WR":
        return {"games": 16, "receptions": 40 + 70 * quality,
                "receiving_yards": 500 + 1000 * quality, "receiving_tds": 2 + 9 * quality}
    return {"games": 16, "receptions": 30 + 50 * quality,
            "receiving_yards": 350 + 650 * quality, "receiving_tds": 1 + 7 * quality}  # TE


def build_synth():
    random.seed(7)
    players, store = [], HistoryStore(RULES)
    counts = {"QB": 24, "RB": 40, "WR": 50, "TE": 20}
    for pos, n in counts.items():
        for i in range(n):
            pid = f"{pos}{i}"
            quality = max(0.0, min(1.0, 1 - i / n + random.uniform(-0.05, 0.05)))
            age = 23 + (i % 10)
            players.append({"id": pid, "full_name": f"{pos} Player {i}",
                            "position": pos, "age": age})
            # 3 seasons of history with slight noise
            for s in (2022, 2023, 2024):
                line = _line(pos, max(0.0, quality + random.uniform(-0.07, 0.07)))
                store.add(pid, s, line, games=line["games"], age=age - (2024 - s), position=pos)
    return players, store.finalize()


def main() -> None:
    # 1) scoring sanity (half-PPR)
    pts = score_stats({"receptions": 100, "receiving_yards": 1200, "receiving_tds": 10}, SCORING)
    assert abs(pts - (100 * 0.5 + 1200 * 0.1 + 10 * 6)) < 0.01, pts
    print(f"✓ scoring: 100/1200/10 WR line (half-PPR) = {pts}")

    # 2) superflex replacement levels
    assert RULES.is_superflex
    repl = RULES.replacement_ranks()
    print(f"✓ replacement ranks (superflex-aware): {repl}")
    assert repl["QB"] > 12, "QB replacement must exceed league size in superflex"

    # 3) full projection + value chain
    players, store = build_synth()
    ensemble = EnsembleProjector([
        (HeuristicProjector(store, RULES, 2025), 1.0),
        (RegressionProjector(store, RULES, 2025), 1.0),
    ])
    pred = Predictability(store, RULES)
    projections, positions = {}, {}
    for p in players:
        pr = ensemble.project(p)
        assert pr and pr.mean > 0 and pr.stdev > 0 and pr.ceiling > pr.floor
        pr.predictability = pred.score(pr.player_id, p["position"])
        assert 0.0 <= pr.predictability <= 1.0
        projections[p["id"]] = pr
        positions[p["id"]] = p["position"]
    print(f"✓ projected {len(projections)} players (mean+distribution+predictability)")

    # predictability flows through the chain and orders K/DST below skill positions
    assert pred.prior["K"] < pred.prior["QB"] and pred.prior["DST"] < pred.prior["RB"]
    rb_rho = sum(projections[p["id"]].predictability for p in players if positions[p["id"]] == "RB")
    rb_rho /= sum(1 for p in players if positions[p["id"]] == "RB")
    print(f"✓ predictability: K/DST priors below skill; mean RB ρ={rb_rho:.2f}")

    values = VorpEngine().compute(projections, positions, RULES)
    assert values[0].rank == 1 and values[0].value >= values[-1].value
    top_qbs = [v for v in values if positions[v.player_id] == "QB"][:5]
    print("✓ VORP top-5 QBs (superflex lifts these):")
    for v in top_qbs:
        print(f"    {v.player_id:<5} VOR {v.vor:+6.1f}  repl {v.replacement:6.1f}")
    # superflex sanity: an elite QB should out-value replacement comfortably
    assert top_qbs[0].vor > 0
    print(f"✓ overall #1: {values[0].player_id} ({positions[values[0].player_id]}) VOR {values[0].vor:+.1f}")

    # 4) K / D-ST scoring + projector treatment
    kpts = score_kicking({"fg_made_0_39": 20, "fg_made_40_49": 6, "fg_made_50_59": 3,
                          "pat_made": 35, "fg_missed": 2}, SCORING)
    assert abs(kpts - (20 * 3 + 6 * 4 + 3 * 5 + 35 * 1 + 2 * -1)) < 0.01, kpts
    print(f"✓ kicking (distance-based) season = {kpts}")
    dpts = score_defense({"sacks": 45, "interceptions": 15, "fumble_recoveries": 8,
                          "def_tds": 4, "points_allowed": 17, "yards_allowed": 280}, SCORING)
    assert dpts > 0
    print(f"✓ defense (events + PA-tier@17=1 + YA-tier@280=2) = {dpts}")

    k = KickerProjector(store, RULES, 2025)   # no network → mid-baseline, no crash
    d = DefenseProjector(store, RULES, 2025)
    kp = k.project({"id": "K1", "full_name": "Some Kicker", "position": "K"})
    dp = d.project({"id": "D1", "full_name": "Some Defense", "position": "DST"})
    assert kp and kp.mean > 0 and kp.stdev > 0
    assert dp and dp.mean > 0 and dp.stdev > dp.mean * 0.3  # D/ST widest σ
    print(f"✓ K projector mean={kp.mean} σ={kp.stdev} · DST mean={dp.mean} σ={dp.stdev}")

    # 5) sentiment scorer + player entity matching (P4)
    sc = VaderScorer()
    inj = sc.score("Bijan Robinson ruled out with a hamstring injury, did not practice")
    opp = sc.score("Jordan Mason is the every-down workhorse now, target share up, breakout")
    assert inj.sentiment < -0.3 and inj.injury_flag and not inj.opportunity_flag
    assert opp.sentiment > 0.3 and opp.opportunity_flag and not opp.injury_flag
    print(f"✓ sentiment: injury {inj.sentiment:+.2f}(flag={inj.injury_flag}) · "
          f"opportunity {opp.sentiment:+.2f}(flag={opp.opportunity_flag})")
    matcher = PlayerMatcher([
        {"id": "p1", "full_name": "Bijan Robinson"},
        {"id": "p2", "full_name": "Jordan Mason"},
        {"id": "p3", "full_name": "Josh Allen"},  # must NOT match bare "Josh"
    ])
    assert matcher.match("Bijan Robinson and Jordan Mason both active") == {"p1", "p2"}
    assert matcher.match("Josh looked good") == set()  # surname/firstname alone → no match
    print("✓ player matcher: full-name match, no bare-name false positives")
    print("\nALL SELFTEST CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
