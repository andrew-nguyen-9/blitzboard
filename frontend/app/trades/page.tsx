import EmptyState from "@/components/EmptyState";
import TradeFinder from "@/components/TradeFinder";
import { getLeagueTeams, getPlayersWithValueByIds } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import type { PlayerWithValue } from "@/lib/types";

export const metadata = { title: "Trade Optimizer" };
export const dynamic = "force-dynamic"; // reflects latest rosters + values

// P5: finds Pareto-improving trades (both lineups improve) between two real
// rosters, need-aware via fillRoster. Rosters come from league_sync (ESPN).
export default async function TradesPage() {
  const live = isSupabaseConfigured();
  const teams = live ? await getLeagueTeams() : [];

  if (teams.length < 2) {
    return (
      <EmptyState title="Trade Optimizer" phase="Phase 5">
        {live
          ? "Need synced rosters. Run pipeline/league_sync.py (ESPN cookies) to pull your league's teams."
          : "Connect Supabase and sync your ESPN league to surface Pareto-improving trades."}
      </EmptyState>
    );
  }

  // hydrate every rostered player (with VORP value) once, pass a lookup to the client
  const allIds = [...new Set(teams.flatMap((t) => t.player_ids))];
  const players = await getPlayersWithValueByIds(allIds);
  const playerMap: Record<string, PlayerWithValue> = Object.fromEntries(
    players.map((p) => [p.id, p]),
  );

  return (
    <div className="py-12">
      <h1 className="font-display text-display-md">Trade Optimizer</h1>
      <p className="mt-2 text-body text-ink-muted">
        Pareto-improving swaps — both lineups get better. Need-aware (superflex roster), ranked by your gain &amp; fairness.
      </p>
      <div className="mt-8">
        <TradeFinder teams={teams} players={playerMap} />
      </div>
    </div>
  );
}
