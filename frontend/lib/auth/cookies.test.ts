import { describe, it, expect } from "vitest";
import { AUTH_COOKIE_OPTIONS } from "./cookies";

describe("AUTH_COOKIE_OPTIONS", () => {
  it("is httpOnly, SameSite=Lax, path=/", () => {
    expect(AUTH_COOKIE_OPTIONS.httpOnly).toBe(true);
    expect(AUTH_COOKIE_OPTIONS.sameSite).toBe("lax");
    expect(AUTH_COOKIE_OPTIONS.path).toBe("/");
  });
});
