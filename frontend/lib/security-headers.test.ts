import { describe, it, expect } from "vitest";
import nextConfig from "../next.config.mjs";

// v2.7.2.2 — automatable half of the header scan: the security headers are configured for every
// route and the CSP locks down framing/defaults. (The live securityheaders.com / TLS-HSTS-preload
// check still runs against the deployment.)
async function headersFor() {
  const routes = await nextConfig.headers!();
  return routes[0].headers;
}

describe("security headers", () => {
  it("sets the core security headers on every route", async () => {
    const keys = (await headersFor()).map((h: { key: string }) => h.key);
    for (const k of [
      "Content-Security-Policy",
      "Strict-Transport-Security",
      "X-Content-Type-Options",
      "X-Frame-Options",
      "Referrer-Policy",
      "Permissions-Policy",
    ]) {
      expect(keys).toContain(k);
    }
  });

  it("CSP denies framing and restricts defaults", async () => {
    const csp = (await headersFor()).find((h: { key: string }) => h.key === "Content-Security-Policy")!.value;
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
  });

  it("HSTS is long-lived and preload-eligible", async () => {
    const hsts = (await headersFor()).find((h: { key: string }) => h.key === "Strict-Transport-Security")!.value;
    expect(hsts).toMatch(/max-age=\d{7,}/); // ≥ ~4 months
    expect(hsts).toContain("preload");
  });
});
