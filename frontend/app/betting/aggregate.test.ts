import { describe, it, expect } from "vitest";
import {
  normalizeEvents,
  biggestBets,
  topTotals,
  chalkParlay,
  impliedProb,
  toDecimal,
  toAmerican,
  type RawEvent,
} from "./aggregate";

const ev = (
  id: string,
  home: string,
  away: string,
  homeSpread: number,
  total: number,
  homeML: number,
  awayML: number,
): RawEvent => ({
  id,
  commence_time: "2025-09-08T00:20:00Z",
  home_team: home,
  away_team: away,
  bookmakers: [
    {
      key: "dk",
      markets: [
        { key: "h2h", outcomes: [{ name: home, price: homeML }, { name: away, price: awayML }] },
        { key: "spreads", outcomes: [{ name: home, point: homeSpread }, { name: away, point: -homeSpread }] },
        { key: "totals", outcomes: [{ name: "Over", point: total }, { name: "Under", point: total }] },
      ],
    },
  ],
});

describe("odds math", () => {
  it("implied prob matches known American odds", () => {
    expect(impliedProb(-150)).toBeCloseTo(0.6, 2);
    expect(impliedProb(100)).toBeCloseTo(0.5, 2);
    expect(impliedProb(200)).toBeCloseTo(0.3333, 3);
  });
  it("decimal <-> american round-trips", () => {
    expect(toDecimal(-200)).toBeCloseTo(1.5, 3);
    expect(toDecimal(150)).toBeCloseTo(2.5, 3);
    expect(toAmerican(2.5)).toBe(150);
    expect(toAmerican(1.5)).toBe(-200);
  });
});

describe("normalizeEvents", () => {
  it("collapses a book to a consensus game and picks the favorite", () => {
    const [g] = normalizeEvents([ev("e1", "KC", "BAL", -3.5, 47.5, -180, 155)]);
    expect(g.favorite).toBe("KC");
    expect(g.underdog).toBe("BAL");
    expect(g.spread).toBe(3.5);
    expect(g.total).toBe(47.5);
    expect(g.favMoneyline).toBe(-180);
    expect(g.favWinProb).toBeGreaterThan(0.5);
  });

  it("medians spread/total across multiple books", () => {
    const raw: RawEvent = {
      id: "e2",
      home_team: "SF",
      away_team: "SEA",
      bookmakers: [
        { key: "dk", markets: [{ key: "spreads", outcomes: [{ name: "SF", point: -6.5 }] }, { key: "totals", outcomes: [{ name: "Over", point: 44 }] }] },
        { key: "fd", markets: [{ key: "spreads", outcomes: [{ name: "SF", point: -7.5 }] }, { key: "totals", outcomes: [{ name: "Over", point: 45 }] }] },
      ],
    };
    const [g] = normalizeEvents([raw]);
    expect(g.spread).toBe(7); // median(6.5, 7.5)
    expect(g.total).toBe(44.5);
    expect(g.favorite).toBe("SF");
  });

  it("degrades on junk / marketless events", () => {
    expect(normalizeEvents(null)).toEqual([]);
    expect(normalizeEvents([])).toEqual([]);
    expect(normalizeEvents([{ id: "x", home_team: "A", away_team: "B", bookmakers: [] }])).toEqual([]);
  });
});

describe("derived views", () => {
  const games = normalizeEvents([
    ev("e1", "KC", "BAL", -7.5, 45, -320, 260), // strong favorite
    ev("e2", "SF", "SEA", -1.5, 51, -120, 100), // shootout, near coin-flip
    ev("e3", "BUF", "MIA", -3.5, 43, -175, 150),
  ]);

  it("biggestBets ranks by favorite conviction", () => {
    expect(biggestBets(games)[0].favorite).toBe("KC");
  });
  it("topTotals ranks by over/under", () => {
    expect(topTotals(games)[0].total).toBe(51);
  });
  it("chalkParlay multiplies legs into combined odds + prob", () => {
    const p = chalkParlay(games, 3)!;
    expect(p.legs).toHaveLength(3);
    expect(p.combinedProb).toBeLessThan(games[0].favWinProb); // product shrinks
    expect(p.decimal).toBeGreaterThan(1);
    expect(Number.isFinite(p.american)).toBe(true);
  });
  it("chalkParlay returns null without enough legs", () => {
    expect(chalkParlay(normalizeEvents([ev("only", "KC", "BAL", -3, 44, -150, 130)]), 3)).toBeNull();
  });
});
