import { describe, it, expect, vi } from "vitest";

const { getSitemapPlayerIds } = vi.hoisted(() => ({ getSitemapPlayerIds: vi.fn() }));
vi.mock("@/lib/queries", () => ({ getSitemapPlayerIds }));

import sitemap from "./sitemap";

describe("sitemap", () => {
  it("emits absolute static routes and DB-enumerated player pages", async () => {
    getSitemapPlayerIds.mockResolvedValue(["abc", "def"]);
    const entries = await sitemap();
    const urls = entries.map((e) => e.url);

    expect(urls).toContain("https://blitzboard.an9.dev/");
    expect(urls).toContain("https://blitzboard.an9.dev/players");
    expect(urls).toContain("https://blitzboard.an9.dev/players/abc");
    expect(urls).toContain("https://blitzboard.an9.dev/players/def");
    // every url is absolute and no private route leaks in
    expect(urls.every((u) => u.startsWith("https://"))).toBe(true);
    expect(urls.some((u) => /\/(account|login|api|kit)/.test(u))).toBe(false);
  });

  it("degrades to static routes only when no keys (empty player list)", async () => {
    getSitemapPlayerIds.mockResolvedValue([]);
    const entries = await sitemap();
    expect(entries).toHaveLength(9); // the 9 static public routes
  });
});
