import { describe, it, expect } from "vitest";
import type { Factor } from "@supabase/supabase-js";
import { needsMfaStepUp, verifiedTotpFactor } from "./mfa";

describe("needsMfaStepUp — TOTP step-up after password sign-in", () => {
  it("aal1 session with an aal2 factor → step up", () => {
    expect(needsMfaStepUp("aal1", "aal2")).toBe(true);
  });
  it("no second factor (next stays aal1) → no step up", () => {
    expect(needsMfaStepUp("aal1", "aal1")).toBe(false);
  });
  it("already at aal2 → no step up (don't re-challenge)", () => {
    expect(needsMfaStepUp("aal2", "aal2")).toBe(false);
  });
  it("null levels (offline/unknown) → no step up", () => {
    expect(needsMfaStepUp(null, null)).toBe(false);
  });
});

const factor = (over: Partial<Factor>): Factor => ({
  id: "f1",
  factor_type: "totp",
  status: "verified",
  created_at: "",
  updated_at: "",
  ...over,
});

describe("verifiedTotpFactor", () => {
  it("returns the verified totp factor", () => {
    const f = factor({ id: "good" });
    expect(verifiedTotpFactor([f])?.id).toBe("good");
  });
  it("ignores unverified totp factors", () => {
    expect(verifiedTotpFactor([factor({ status: "unverified" })])).toBeNull();
  });
  it("ignores non-totp factors", () => {
    expect(verifiedTotpFactor([factor({ factor_type: "phone" })])).toBeNull();
  });
  it("null/empty → null", () => {
    expect(verifiedTotpFactor(null)).toBeNull();
    expect(verifiedTotpFactor([])).toBeNull();
  });
});
