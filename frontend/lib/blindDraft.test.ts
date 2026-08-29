import { describe, expect, it } from "vitest";
import * as draftAI from "./draftAI";
import { mulberry32, runSnakeDraft } from "./snakeDraft";
import { fillRoster, SUPERFLEX_ROSTER, type RosterSlot } from "./draft";
import type { PlayerWithValue } from "./types";

function player(id: string, position: string, adp: number | null): PlayerWithValue {
  return {
    id,
    full_name: id,
    position,
    nfl_team: "TST",
    bye_week: 8,
    metadata: {},
    value: {
      player_id: id,
      engine: "vorp",
      value: 10_000,
      vor: 9_000,
      replacement: 1_000,
      boom: 20_000,
      bust: -20_000,
      adp,
      rank: -999,
    },
  } as PlayerWithValue;
}

const ROSTER: RosterSlot[] = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "WR", eligible: ["WR"] },
  { slot: "FLEX", eligible: ["RB", "WR", "TE"] },
  { slot: "K", eligible: ["K"] },
  { slot: "DST", eligible: ["DST", "DEF"] },
];

function context(
  pool: PlayerWithValue[],
  teamPicks: PlayerWithValue[] = [],
  overrides: Partial<draftAI.AIContext> = {},
): draftAI.AIContext {
  return {
    pool,
    teamPicks,
    roster: ROSTER,
    benchSize: 2,
    allPicks: [],
    numTeams: 12,
    picksUntilNext: 12,
    round: 1,
    totalRounds: ROSTER.length + 2,
    ...overrides,
  };
}

function marketPool(): PlayerWithValue[] {
  const counts = { QB: 60, RB: 110, WR: 130, TE: 50, K: 24, DEF: 24 };
  const pool = Object.entries(counts).flatMap(([position, count]) =>
    Array.from({ length: count }, (_, i) => player(`${position}-${i}`, position, null)),
  );
  // Interleave positions into a plausible overall market board instead of grouping
  // every QB/K/DST together. The benchmark policy sees only this ADP and position.
  const positionOrder = ["RB", "WR", "QB", "TE"];
  const marketOrder = (p: PlayerWithValue) => {
    const index = Number(p.id.split("-")[1]);
    if (p.position === "K") return 260 + index * 2;
    if (draftAI.norm(p.position) === "DST") return 261 + index * 2;
    return index * positionOrder.length + positionOrder.indexOf(p.position!);
  };
  pool.sort((a, b) => {
    return marketOrder(a) - marketOrder(b) || a.id.localeCompare(b.id);
  });
  pool.forEach((p, i) => {
    p.value!.adp = i + 1;
  });
  return pool;
}

