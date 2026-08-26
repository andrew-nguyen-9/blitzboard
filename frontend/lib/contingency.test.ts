// C01 adversarial coverage for the consolidated bye-coverage + contingent-role module.
// Required cases (v6 contract): missing byes, FLEX, superflex, double counting,
// false positives, ambiguous depth, missing metadata.
import { describe, it, expect } from "vitest";
import { weeklyByeCoverage, contingentRole, contingentValuation, injuryRisk, type ByeCoverage } from "./contingency";
import { SUPERFLEX_ROSTER, type RosterSlot } from "./draft";
import type { PlayerWithValue } from "./types";

const GENERAL_ROSTER: RosterSlot[] = SUPERFLEX_ROSTER.filter((s) => s.slot !== "OP");

function mk(
  id: string,
  position: string,
  opts: {
    bye?: number | null;
    team?: string | null;
    depth?: number | null;
    role_transfer?: string;
    injury?: string | null;
  } = {},
): PlayerWithValue {
  const { bye = null, team = null, depth = null, role_transfer, injury = null } = opts;
  return {
    id,
    full_name: id,
    position,
    nfl_team: team,
    bye_week: bye,
    injury_status: injury,
    metadata: {
      depth_chart_order: depth,
      ...(role_transfer ? { role_transfer } : {}),
    },
    value: { player_id: id, engine: "vorp", value: 100, vor: 100, replacement: 0, boom: 120, bust: 60, adp: null, rank: null },
  } as PlayerWithValue;
}

const at = (slot: string, p: PlayerWithValue | null) => ({ slot, player: p });
const weeks = (r: ByeCoverage) => r.covered.map((c) => c.week);

describe("weeklyByeCoverage — candidate-aware max-matched weekly coverage", () => {
  it("covers a same-position starter bye when the candidate's own bye differs", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("WR", mk("wr1", "WR", { bye: 7 }))], GENERAL_ROSTER);
    expect(weeks(r)).toEqual([7]);
    expect(r.degraded).toBe(false);
  });

  it("a shared bye gets NO credit (candidate is on bye the same week)", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 7 }), [at("WR", mk("wr1", "WR", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
    expect(r.degraded).toBe(false);
  });

  it("missing candidate bye: no credit, degraded", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: null }), [at("WR", mk("wr1", "WR", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
    expect(r.degraded).toBe(true);
  });

  it("missing starter bye at an eligible slot: that hole is unknown → degraded, no phantom credit", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("WR", mk("wr1", "WR", { bye: null }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
    expect(r.degraded).toBe(true);
  });

  it("double counting: two starters on the SAME bye week yield one covered week, not two", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("WR", mk("wr2", "WR", { bye: 7 }))];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), starters, GENERAL_ROSTER);
    expect(weeks(r)).toEqual([7]);
  });

  it("distinct bye weeks each count once", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("WR", mk("wr2", "WR", { bye: 11 }))];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), starters, GENERAL_ROSTER);
    expect(weeks(r)).toEqual([7, 11]);
  });

  it("FLEX: a WR candidate covers an RB starter's bye when that starter occupies FLEX", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("FLEX", mk("rb3", "RB", { bye: 7 }))], GENERAL_ROSTER);
    expect(weeks(r)).toEqual([7]);
  });

  it("slot eligibility: a WR candidate cannot cover an RB starter in a dedicated RB slot", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("RB", mk("rb1", "RB", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
    expect(r.degraded).toBe(false);
  });

  it("superflex: a QB candidate covers an OP-slot QB bye in a superflex template only", () => {
    const qb2 = mk("qb2", "QB", { bye: 5 });
    const opQb = [at("OP", mk("qb1b", "QB", { bye: 9 }))];
    expect(weeks(weeklyByeCoverage(qb2, opQb, SUPERFLEX_ROSTER))).toEqual([9]);
    // the general template has no OP slot; an OP entry not in the template is ignored
    expect(weeks(weeklyByeCoverage(qb2, opQb, GENERAL_ROSTER))).toEqual([]);
  });

  it("marginal matching: a hole already covered by an owned bench body earns the candidate nothing", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })]; // already covers week 7
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
    expect(r.degraded).toBe(false);
  });

  it("marginal matching: two same-week holes and one owned cover leave one hole for the candidate", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("WR", mk("wr2", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(weeks(r)).toEqual([7]);
  });

  it("marginal matching: an owned body on the SAME bye as the hole does not count as a cover", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 7 })]; // absent the same week — no cover
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(weeks(r)).toEqual([7]);
  });

  it("marginal matching: an ineligible owned body (RB for a WR slot) does not block the candidate", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("rb8", "RB", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(weeks(r)).toEqual([7]);
  });

  it("marginal matching with an augmenting path: the flexible owned body re-routes to FLEX so the candidate covers WR", () => {
    // holes in week 7: WR slot (WR-only under this check via cand) and FLEX (RB or WR).
    // Owned wr8 could sit in either; a greedy assignment of wr8→WR must not blind the
    // matcher to (wr8→FLEX, cand→WR).
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("FLEX", mk("rb3", "RB", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(weeks(r)).toEqual([7]);
  });

  it("the candidate cannot cover its own starting slot", () => {
    const cand = mk("wr1", "WR", { bye: 7 });
    const r = weeklyByeCoverage(cand, [at("WR", cand)], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
  });
});

describe("weeklyByeCoverage — covered records and expected starts (C01A)", () => {
  it("returns the covered week/slot/starter from the matching assignment, and expectedStarts = records", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("FLEX", mk("rb3", "RB", { bye: 11 }))];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), starters, GENERAL_ROSTER);
    expect(r.covered).toEqual([
      { week: 7, slot: "WR", starterId: "wr1" },
      { week: 11, slot: "FLEX", starterId: "rb3" },
    ]);
    expect(r.expectedStarts).toBe(2);
  });

  it("identifies WHICH of two same-week holes the candidate fills once an owned body takes the other", () => {
    // rb8 is eligible for the FLEX hole only, so the WR candidate's record must land on
    // the WR hole — the record comes from the real assignment, not a guess.
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("FLEX", mk("rb3", "RB", { bye: 7 }))];
    const bench = [mk("rb8", "RB", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([{ week: 7, slot: "WR", starterId: "wr1" }]);
    expect(r.expectedStarts).toBe(1);
  });

  it("is deterministic: identical inputs give identical records", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("FLEX", mk("rb3", "RB", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })];
    const cand = () => mk("wr9", "WR", { bye: 4 });
    const a = weeklyByeCoverage(cand(), starters, GENERAL_ROSTER, bench);
    const b = weeklyByeCoverage(cand(), starters, GENERAL_ROSTER, bench);
    expect(a).toEqual(b);
    expect(a.covered).toHaveLength(1);
    expect(a.covered[0].week).toBe(7);
  });
});

