import { describe, it, expect } from "vitest";
import { parsePrefs } from "./prefs";

describe("parsePrefs", () => {
  it("fills defaults from empty input", () => {
    expect(parsePrefs({})).toEqual({ theme: "dark", reducedMotion: false });
  });
  it("accepts valid values", () => {
    expect(parsePrefs({ theme: "light", reducedMotion: true })).toEqual({
      theme: "light",
      reducedMotion: true,
    });
  });
  it("coerces legacy/invalid theme to dark", () => {
    expect(parsePrefs({ theme: "system" }).theme).toBe("dark");
    expect(parsePrefs({ theme: "neon" }).theme).toBe("dark");
  });
  it("rejects unknown keys", () => {
    expect(() => parsePrefs({ isAdmin: true })).toThrow();
  });
});
