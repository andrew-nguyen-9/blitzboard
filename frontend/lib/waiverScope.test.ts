import { describe, it, expect } from "vitest";
import { freeAgentsOnWaivers, newsForTargets } from "./waiverScope";
import type { WaiverTarget, NewsItem } from "./queries";

const t = (id: string, full_name: string): WaiverTarget => ({
  player_id: id, full_name, position: "WR", nfl_team: "BUF", injury_status: null,
  trend_score: 0.5, sentiment_avg: 0, sleeper_adds: 0, sleeper_drops: 0, vor: null,
});

describe("freeAgentsOnWaivers", () => {
  it("drops rostered players", () => {
    const out = freeAgentsOnWaivers([t("a", "Khalil Shakir"), t("b", "Keon Coleman")], ["a"]);
    expect(out.map((x) => x.player_id)).toEqual(["b"]);
  });
  it("returns all when no rosters synced (degrade, never empty)", () => {
    const all = [t("a", "Khalil Shakir")];
    expect(freeAgentsOnWaivers(all, [])).toEqual(all);
  });
});

describe("newsForTargets", () => {
  const news: NewsItem[] = [
    { title: "Khalil Shakir trending up", source: "x", url: null, sentiment: 1, injury_flag: false, opportunity_flag: true, published_at: null },
    { title: "Unrelated headline", source: "x", url: null, sentiment: 0, injury_flag: false, opportunity_flag: false, published_at: null },
  ];
  it("keeps only headlines mentioning a target name token", () => {
    expect(newsForTargets(news, [t("a", "Khalil Shakir")]).map((n) => n.title)).toEqual([
      "Khalil Shakir trending up",
    ]);
  });
});
