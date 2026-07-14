import { describe, it, expect } from "vitest";
import { reasonChips } from "./reasons";

describe("reasonChips", () => {
  it("maps the four brief dimensions and orders need first", () => {
    const chips = reasonChips({ need: true, vona: true, scarce: true, run: true });
    expect(chips.map((c) => c.key)).toEqual(["need", "vona", "scarce", "run"]);
    expect(chips.every((c) => c.label && c.title)).toBe(true);
  });

  it("falls back to a best-value chip when no signal fires", () => {
    const chips = reasonChips({});
    expect(chips).toHaveLength(1);
    expect(chips[0].label).toBe("best value");
  });

  it("includes ADP value and upside when flagged", () => {
    const keys = reasonChips({ value: true, upside: true }).map((c) => c.key);
    expect(keys).toContain("value");
    expect(keys).toContain("upside");
  });
});