describe("weeklyByeCoverage — missing owned-bench bye metadata degrades (C01A)", () => {
  it("an owned body with an unknown bye that could occupy a hole makes the marginal verdict degraded", () => {
    // wr8's bye is unknown: it might already cover week 7 (candidate marginal = 0) or
    // share the bye (candidate marginal = 1). The apparent-certain credit must degrade.
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: null })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(weeks(r)).toEqual([7]); // baseline (bye-less body excluded) still credits…
    expect(r.degraded).toBe(true); // …but flagged conditional on missing metadata
  });

  it("an owned bye-less body that can start in NO hole slot does not degrade", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("k8", "K", { bye: null })]; // a K can never occupy the WR hole
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(weeks(r)).toEqual([7]);
    expect(r.degraded).toBe(false);
  });
});

describe("contingentRole — structured evidence replaces the depth-inferred handcuff boolean", () => {
  it("RB succession: same team + authoritative direct-backup depth is supported", () => {
    const starter = mk("rb1", "RB", { team: "SF", depth: 1 });
    const cand = mk("rb2", "RB", { team: "SF", depth: 2 });
    const r = contingentRole(cand, starter);
    expect(r.status).toBe("supported");
    expect(r.evidence).toMatchObject({ kind: "rb-succession", starterId: "rb1", team: "SF" });
  });

  it("false positive: an RB behind my starter but on a DIFFERENT team gets no evidence", () => {
    const r = contingentRole(mk("rb2", "RB", { team: "DAL", depth: 2 }), mk("rb1", "RB", { team: "SF", depth: 1 }));
    expect(r.status).toBe("no-evidence");
    expect(r.evidence).toBeNull();
  });

  it("ambiguous depth: same-team RB with no depth_chart_order is ambiguous, not supported", () => {
    const r = contingentRole(mk("rb2", "RB", { team: "SF", depth: null }), mk("rb1", "RB", { team: "SF" }));
    expect(r.status).toBe("ambiguous-depth");
    expect(r.evidence).toBeNull();
  });

  it("buried depth: a same-team RB3+ is not a successor", () => {
    const r = contingentRole(mk("rb3", "RB", { team: "SF", depth: 3 }), mk("rb1", "RB", { team: "SF", depth: 1 }));
    expect(r.status).toBe("no-evidence");
  });

  it("QB requires authoritative depth: QB2 by feed is supported", () => {
    const r = contingentRole(mk("qbB", "QB", { team: "KC", depth: 2 }), mk("qbA", "QB", { team: "KC", depth: 1 }));
    expect(r.status).toBe("supported");
    expect(r.evidence).toMatchObject({ kind: "qb-authoritative-depth" });
  });

  it("QB without feed depth gets no credit (ambiguous), never inferred from projections", () => {
    const r = contingentRole(mk("qbB", "QB", { team: "KC", depth: null }), mk("qbA", "QB", { team: "KC" }));
    expect(r.status).toBe("ambiguous-depth");
  });

  it("WR requires explicit role-transfer evidence; same-team depth alone is not evidence", () => {
    const noEv = contingentRole(mk("wr2", "WR", { team: "MIA", depth: 2 }), mk("wr1", "WR", { team: "MIA", depth: 1 }));
    expect(noEv.status).toBe("no-evidence");
    const ev = contingentRole(
      mk("wr2", "WR", { team: "MIA", depth: 2, role_transfer: "beat-report:2026-08-20" }),
      mk("wr1", "WR", { team: "MIA", depth: 1 }),
    );
    expect(ev.status).toBe("supported");
    expect(ev.evidence).toMatchObject({ kind: "explicit-role-transfer", source: "beat-report:2026-08-20" });
  });

  it("TE follows the WR rule", () => {
    const r = contingentRole(mk("te2", "TE", { team: "BAL", depth: 2 }), mk("te1", "TE", { team: "BAL" }));
    expect(r.status).toBe("no-evidence");
  });

  it("missing metadata: unknown NFL team on either side is missing-metadata, no credit", () => {
    expect(contingentRole(mk("rb2", "RB", { team: null, depth: 2 }), mk("rb1", "RB", { team: "SF" })).status).toBe("missing-metadata");
    expect(contingentRole(mk("rb2", "RB", { team: "SF", depth: 2 }), mk("rb1", "RB", { team: null })).status).toBe("missing-metadata");
  });

  it("no starter to succeed: no-evidence", () => {
    expect(contingentRole(mk("rb2", "RB", { team: "SF", depth: 2 }), null).status).toBe("no-evidence");
  });

  it("K/DST never carry a contingent role", () => {
    expect(contingentRole(mk("k2", "K", { team: "SF", depth: 2 }), mk("k1", "K", { team: "SF", depth: 1 })).status).toBe("not-applicable");
  });
});

