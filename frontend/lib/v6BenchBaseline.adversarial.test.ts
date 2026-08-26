import { describe, expect, it } from "vitest";
import { benchScore, type BenchCtx } from "./benchScore";
import { byeCover, DEFAULT_POLICY, overfillPenalty } from "./draftAI";
import type { RosterSlot } from "./draft";
import type { PlayerWithValue } from "./types";

function player(
  id: string,
  position: string,
  projection: number,
  options: {
    bye?: number | null;
    team?: string | null;
    depth?: number;
    injury?: string | null;
  } = {},
): PlayerWithValue {
  return {
    id,
    full_name: id,
    position,
    nfl_team: options.team ?? null,
    bye_week: options.bye ?? null,
    injury_status: options.injury ?? null,
    metadata: options.depth == null ? {} : { depth_chart_order: options.depth },
    value: {
      player_id: id,
      engine: "vorp",
      value: projection,
      vor: projection,
      replacement: 0,
      boom: projection * 1.25,
      bust: projection * 0.5,
      adp: null,
      rank: null,
    },
  } as PlayerWithValue;
}

describe("C00 baseline: candidate-aware bye coverage gaps", () => {
  it.fails("gives no credit when the candidate shares the starter's bye", () => {
    const starter = player("rb1", "RB", 240, { bye: 7 });
    const candidate = player("rb2", "RB", 130, { bye: 7 });
    expect(byeCover(candidate, [starter])).toBe(0);
  });

  it.fails("degrades safely when the candidate bye is missing", () => {
    const starter = player("rb1", "RB", 240, { bye: 7 });
    const candidate = player("rb2", "RB", 130, { bye: null });
    expect(byeCover(candidate, [starter])).toBe(0);
  });

  it.fails("uses FLEX eligibility rather than strict position equality", () => {
    const flexStarter = player("wr1", "WR", 220, { bye: 8 });
    const candidate = player("rb2", "RB", 130, { bye: 10 });
    expect(byeCover(candidate, [flexStarter])).toBe(1);
  });

  it.fails("uses superflex eligibility rather than strict position equality", () => {
    const opStarter = player("qb2", "QB", 220, { bye: 9 });
    const candidate = player("wr3", "WR", 130, { bye: 11 });
    expect(byeCover(candidate, [opStarter])).toBe(1);
  });
});

describe("C00 baseline: generic handcuff false positives", () => {
  function score(candidate: PlayerWithValue, starter: PlayerWithValue): number {
    const ctx: BenchCtx = { roster: [starter, candidate], superflex: false };
    return benchScore(candidate, ctx).score;
  }

  it.fails("does not amplify an unrelated WR because another WR is injured", () => {
    const candidate = player("buf-wr", "WR", 120, { team: "BUF", depth: 2 });
    const injured = player("kc-wr", "WR", 220, { team: "KC", injury: "Out" });
    const healthy = player("kc-wr", "WR", 220, { team: "KC" });
    expect(score(candidate, injured)).toBe(score(candidate, healthy));
  });

  it.fails("does not amplify an unrelated RB without succession evidence", () => {
    const candidate = player("buf-rb", "RB", 120, { team: "BUF", depth: 2 });
    const injured = player("kc-rb", "RB", 220, { team: "KC", injury: "Out" });
    const healthy = player("kc-rb", "RB", 220, { team: "KC" });
    expect(score(candidate, injured)).toBe(score(candidate, healthy));
  });
});

describe("C00 baseline: fixed production overfill authority", () => {
  it("records the shipped v4 scalar depths", () => {
    expect(DEFAULT_POLICY.overfillDepth).toEqual({ QB: 3, RB: 5, WR: 5, TE: 2, K: 1, DST: 1 });
  });

  it("produces the same RB penalty for 1QB and superflex because config is not an input", () => {
    const candidate = player("rb6", "RB", 100);
    const teamPicks = Array.from({ length: 5 }, (_, i) => player(`rb${i}`, "RB", 200 - i));
    const oneQb: RosterSlot[] = [{ slot: "QB", eligible: ["QB"] }];
    const superflex: RosterSlot[] = [
      { slot: "QB", eligible: ["QB"] },
      { slot: "OP", eligible: ["QB", "RB", "WR", "TE"] },
    ];
    const ctx = (roster: RosterSlot[]) => ({
      pool: [candidate], teamPicks, roster, benchSize: 6, allPicks: [], numTeams: 12,
      picksUntilNext: 1, round: 10, totalRounds: 16,
    });
    expect(overfillPenalty(candidate, ctx(oneQb), DEFAULT_POLICY)).toBe(
      overfillPenalty(candidate, ctx(superflex), DEFAULT_POLICY),
    );
  });
});
