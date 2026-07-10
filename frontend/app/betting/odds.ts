import { normalizeEvents, type Game } from "./aggregate";

// Server-side betting-market fetch (E5). Reads the live free-tier slate straight
// from The Odds API using the SERVER key `ODDS_API_KEY`. No key → `{configured:
// false}` and the page renders a graceful empty state — never an error, never a
// client-exposed key.
const SPORT = "americanfootball_nfl";
const URL = `https://api.the-odds-api.com/v4/sports/${SPORT}/odds`;

export interface MarketsResult {
  configured: boolean; // is ODDS_API_KEY present?
  games: Game[];
  error?: string;
}

export async function getBettingMarkets(): Promise<MarketsResult> {
  const key = process.env.ODDS_API_KEY;
  if (!key) return { configured: false, games: [] };

  const qs = new URLSearchParams({
    apiKey: key,
    regions: "us",
    markets: "h2h,spreads,totals",
    oddsFormat: "american",
  });
  try {
    // Odds drift slowly relative to a page view; cache 10 min to protect the
    // ~500 req/mo free-tier quota.
    const res = await fetch(`${URL}?${qs}`, { next: { revalidate: 600 } });
    if (!res.ok) return { configured: true, games: [], error: `odds api ${res.status}` };
    return { configured: true, games: normalizeEvents(await res.json()) };
  } catch {
    return { configured: true, games: [], error: "odds api unreachable" };
  }
}
