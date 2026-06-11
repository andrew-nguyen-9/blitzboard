import EmptyState from "@/components/EmptyState";
import PlayerTable from "@/components/PlayerTable";
import EngineToggle from "@/components/EngineToggle";
import { getPlayers, getPlayersByValue } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import type { Engine } from "@/lib/types";

export const metadata = { title: "Player Explorer" };

// P1 surface: ranked, searchable, sortable player board. Renders an empty state
// until the backend + ingest are live; once values exist it shows the real board.
export default async function PlayersPage({
  searchParams,
}: {
  searchParams: Promise<{ engine?: string }>;
}) {
  const { engine: engineParam } = await searchParams;
  const engine: Engine = engineParam === "monte_carlo" ? "monte_carlo" : "vorp";

  const live = isSupabaseConfigured();
  const ranked = live ? await getPlayersByValue(engine, 300) : [];
  // fall back to the raw universe (no values yet) so the board still renders
  const players = ranked.length ? ranked : live ? await getPlayers({ limit: 300 }) : [];

  if (!players.length) {
    return (
      <EmptyState title="Player Explorer" phase="Phase 1">
        {live
          ? "Backend connected, but no players yet. Run pipeline/player_ingest.py, then value_engine_run.py to populate values."
          : "No backend configured yet. Set NEXT_PUBLIC_SUPABASE_* and run the Sleeper ingest to light this up."}
      </EmptyState>
    );
  }

  const hasValues = ranked.length > 0;

  return (
    <div className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Player Explorer</h1>
          <p className="mt-2 text-body text-ink-muted">
            {players.length} players · {hasValues ? "VORP value · superflex-aware" : "universe loaded — values pending"}
          </p>
        </div>
        <EngineToggle active={engine} />
      </div>

      <div className="mt-8">
        <PlayerTable players={players} />
      </div>
    </div>
  );
}
