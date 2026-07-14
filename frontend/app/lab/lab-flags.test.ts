import { describe, it, expect } from "vitest";
import { labEnabled } from "./lab-flags";

describe("labEnabled — prod-exclusion gate", () => {
  it("is OFF in a production build even when the opt-in flag is set", () => {
    // The load-bearing guarantee: prod excludes the Lab, no matter the flag.
    expect(labEnabled({ NODE_ENV: "production", NEXT_PUBLIC_ENABLE_LAB: "1" })).toBe(false);
  });

  it("is OFF locally until explicitly opted in", () => {
    expect(labEnabled({ NODE_ENV: "development" })).toBe(false);
    expect(labEnabled({ NODE_ENV: "development", NEXT_PUBLIC_ENABLE_LAB: "0" })).toBe(false);
  });

  it("is ON only for a non-prod build with the flag set", () => {
    expect(labEnabled({ NODE_ENV: "development", NEXT_PUBLIC_ENABLE_LAB: "1" })).toBe(true);
    expect(labEnabled({ NODE_ENV: "test", NEXT_PUBLIC_ENABLE_LAB: "1" })).toBe(true);
  });
});
