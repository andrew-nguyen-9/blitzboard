import { describe, expect, test } from "vitest";
import { isReducedMotion } from "./reducedMotion";

describe("isReducedMotion", () => {
  test("true when the OS prefers reduced motion", () => {
    expect(isReducedMotion(true, null)).toBe(true);
  });

  test("true when the in-app override sets data-motion='reduce' (OS off)", () => {
    expect(isReducedMotion(false, "reduce")).toBe(true);
  });

  test("false when neither signal asks to reduce", () => {
    expect(isReducedMotion(false, null)).toBe(false);
  });

  test("false for a data-motion value that is not 'reduce' (e.g. 'system')", () => {
    // A11ySettings writes 'system' to localStorage but removes the attribute;
    // if an unexpected value ever lands on the attribute it must not reduce.
    expect(isReducedMotion(false, "system")).toBe(false);
  });

  test("either signal alone is sufficient", () => {
    expect(isReducedMotion(true, "system")).toBe(true);
    expect(isReducedMotion(false, "reduce")).toBe(true);
  });
});
