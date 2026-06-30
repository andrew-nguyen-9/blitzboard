import { describe, expect, it } from "vitest";
import { compareCells } from "@/lib/playerSort";

describe("compareCells", () => {
  it("orders numbers by direction", () => {
    expect(compareCells(1, 2, true)).toBeLessThan(0);
    expect(compareCells(1, 2, false)).toBeGreaterThan(0);
  });
  it("orders strings by locale, direction-aware", () => {
    expect(compareCells("a", "b", true)).toBeLessThan(0);
    expect(compareCells("a", "b", false)).toBeGreaterThan(0);
  });
  it("sorts null last regardless of direction", () => {
    expect(compareCells(null, 5, true)).toBe(1);
    expect(compareCells(null, 5, false)).toBe(1);
    expect(compareCells(5, null, true)).toBe(-1);
    expect(compareCells(null, null, true)).toBe(0);
  });
});
