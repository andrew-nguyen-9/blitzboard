import { describe, it, expect } from "vitest";
import { credentialInput, sleeperLeagueId, sleeperUsername, validate, isSameOrigin } from "./validation";

describe("credentialInput", () => {
  it("accepts a valid platform + secret", () => {
    const r = validate(credentialInput, { platform: "espn", secret: "espn_s2=abc; SWID={x}" });
    expect(r.ok).toBe(true);
  });
  it("rejects an empty secret", () => {
    const r = validate(credentialInput, { platform: "espn", secret: "" });
    expect(r.ok).toBe(false);
  });
  it("rejects an unknown platform", () => {
    const r = validate(credentialInput, { platform: "yahoo", secret: "x" });
    expect(r.ok).toBe(false);
  });
});

describe("sleeper id/username schemas", () => {
  it("accepts a numeric league id, rejects non-numeric", () => {
    expect(validate(sleeperLeagueId, "1234567890").ok).toBe(true);
    expect(validate(sleeperLeagueId, "abc; drop table").ok).toBe(false);
  });
  it("accepts alnum usernames, rejects injection-y input", () => {
    expect(validate(sleeperUsername, "example_99").ok).toBe(true);
    expect(validate(sleeperUsername, "a b/../x").ok).toBe(false);
  });
});

describe("isSameOrigin (CSRF guard)", () => {
  const mk = (h: Record<string, string>) => ({ headers: { get: (n: string) => h[n.toLowerCase()] ?? null } });
  it("allows a same-host origin", () => {
    expect(isSameOrigin(mk({ origin: "https://app.example.com", host: "app.example.com" }))).toBe(true);
  });
  it("rejects a cross-site origin", () => {
    expect(isSameOrigin(mk({ origin: "https://evil.com", host: "app.example.com" }))).toBe(false);
  });
  it("allows a missing origin (same-site nav / server action)", () => {
    expect(isSameOrigin(mk({ host: "app.example.com" }))).toBe(true);
  });
});
