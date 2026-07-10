import { describe, it, expect, vi, afterEach } from "vitest";
import { rateLimit, verifyFallback, humanCheck, verifyHCaptcha } from "./botDefense";

describe("rateLimit", () => {
  afterEach(() => vi.useRealTimers());

  it("allows up to max then blocks within the window", () => {
    const key = `t:${Math.random()}`;
    for (let i = 0; i < 3; i++) expect(rateLimit(key, 3, 60_000)).toBe(true);
    expect(rateLimit(key, 3, 60_000)).toBe(false);
  });
  it("resets after the window elapses", () => {
    vi.useFakeTimers();
    const key = `t:${Math.random()}`;
    expect(rateLimit(key, 1, 60_000)).toBe(true);
    expect(rateLimit(key, 1, 60_000)).toBe(false); // blocked within window
    vi.advanceTimersByTime(60_001);
    expect(rateLimit(key, 1, 60_000)).toBe(true); // window elapsed → allowed again
  });
});

describe("verifyFallback", () => {
  const ok = { honeypot: "", a: 3, b: 4, answer: 7, elapsedMs: 3000 };
  it("accepts a correct, human-paced answer", () => {
    expect(verifyFallback(ok)).toBe(true);
  });
  it("rejects a filled honeypot", () => {
    expect(verifyFallback({ ...ok, honeypot: "bot" })).toBe(false);
  });
  it("rejects an instant submit (bot timing)", () => {
    expect(verifyFallback({ ...ok, elapsedMs: 200 })).toBe(false);
  });
  it("rejects a wrong answer", () => {
    expect(verifyFallback({ ...ok, answer: 8 })).toBe(false);
  });
  it("rejects missing input", () => {
    expect(verifyFallback(undefined)).toBe(false);
  });
});

describe("verifyHCaptcha (server-side token verification)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("skips (passes) when HCAPTCHA_SECRET is not configured — degrade, don't block", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    expect(await verifyHCaptcha("any-token", {})).toBe(true);
    expect(fetchSpy).not.toHaveBeenCalled(); // no network when unconfigured
  });
  it("rejects a missing token when the secret IS configured", async () => {
    expect(await verifyHCaptcha(undefined, { HCAPTCHA_SECRET: "s" })).toBe(false);
  });
  it("verifies the token against siteverify and returns its success flag", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ success: true }), { status: 200 }),
    );
    expect(await verifyHCaptcha("good", { HCAPTCHA_SECRET: "s" })).toBe(true);
  });
  it("returns false when siteverify reports failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ success: false }), { status: 200 }),
    );
    expect(await verifyHCaptcha("bad", { HCAPTCHA_SECRET: "s" })).toBe(false);
  });
});

describe("humanCheck", () => {
  it("passes the fallback when no hCaptcha secret is configured", async () => {
    const fb = { honeypot: "", a: 1, b: 2, answer: 3, elapsedMs: 3000 };
    expect(await humanCheck({ fallback: fb }, {})).toBe(true);
  });
  it("allows an empty check only when hCaptcha is not configured", async () => {
    expect(await humanCheck({}, {})).toBe(true);
    expect(await humanCheck({}, { HCAPTCHA_SECRET: "x" })).toBe(false);
  });
});
