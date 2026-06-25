import { describe, it, expect } from "vitest";
import { parsePrefs } from "./prefs";

describe("parsePrefs", () => {
  it("fills defaults from empty input", () => {
    expect(parsePrefs({})).toEqual({ theme: "system", reducedMotion: false });
  });
  it("accepts valid values", () => {
    expect(parsePrefs({ theme: "dark", reducedMotion: true })).toEqual({
      theme: "dark",
      reducedMotion: true,
    });
  });
  it("rejects an invalid theme", () => {
    expect(() => parsePrefs({ theme: "neon" })).toThrow();
  });
  it("rejects unknown keys", () => {
    expect(() => parsePrefs({ isAdmin: true })).toThrow();
  });
});
