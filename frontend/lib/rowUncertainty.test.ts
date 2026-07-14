import { describe, expect, it } from "vitest";
import { rowUncertainty } from "./rowUncertainty";
import { rangeFromQuantiles } from "@/components/uncertainty";
import type { SnapshotPlayer } from "./snapshot";

const row = (over: Partial<SnapshotPlayer>): SnapshotPlayer => ({
  id: "1",
  full_name: "Test Player",
  position: "WR",
  nfl_team: "SF",
  value: null,
  vor: null,
  rank: 1,
  predictability: 0.5,
  trend: null,
  adp: null,
  boom: null,
  bust: null,
  bye: null,
  ...over,
});

describe("rowUncertainty", () => {
  it("derives a floor–median–ceiling band from the value row's bust/value/boom", () => {
    const u = rowUncertainty(row({ bust: 8, value: 14, boom: 22 }));
    expect(u).not.toBeNull();
    expect(u!.quantiles.length).toBeGreaterThanOrEqual(3);
    // the band is renderable by the shared RangeBar (P10 < median < P90)
    const range = rangeFromQuantiles(u!.quantiles);
    expect(range).not.toBeNull();
    expect(range!.floor).toBeLessThan(range!.median);
    expect(range!.median).toBeLessThan(range!.ceiling);
  });

  it("returns null when the row carries no outcome band (row omits uncertainty gracefully)", () => {
    expect(rowUncertainty(row({}))).toBeNull();
  });
});