describe("blind human-market opponent", () => {
  it("exposes a source-isolated market picker", () => {
    expect(typeof (draftAI as Record<string, unknown>).pickHumanAdp).toBe("function");
  });

  it("strict provider mode follows the earliest available rank", () => {
    const pool = [player("wr2", "WR", 2), player("rb1", "RB", 1), player("qb3", "QB", 3)];
    expect(draftAI.pickHumanAdp(context(pool), { topK: 1 })?.id).toBe("rb1");
  });

  it("is byte-identical when every BlitzBoard model field is adversarially mutated", () => {
    const original = [
      player("rb1", "RB", 1),
      player("wr2", "WR", 2),
      player("qb3", "QB", 3),
      player("te4", "TE", 4),
    ];
    const poisoned = structuredClone(original);
    for (const [i, p] of poisoned.entries()) {
      Object.assign(p.value!, {
        value: i % 2 ? Number.MAX_SAFE_INTEGER : -Number.MAX_SAFE_INTEGER,
        vor: i % 2 ? -Infinity : Infinity,
        replacement: Number.NaN,
        boom: i * -1_000_000,
        bust: i * 1_000_000,
        rank: 1000 - i,
      });
      p.injury_status = i % 2 ? "IR" : null;
      p.metadata = { depth_chart_order: 99 - i, trend_score: i * 100 };
    }
    const a = draftAI.pickHumanAdp(context(original, [], { rng: mulberry32(771) }), { topK: 4 });
    const b = draftAI.pickHumanAdp(context(poisoned, [], { rng: mulberry32(771) }), { topK: 4 });
    expect(b?.id).toBe(a?.id);
  });

  it("uses market rank as the causal input", () => {
    const pool = [player("rb", "RB", 2), player("wr", "WR", 1)];
    expect(draftAI.pickHumanAdp(context(pool), { topK: 1 })?.id).toBe("wr");
    pool[0].value!.adp = 1;
    pool[1].value!.adp = 2;
    expect(draftAI.pickHumanAdp(context(pool), { topK: 1 })?.id).toBe("rb");
  });

  it("forces a pick that preserves starter completion at the last possible turn", () => {
    const owned = [player("qb-owned", "QB", 50)];
    const roster: RosterSlot[] = [
      { slot: "QB", eligible: ["QB"] },
      { slot: "RB", eligible: ["RB"] },
    ];
    const pool = [player("wr-adp1", "WR", 1), player("rb-adp90", "RB", 90)];
    const pick = draftAI.pickHumanAdp(
      context(pool, owned, { roster, round: 2, totalRounds: 2 }),
      { topK: 8 },
    );
    expect(pick?.id).toBe("rb-adp90");
  });

  it("does not over-constrain early picks when enough turns remain", () => {
    const owned = [player("qb-owned", "QB", 50)];
    const roster: RosterSlot[] = [
      { slot: "QB", eligible: ["QB"] },
      { slot: "RB", eligible: ["RB"] },
    ];
    const pool = [player("wr-adp1", "WR", 1), player("rb-adp90", "RB", 90)];
    const pick = draftAI.pickHumanAdp(
      context(pool, owned, { roster, round: 1, totalRounds: 3 }),
      { topK: 1 },
    );
    expect(pick?.id).toBe("wr-adp1");
  });

  it("caps duplicate kicker and defense picks without reading model values", () => {
    const owned = [player("k-owned", "K", 80), player("dst-owned", "DST", 90)];
    const pool = [
      player("k-adp1", "K", 1),
      player("def-adp2", "DEF", 2),
      player("wr-adp3", "WR", 3),
    ];
    expect(draftAI.pickHumanAdp(context(pool, owned), { topK: 1 })?.id).toBe("wr-adp3");
  });

  it("replays the same seeded sequence exactly", () => {
    const pool = Array.from({ length: 8 }, (_, i) => player(`p${i + 1}`, i % 2 ? "WR" : "RB", i + 1));
    const sequence = (seed: number) => {
      const rng = mulberry32(seed);
      return Array.from({ length: 20 }, () =>
        draftAI.pickHumanAdp(context(pool, [], { rng }), { topK: 8 })?.id,
      );
    };
    expect(sequence(0x5eed)).toEqual(sequence(0x5eed));
    expect(sequence(0x5eed)).not.toEqual(sequence(0x5eee));
  });

  it("produces bounded, top-heavy variation instead of chaotic reaches", () => {
    const pool = Array.from({ length: 12 }, (_, i) => player(`p${i + 1}`, "WR", i + 1));
    const counts = new Map<string, number>();
    for (let seed = 1; seed <= 1000; seed++) {
      const id = draftAI.pickHumanAdp(context(pool, [], { rng: mulberry32(seed) }), { topK: 8 })!.id;
      counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    expect([...counts.keys()].every((id) => Number(id.slice(1)) <= 8)).toBe(true);
    expect(counts.size).toBeGreaterThanOrEqual(6);
    expect(counts.get("p1")!).toBeGreaterThan(counts.get("p8")! * 3);
  });

  it("places missing and non-finite ADP after ranked players with a stable id tie-break", () => {
    const pool = [
      player("z-null", "WR", null),
      player("b-inf", "RB", Infinity),
      player("a-nan", "QB", Number.NaN),
      player("ranked", "TE", 250),
    ];
    expect(draftAI.pickHumanAdp(context(pool), { topK: 1 })?.id).toBe("ranked");
    pool.pop();
    expect(draftAI.pickHumanAdp(context(pool), { topK: 1 })?.id).toBe("a-nan");
  });

  it("returns null for an empty pool", () => {
    expect(draftAI.pickHumanAdp(context([]), { topK: 8 })).toBeNull();
  });

  it("keeps an entire seeded draft byte-identical after model fields are poisoned", () => {
    const original = marketPool();
    const poisoned = structuredClone(original);
    poisoned.forEach((p, i) => {
      Object.assign(p.value!, {
        value: i % 2 ? Infinity : -Infinity,
        vor: i % 3 ? Number.NaN : Number.MAX_SAFE_INTEGER,
        replacement: -Number.MAX_SAFE_INTEGER,
        boom: i * 1e9,
        bust: i * -1e9,
        rank: poisoned.length - i,
      });
      p.injury_status = i % 2 ? "IR" : null;
    });
    const draft = (pool: PlayerWithValue[]) =>
      runSnakeDraft(pool, {
        numTeams: 12,
        rng: mulberry32(0xabc123),
        chooser: (ctx) => draftAI.pickHumanAdp(ctx, { topK: 8 }),
      }).map((pick) => `${pick.pickNo}:${pick.team}:${pick.player.id}`);
    expect(draft(poisoned)).toEqual(draft(original));
  });

  it.each([
    [10, 11],
    [10, 912],
    [12, 22],
    [12, 923],
    [14, 33],
    [14, 934],
  ])("%i teams, seed %i: every completed roster is legal and duplicate-free", (teams, seed) => {
    const picks = runSnakeDraft(marketPool(), {
      numTeams: teams,
      rng: mulberry32(seed),
      chooser: (ctx) => draftAI.pickHumanAdp(ctx, { topK: 8 }),
    });
    expect(new Set(picks.map((pick) => pick.player.id)).size).toBe(picks.length);
    for (let team = 1; team <= teams; team++) {
      const roster = picks.filter((pick) => pick.team === team).map((pick) => pick.player);
      expect(fillRoster(roster, SUPERFLEX_ROSTER).needs).toEqual([]);
      expect(roster.filter((p) => draftAI.norm(p.position) === "K")).toHaveLength(1);
      expect(roster.filter((p) => draftAI.norm(p.position) === "DST")).toHaveLength(1);
    }
  });
});
