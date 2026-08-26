import { describe, expect, it } from "vitest";
import { ceilingWeeks, DEFAULT_POLICY } from "./draftAI";
import type { PlayerWithValue } from "./types";

describe("C01 player-value unit contracts", () => {
  it.fails("compares a raw projection ceiling with a raw starter projection", () => {
    const candidate = {
      id: "candidate",
      full_name: "candidate",
      position: "RB",
      metadata: {},
      value: {
        player_id: "candidate",
        engine: "vorp",
        value: 100,
        vor: 100,
        replacement: 100,
        // Current wire meaning: raw ceiling 250 minus replacement 100.
        boom: 150,
        bust: 50,
        adp: null,
        rank: null,
      },
    } as PlayerWithValue;

    // Raw ceiling 250 exceeds the raw starter projection 180, so option value is positive.
    // The current consumer compares ceiling-VOR 150 with raw projection 180 and returns zero.
    expect(ceilingWeeks(candidate, 180, DEFAULT_POLICY)).toBeGreaterThan(0);
  });
});
