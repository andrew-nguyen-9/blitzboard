import { describe, it, expect } from "vitest";
import { applyInjury, type ScenarioPlayer } from "./whatif";

const roster: ScenarioPlayer[] = [
  { id: "wr1", name: "Alpha", team: "KC", position: "WR", proj: 18 },
  { id: "wr2", name: "Bravo", team: "KC", position: "WR", proj: 9 },
  { id: "wr3", name: "Charlie", team: "KC", position: "WR", proj: 3 },
  { id: "wrX", name: "Delta", team: "BUF", position: "WR", proj: 12 }, // other team
  { id: "rb1", name: "Echo", team: "KC", position: "RB", proj: 14 }, // other position
];

describe("applyInjury", () => {
  it("zeroes the injured player and redistributes his share to same-team, same-position mates", () => {
    const deltas = applyInjury(roster, "wr1", 0.6); // pool = 18 * 0.6 = 10.8
    const inj = deltas.find((d) => d.id === "wr1")!;
    expect(inj.after).toBe(0);
    expect(inj.delta).toBe(-18);

    // beneficiaries wr2 (weight 9) + wr3 (weight 3) → 3:1 split of 10.8
    const wr2 = deltas.find((d) => d.id === "wr2")!;
    const wr3 = deltas.find((d) => d.id === "wr3")!;
    expect(wr2.delta).toBeCloseTo(8.1, 6);
    expect(wr3.delta).toBeCloseTo(2.7, 6);
    // conservation: gained share equals the pool
    expect(wr2.delta + wr3.delta).toBeCloseTo(10.8, 6);
  });

  it("never touches other teams or other positions", () => {
    const ids = applyInjury(roster, "wr1").map((d) => d.id);
    expect(ids).not.toContain("wrX");
    expect(ids).not.toContain("rb1");
  });

  it("returns the injured player sorted first (largest swing) and empty for unknown ids", () => {
    expect(applyInjury(roster, "wr1")[0].id).toBe("wr1");
    expect(applyInjury(roster, "nope")).toEqual([]);
  });
});
