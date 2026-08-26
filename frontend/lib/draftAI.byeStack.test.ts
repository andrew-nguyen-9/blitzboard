// e10 — the bench-depth-conditional bye-stack seam.
//
// e6 refuted a FLAT byeStackPenalty: the sign is conditional on bench depth (deep benches prefer
// CLUSTERED byes, shallow benches prefer them spread). Neither replacement value cleared e10's
// gate, so the seam ships INERT — `byeStackDeepBenchSlots: 99` means the deep-bench arm never
// fires and behaviour is bit-identical to e1's flat 12. These tests lock BOTH facts: the default
// is a no-op, and the mechanism actually works when a future unit (e12) turns it on.
import { describe, it, expect } from "vitest";
import { byeStackPenalty, DEFAULT_POLICY } from "./draftAI";
import type { PlayerWithValue } from "./types";

const mk = (id: string, position: string, bye: number): PlayerWithValue =>
  ({
    id,
    full_name: id,
    position,
    nfl_team: "XX",
    bye_week: bye,
    injury_status: null,
    metadata: {},
    value: { player_id: id, engine: "vorp", value: 100, vor: 50, replacement: 50, rank: 1 },
  }) as unknown as PlayerWithValue;

const ROSTER = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "WR", eligible: ["WR"] },
];

// Two starters already sit on bye week 7; the candidate would be the third.
const STARTERS = [mk("qb1", "QB", 7), mk("rb1", "RB", 7)];
const CAND = mk("wr1", "WR", 7);

const ctx = (benchSize: number) =>
  ({ teamPicks: STARTERS, roster: ROSTER, benchSize }) as never;

describe("e10 byeStackPenalty — conditional on bench depth", () => {
  it("ships INERT: the default policy is the flat e1 penalty at every bench size", () => {
    expect(DEFAULT_POLICY.byeStackDeepBenchSlots).toBe(99);
    expect(DEFAULT_POLICY.byeStackPenaltyDeepBench).toBe(DEFAULT_POLICY.byeStackPenalty);
    for (const bench of [4, 6, 8, 12]) {
      expect(byeStackPenalty(CAND, ctx(bench), DEFAULT_POLICY)).toBe(
        2 * DEFAULT_POLICY.byeStackPenalty,
      );
    }
  });

  it("switches on bench depth once the threshold is armed, and may go NEGATIVE", () => {
    const p = {
      ...DEFAULT_POLICY,
      byeStackDeepBenchSlots: 7,
      byeStackPenalty: 18,
      byeStackPenaltyDeepBench: -12,
    };
    expect(byeStackPenalty(CAND, ctx(6), p)).toBe(36); // shallow bench: spread byes
    expect(byeStackPenalty(CAND, ctx(8), p)).toBe(-24); // deep bench: clustering is a BONUS
  });

  it("is zero for a candidate with no bye and scales with shared starters", () => {
    expect(byeStackPenalty(mk("wr2", "WR", 0), ctx(6), DEFAULT_POLICY)).toBe(0);
    const oneShared = { teamPicks: [STARTERS[0]], roster: ROSTER, benchSize: 6 } as never;
    expect(byeStackPenalty(CAND, oneShared, DEFAULT_POLICY)).toBe(
      DEFAULT_POLICY.byeStackPenalty,
    );
  });
});
