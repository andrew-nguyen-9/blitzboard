import { describe, it, expect, vi, afterEach } from "vitest";
import { rateLimit, verifyFallback, humanCheck } from "./botDefense";

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
