import { describe, it, expect } from "vitest";
import { safeNext, isProtectedPath } from "./redirect";

describe("safeNext", () => {
  it("passes through a same-origin path", () => {
    expect(safeNext("/players")).toBe("/players");
  });
  it("rejects protocol-relative and absolute URLs", () => {
    expect(safeNext("//evil.com")).toBe("/");
    expect(safeNext("https://evil.com")).toBe("/");
    expect(safeNext("/\\evil.com")).toBe("/");
  });
  it("defaults empty/nullish to /", () => {
    expect(safeNext(null)).toBe("/");
    expect(safeNext("")).toBe("/");
    expect(safeNext(undefined)).toBe("/");
  });
});

describe("isProtectedPath", () => {
  it("gates the league page and its subpaths", () => {
    expect(isProtectedPath("/league")).toBe(true);
    expect(isProtectedPath("/league/standings")).toBe(true);
  });
  it("leaves public routes open", () => {
    expect(isProtectedPath("/")).toBe(false);
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/players")).toBe(false);
    expect(isProtectedPath("/leaguex")).toBe(false); // prefix must be a path boundary
  });
});