describe("contingentRole — position compatibility and authoritative starter depth (C01A)", () => {
  it("cross-position: a depth-2 RB paired with a same-team WR is never supported", () => {
    const r = contingentRole(mk("rb2", "RB", { team: "SF", depth: 2 }), mk("wr1", "WR", { team: "SF", depth: 1 }));
    expect(r.status).toBe("no-evidence");
    expect(r.evidence).toBeNull();
  });

  it("cross-position: explicit role-transfer cannot cross positions either (WR cand, TE starter)", () => {
    const r = contingentRole(
      mk("wr2", "WR", { team: "MIA", depth: 2, role_transfer: "beat-report:2026-08-20" }),
      mk("te1", "TE", { team: "MIA", depth: 1 }),
    );
    expect(r.status).toBe("no-evidence");
  });

  it("missing starter depth: a depth-2 RB behind a depth-less starter is ambiguous, not supported", () => {
    const r = contingentRole(mk("rb2", "RB", { team: "SF", depth: 2 }), mk("rb1", "RB", { team: "SF", depth: null }));
    expect(r.status).toBe("ambiguous-depth");
    expect(r.evidence).toBeNull();
  });

  it("ambiguous starter depth: two same-team RBs both at depth 2 are ambiguous, not supported", () => {
    const r = contingentRole(mk("rb2", "RB", { team: "SF", depth: 2 }), mk("rbA", "RB", { team: "SF", depth: 2 }));
    expect(r.status).toBe("ambiguous-depth");
  });

  it("QB requires the starter at authoritative depth 1 as well", () => {
    expect(contingentRole(mk("qbB", "QB", { team: "KC", depth: 2 }), mk("qbA", "QB", { team: "KC", depth: null })).status).toBe("ambiguous-depth");
    expect(contingentRole(mk("qbB", "QB", { team: "KC", depth: 2 }), mk("qbA", "QB", { team: "KC", depth: 2 })).status).toBe("ambiguous-depth");
  });
});

