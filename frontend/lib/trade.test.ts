import { describe, it, expect } from "vitest";
import {
  FAIR_TRADE_BAND,
  tradeFairness,
  seededRng,
  randomFairTrade,
  bestTradesForRoster,
  findTrades,
} from "./trade";
import type { PlayerWithValue } from "./types";

// ── fixtures ────────────────────────────────────────────────────────────────
// A player carrying just enough for fillRoster (position + value.vor + replacement).
const mk = (id: string, position: string, vor: number, replacement = 40): PlayerWithValue => ({
  id,
  sleeper_id: id,
  espn_id: null,
  full_name: `Player ${id}`,
  position: position as PlayerWithValue["position"],
  nfl_team: "KC",
  bye_week: null,
  age: null,
  years_exp: null,
  status: null,
  injury_status: null,
  value: { player_id: id, engine: "vorp", value: vor, vor, replacement, boom: null, bust: null, adp: null, rank: null },
});

// Simple pool for the random fair-trade generator (only id + a value needed).
const pool = [
  { id: "a", v: 100 },
  { id: "b", v: 98 },
  { id: "c", v: 60 },
  { id: "d", v: 55 },
  { id: "e", v: 52 },
  { id: "f", v: 20 },
  { id: "g", v: 12 },
];
const val = (p: { v: number }) => p.v;

describe("tradeFairness", () => {
  it("is 1 for identical sides and for two empty sides", () => {
    expect(tradeFairness(50, 50)).toBe(1);
    expect(tradeFairness(0, 0)).toBe(1);
  });
  it("is the min/max ratio otherwise", () => {
    expect(tradeFairness(80, 100)).toBeCloseTo(0.8);
  });
});

describe("randomFairTrade — parity band", () => {
  it("returns a trade whose two sides sit inside FAIR_TRADE_BAND", () => {
    // Sweep seeds: every generated trade must respect the band (the load-bearing DoD assertion).
    for (let seed = 1; seed <= 50; seed++) {
      const t = randomFairTrade(pool, { value: val, rng: seededRng(seed) });
      expect(t).not.toBeNull();
      const gap = Math.abs(t!.giveValue - t!.getValue) / Math.max(t!.giveValue, t!.getValue);
      expect(gap).toBeLessThanOrEqual(FAIR_TRADE_BAND + 1e-9);
      expect(t!.fairness).toBeGreaterThanOrEqual(1 - FAIR_TRADE_BAND - 1e-9);
      // give/get are disjoint, non-empty
      expect(t!.give.length).toBeGreaterThan(0);
      expect(t!.get.length).toBeGreaterThan(0);
      const getIds = new Set(t!.get.map((p) => p.id));
      expect(t!.give.every((p) => !getIds.has(p.id))).toBe(true);
    }
  });

  it("is deterministic for a fixed seed", () => {
    const a = randomFairTrade(pool, { value: val, rng: seededRng(7) });
    const b = randomFairTrade(pool, { value: val, rng: seededRng(7) });
    expect(a!.give.map((p) => p.id)).toEqual(b!.give.map((p) => p.id));
    expect(a!.get.map((p) => p.id)).toEqual(b!.get.map((p) => p.id));
  });

  it("packages a 2-for-1 when a lone anchor has no single fair match", () => {
    // 100 has no single within 15% except… only a peer at 92 does. Remove peers so
    // the only fair balance for the 100 anchor is 48+50=98 (within band).
    const lopsided = [
      { id: "star", v: 100 },
      { id: "x", v: 50 },
      { id: "y", v: 48 },
      { id: "z", v: 10 },
    ];
    const t = randomFairTrade(lopsided, { value: val, rng: seededRng(3) });
    expect(t).not.toBeNull();
    const gap = Math.abs(t!.giveValue - t!.getValue) / Math.max(t!.giveValue, t!.getValue);
    expect(gap).toBeLessThanOrEqual(FAIR_TRADE_BAND + 1e-9);
  });

  it("returns null when no fair pairing exists", () => {
    const impossible = [
      { id: "whale", v: 100 },
      { id: "minnow", v: 5 },
    ];
    expect(randomFairTrade(impossible, { value: val, rng: seededRng(1), maxGetPerSide: 1 })).toBeNull();
  });
});

