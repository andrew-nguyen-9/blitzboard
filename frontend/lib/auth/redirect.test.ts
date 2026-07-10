import { describe, it, expect } from "vitest";
import { safeNext, isProtectedPath, resolveAuthOrigin } from "./redirect";

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

describe("resolveAuthOrigin", () => {
  const internal = "http://localhost:3000"; // what request.url reports behind a proxy

  it("honors the forwarded host/proto in production (avoids the internal origin)", () => {
    const got = resolveAuthOrigin(
      internal,
      { forwardedHost: "blitzboard.app", forwardedProto: "https" },
      { NODE_ENV: "production" },
    );
    expect(got).toBe("https://blitzboard.app");
  });
  it("defaults the proto to https when only the host is forwarded", () => {
    expect(
      resolveAuthOrigin(internal, { forwardedHost: "blitzboard.app" }, { NODE_ENV: "production" }),
    ).toBe("https://blitzboard.app");
  });
  it("falls back to NEXT_PUBLIC_SITE_URL when no forwarded host", () => {
    expect(
      resolveAuthOrigin(internal, {}, { NODE_ENV: "production", NEXT_PUBLIC_SITE_URL: "https://bb.io" }),
    ).toBe("https://bb.io");
  });
  it("uses the raw origin in development (no proxy)", () => {
    expect(
      resolveAuthOrigin(internal, { forwardedHost: "blitzboard.app" }, { NODE_ENV: "development" }),
    ).toBe(internal);
  });
  it("uses the raw origin when nothing else is configured", () => {
    expect(resolveAuthOrigin(internal, {}, { NODE_ENV: "production" })).toBe(internal);
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