describe("contingentValuation — the ONE shared whether/probability/value result (C01A)", () => {
  const starter = (injury: string | null = null) => {
    const s = mk("rb1", "RB", { team: "SF", depth: 1, bye: 7 });
    s.injury_status = injury;
    return s;
  };
  const backup = () => mk("rb2", "RB", { team: "SF", depth: 2, bye: 7 });

  it("supported: eligible, relevant starter, probability and expected value populated, no degradation", () => {
    const v = contingentValuation(backup(), starter("Questionable"));
    expect(v.eligible).toBe(true);
    expect(v.status).toBe("supported");
    expect(v.starterId).toBe("rb1");
    expect(v.inheritanceProb).toBe(injuryRisk("Questionable"));
    // expectedValue = inheritanceProb × raw projection mean (vor 100 + replacement 0)
    expect(v.expectedValue).toBeCloseTo(v.inheritanceProb * 100, 10);
    expect(v.degradedReason).toBeNull();
    expect(v.evidence).toMatchObject({ kind: "rb-succession", starterId: "rb1" });
  });

  it("a sicker starter raises the shared inheritance probability and expected value", () => {
    const healthy = contingentValuation(backup(), starter(null));
    const out = contingentValuation(backup(), starter("Out"));
    expect(out.inheritanceProb).toBeGreaterThan(healthy.inheritanceProb);
    expect(out.expectedValue).toBeGreaterThan(healthy.expectedValue);
  });

  it("not eligible: zero probability/value and an explicit degradation reason when evidence is unverifiable", () => {
    const ambiguous = contingentValuation(backup(), mk("rb1", "RB", { team: "SF", depth: null }));
    expect(ambiguous.eligible).toBe(false);
    expect(ambiguous.inheritanceProb).toBe(0);
    expect(ambiguous.expectedValue).toBe(0);
    expect(ambiguous.status).toBe("ambiguous-depth");
    expect(ambiguous.degradedReason).toMatch(/depth chart/);

    const noEvidence = contingentValuation(mk("rb2", "RB", { team: "DAL", depth: 2 }), starter());
    expect(noEvidence.eligible).toBe(false);
    expect(noEvidence.degradedReason).toBeNull(); // clean negative, not degraded
    expect(noEvidence.starterId).toBe("rb1"); // the proposed relevant starter is still named
  });
});

describe("weeklyByeCoverage — 2QB and custom slot shapes (C01A)", () => {
  const TWO_QB: RosterSlot[] = [
    { slot: "QB", eligible: ["QB"] },
    { slot: "QB", eligible: ["QB"] },
    { slot: "RB", eligible: ["RB"] },
  ];

  it("a QB candidate covers the second dedicated QB slot's bye in a 2QB template", () => {
    const starters = [at("QB", mk("qbA", "QB", { bye: 6 })), at("QB", mk("qbB", "QB", { bye: 9 }))];
    const r = weeklyByeCoverage(mk("qb9", "QB", { bye: 4 }), starters, TWO_QB);
    expect(r.covered).toEqual([
      { week: 6, slot: "QB", starterId: "qbA" },
      { week: 9, slot: "QB", starterId: "qbB" },
    ]);
    expect(r.expectedStarts).toBe(2);
  });

  it("a custom template without a slot for the candidate's position yields zero coverage", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), [at("QB", mk("qbA", "QB", { bye: 6 }))], TWO_QB);
    expect(r.covered).toEqual([]);
    expect(r.expectedStarts).toBe(0);
    expect(r.degraded).toBe(false);
  });
});
