// C01 adversarial coverage for the consolidated bye-coverage + contingent-role module.
// Required cases (v6 contract): missing byes, FLEX, superflex, double counting,
// false positives, ambiguous depth, missing metadata.
import { describe, it, expect } from "vitest";
import { weeklyByeCoverage, contingentRole } from "./contingency";
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

describe("weeklyByeCoverage — candidate-aware max-matched weekly coverage", () => {
  it("covers a same-position starter bye when the candidate's own bye differs", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("WR", mk("wr1", "WR", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([7]);
    expect(r.degraded).toBe(false);
  });

  it("a shared bye gets NO credit (candidate is on bye the same week)", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 7 }), [at("WR", mk("wr1", "WR", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.degraded).toBe(false);
  });

  it("missing candidate bye: no credit, degraded", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: null }), [at("WR", mk("wr1", "WR", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.degraded).toBe(true);
  });

  it("missing starter bye at an eligible slot: that hole is unknown → degraded, no phantom credit", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("WR", mk("wr1", "WR", { bye: null }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.degraded).toBe(true);
  });

  it("double counting: two starters on the SAME bye week yield one covered week, not two", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("WR", mk("wr2", "WR", { bye: 7 }))];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), starters, GENERAL_ROSTER);
    expect(r.covered).toEqual([7]);
  });

  it("distinct bye weeks each count once", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("WR", mk("wr2", "WR", { bye: 11 }))];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), starters, GENERAL_ROSTER);
    expect(r.covered).toEqual([7, 11]);
  });

  it("FLEX: a WR candidate covers an RB starter's bye when that starter occupies FLEX", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("FLEX", mk("rb3", "RB", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([7]);
  });

  it("slot eligibility: a WR candidate cannot cover an RB starter in a dedicated RB slot", () => {
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 5 }), [at("RB", mk("rb1", "RB", { bye: 7 }))], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
    expect(r.degraded).toBe(false);
  });

  it("superflex: a QB candidate covers an OP-slot QB bye in a superflex template only", () => {
    const qb2 = mk("qb2", "QB", { bye: 5 });
    const opQb = [at("OP", mk("qb1b", "QB", { bye: 9 }))];
    expect(weeklyByeCoverage(qb2, opQb, SUPERFLEX_ROSTER).covered).toEqual([9]);
    // the general template has no OP slot; an OP entry not in the template is ignored
    expect(weeklyByeCoverage(qb2, opQb, GENERAL_ROSTER).covered).toEqual([]);
  });

  it("marginal matching: a hole already covered by an owned bench body earns the candidate nothing", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })]; // already covers week 7
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([]);
    expect(r.degraded).toBe(false);
  });

  it("marginal matching: two same-week holes and one owned cover leave one hole for the candidate", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("WR", mk("wr2", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([7]);
  });

  it("marginal matching: an owned body on the SAME bye as the hole does not count as a cover", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 7 })]; // absent the same week — no cover
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([7]);
  });

  it("marginal matching: an ineligible owned body (RB for a WR slot) does not block the candidate", () => {
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 }))];
    const bench = [mk("rb8", "RB", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([7]);
  });

  it("marginal matching with an augmenting path: the flexible owned body re-routes to FLEX so the candidate covers WR", () => {
    // holes in week 7: WR slot (WR-only under this check via cand) and FLEX (RB or WR).
    // Owned wr8 could sit in either; a greedy assignment of wr8→WR must not blind the
    // matcher to (wr8→FLEX, cand→WR).
    const starters = [at("WR", mk("wr1", "WR", { bye: 7 })), at("FLEX", mk("rb3", "RB", { bye: 7 }))];
    const bench = [mk("wr8", "WR", { bye: 5 })];
    const r = weeklyByeCoverage(mk("wr9", "WR", { bye: 4 }), starters, GENERAL_ROSTER, bench);
    expect(r.covered).toEqual([7]);
  });

  it("the candidate cannot cover its own starting slot", () => {
    const cand = mk("wr1", "WR", { bye: 7 });
    const r = weeklyByeCoverage(cand, [at("WR", cand)], GENERAL_ROSTER);
    expect(r.covered).toEqual([]);
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
