import { describe, it, expect } from "vitest";
import { safeNext } from "./redirect";

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
