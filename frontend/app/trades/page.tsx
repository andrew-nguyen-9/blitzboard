import TradeCalculator from "@/components/TradeCalculator";
import TradeFinder from "@/components/TradeFinder";
import { getRecentNews, getLeagueTeams, getPlayersWithValueByIds } from "@/lib/queries";
import type { PlayerWithValue } from "@/lib/types";
import { getMyLeagues } from "@/lib/queries.auth";
import { isSupabaseConfigured } from "@/lib/supabase";

export const metadata = { title: "Trade Calculator" };
export const dynamic = "force-dynamic"; // news refreshes; never serve stale

// Epic 10 (unauth): the public trade calculator — search the all-NFL player
// snapshot, stack both sides, compare by value, plus a 🎲 fair-trade button that
// generates a balanced swap within the parity band. No league context.
// Authed (E7): a "Your best trades" finder scans the user's league for the top
// Pareto-improving deals across their roster + positional needs.
//
// RLS / authz check point: getMyLeagues() runs through getServerSupabase() (anon key
// + the caller's session cookie → auth.uid()), so the authed section only renders for a
// signed-in user with a connected league — a signed-out request gets an empty list and
// never reaches the roster hydration below. bestTradesForRoster only ever searches the
// `teams` handed to it, so nothing outside the league's rosters can surface.
export default async function TradesPage() {
  const live = isSupabaseConfigured();
  const [news, myLeagues] = live ? await Promise.all([getRecentNews(12), getMyLeagues()]) : [[], []];
  const authed = myLeagues.length > 0;

  // Hydrate league rosters with VORP values ONLY for an authenticated user (gate above).
  let teams: Awaited<ReturnType<typeof getLeagueTeams>> = [];
  let playersById: Record<string, PlayerWithValue> = {};
  if (authed) {
    teams = await getLeagueTeams();
    const ids = [...new Set(teams.flatMap((t) => t.player_ids))];
    if (ids.length) {
      const hydrated = await getPlayersWithValueByIds(ids);
      playersById = Object.fromEntries(hydrated.map((p) => [p.id, p]));
    }
  }

  return (
    <div className="space-y-12 py-12">
      <TradeCalculator news={news} leagues={myLeagues.map((l) => ({ id: l.id, name: l.name ?? "League" }))} />

      {authed && teams.length > 0 && (
        <section aria-labelledby="best-trades">
          <h2 id="best-trades" className="font-display text-display-md">Your best trades</h2>
          <p className="mb-6 mt-2 text-body text-ink-muted">
            Pareto-improving deals across your league — ranked by how much they lift your starting lineup,
            need-aware so a swap that fills a hole beats pure point-chasing.
          </p>
          <TradeFinder teams={teams} players={playersById} />
        </section>
      )}
    </div>
  );
}