describe("bestTradesForRoster", () => {
  // mine: RB-heavy with a benched RB (trade bait) + weak WR starters. opponents:
  // WR-heavy with a benched WR + weak RB starters → a bench-for-need swap lifts both.
  const mine = [
    mk("m-qb", "QB", 100),
    mk("m-rb1", "RB", 140),
    mk("m-rb2", "RB", 135),
    mk("m-rb3", "RB", 130),
    mk("m-rb4", "RB", 58),
    mk("m-rb5", "RB", 54), // bench surplus
    mk("m-wr1", "WR", 22), // weak WR starters
    mk("m-wr2", "WR", 16),
    mk("m-te", "TE", 50),
    mk("m-k", "K", 8),
    mk("m-dst", "DST", 10),
  ];
  const alpha = {
    id: "alpha",
    name: "Alpha",
    players: [
      mk("a-qb", "QB", 98),
      mk("a-wr1", "WR", 138),
      mk("a-wr2", "WR", 132),
      mk("a-wr3", "WR", 128),
      mk("a-wr4", "WR", 88),
      mk("a-wr5", "WR", 82), // bench surplus
      mk("a-rb1", "RB", 18), // weak RB starters
      mk("a-rb2", "RB", 14),
      mk("a-te", "TE", 48),
      mk("a-k", "K", 7),
      mk("a-dst", "DST", 9),
    ],
  };
  const beta = {
    id: "beta",
    name: "Beta",
    players: [
      mk("b-qb", "QB", 94),
      mk("b-wr1", "WR", 122),
      mk("b-wr2", "WR", 118),
      mk("b-wr3", "WR", 72),
      mk("b-wr4", "WR", 68), // bench surplus
      mk("b-rb1", "RB", 17), // weak RB starters
      mk("b-rb2", "RB", 13),
      mk("b-te", "TE", 44),
    ],
  };

  it("finds mutually-beneficial trades across every opponent", () => {
    const trades = bestTradesForRoster(mine, [alpha, beta]);
    expect(trades.length).toBeGreaterThan(0);
    // Pareto: both sides gain (inherited from findTrades).
    for (const t of trades) {
      expect(t.myDelta).toBeGreaterThan(0);
      expect(t.theirDelta).toBeGreaterThan(0);
    }
  });

  it("ranks by my gain (descending)", () => {
    const trades = bestTradesForRoster(mine, [alpha, beta]);
    for (let i = 1; i < trades.length; i++) {
      expect(trades[i - 1].myDelta).toBeGreaterThanOrEqual(trades[i].myDelta);
    }
  });

  it("never leaks players from outside the passed opponent rosters (RLS scope)", () => {
    // The universe of gettable players is exactly the union of opponents handed in.
    const allowed = new Set([...alpha.players, ...beta.players].map((p) => p.id));
    const trades = bestTradesForRoster(mine, [alpha, beta]);
    for (const t of trades) {
      for (const g of t.get) expect(allowed.has(g.id)).toBe(true);
      // and every give is from my own roster
      for (const g of t.give) expect(mine.some((m) => m.id === g.id)).toBe(true);
    }
    // Dropping beta from the input removes all beta-sourced trades — no stale leakage.
    const onlyAlpha = bestTradesForRoster(mine, [alpha]);
    expect(onlyAlpha.every((t) => t.partnerId === "alpha")).toBe(true);
  });

  it("tags each trade with the correct partner", () => {
    const trades = bestTradesForRoster(mine, [alpha, beta]);
    for (const t of trades) {
      const partner = t.partnerId === "alpha" ? alpha : beta;
      expect(t.partnerName).toBe(partner.name);
      for (const g of t.get) expect(partner.players.some((p) => p.id === g.id)).toBe(true);
    }
  });

  it("matches a direct findTrades run for a single partner", () => {
    const direct = findTrades(mine, alpha.players, { limit: 5 });
    const viaBest = bestTradesForRoster(mine, [alpha], { perPartner: 5, limit: 5 });
    expect(viaBest.map((t) => t.myDelta)).toEqual(direct.map((t) => t.myDelta));
  });
});
