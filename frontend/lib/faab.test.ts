import { describe, it, expect } from "vitest";
import { faabBid, faabBidRange } from "./faab";

describe("faabBid", () => {
  it("scales with remaining budget at the same demand", () => {
    const a = faabBid({ remainingBudget: 100, trend: 0.8, need: 0.8 });
    const b = faabBid({ remainingBudget: 50, trend: 0.8, need: 0.8 });
    expect(a).toBeGreaterThan(b);
    expect(Math.abs(a - b * 2)).toBeLessThanOrEqual(2); // ~proportional to budget (± rounding)
  });

  it("bids more for a high-trend, high-need target than a low one", () => {
    const hot = faabBid({ remainingBudget: 100, trend: 0.9, need: 0.9, scarcity: 0.9 });
    const cold = faabBid({ remainingBudget: 100, trend: 0.1, need: 0.1, scarcity: 0.1 });
    expect(hot).toBeGreaterThan(cold);
  });

  it("never bids 0 when there is budget, never exceeds the budget", () => {
    expect(faabBid({ remainingBudget: 3, trend: 0, need: 0, scarcity: 0 })).toBeGreaterThanOrEqual(1);
    expect(faabBid({ remainingBudget: 10, trend: 1, need: 1, scarcity: 1 })).toBeLessThanOrEqual(10);
  });

  it("returns 0 with no budget left", () => {
    expect(faabBid({ remainingBudget: 0, trend: 1, need: 1 })).toBe(0);
  });
});

describe("faabBidRange", () => {
  it("brackets the recommendation low ≤ rec ≤ high, all within budget", () => {
    const r = faabBidRange({ remainingBudget: 100, trend: 0.6, need: 0.6 });
    expect(r.low).toBeLessThanOrEqual(r.rec);
    expect(r.rec).toBeLessThanOrEqual(r.high);
    expect(r.high).toBeLessThanOrEqual(100);
    expect(r.low).toBeGreaterThanOrEqual(1);
  });
});
