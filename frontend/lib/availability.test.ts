import { describe, expect, it } from "vitest";
import { availabilityOf, ZERO_AVAILABILITY_EPS } from "./availability";
import type { PlayerWithValue } from "./types";

function player(overrides: Partial<PlayerWithValue> = {}): PlayerWithValue {
  return {
    id: "p1",
    sleeper_id: "p1",
    espn_id: null,
    full_name: "Player One",
    position: "K",
    nfl_team: "KC",
    bye_week: null,
    age: null,
    years_exp: null,
    status: "Active",
    injury_status: null,
    ...overrides,
  };
}

describe("availabilityOf", () => {
  it.each(["Inactive", "Retired", "non_roster", "cut"])(
    "treats a %s player as unavailable even when a stale team remains",
    (status) => {
      expect(availabilityOf(player({ status }))).toBeLessThan(ZERO_AVAILABILITY_EPS);
    },
  );

  it("keeps an active rostered player fully available", () => {
    expect(availabilityOf(player())).toBe(1);
  });
});
