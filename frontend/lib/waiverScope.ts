// Pure helpers for the authed waiver scope (Epic 8). "Free agents on waivers" = trending players
// not already rostered in the active league. News can refocus to those FA names. Kept framework-
// free + tested so the scope logic has one runnable check.
import type { WaiverTarget, NewsItem } from "./queries";

// Players on waivers = trending targets whose id is NOT in the league's rostered set.
// Empty rostered set (no league sync) → returns all targets (degrade to all-NFL, never empty).
export function freeAgentsOnWaivers(targets: WaiverTarget[], rosteredIds: Iterable<string>): WaiverTarget[] {
  const taken = new Set(rosteredIds);
  if (taken.size === 0) return targets;
  return targets.filter((t) => !taken.has(t.player_id));
}

// News scoped to the on-waivers players: keep headlines mentioning an FA name token (≥4 chars).
// ponytail: name-token match (NewsItem has no player_id); upgrade = a player_id join on news.
export function newsForTargets(news: NewsItem[], targets: WaiverTarget[]): NewsItem[] {
  const names = targets.flatMap((t) =>
    t.full_name.toLowerCase().split(" ").filter((w) => w.length >= 4),
  );
  if (!names.length) return news;
  const hits = news.filter((n) => names.some((nm) => n.title.toLowerCase().includes(nm)));
  return hits;
}
