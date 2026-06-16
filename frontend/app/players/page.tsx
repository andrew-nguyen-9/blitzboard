import EmptyState from "@/components/EmptyState";
import PlayerTable from "@/components/PlayerTable";
import EngineToggle from "@/components/EngineToggle";
import { getAllPlayersByValue, getPlayers, getRosteredIds, getTrendingMap } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import type { Engine } from "@/lib/types";

export const metadata = { title: "Player Explorer" };
export const dynamic = "force-dynamic";

// Player Explorer: the FULL ranked universe (paginated past the 1000-row cap),
// searchable/sortable, with positional tiers, ADP, byes, and a free-agent filter.
export default async function PlayersPage({
  searchParams,
}: {
  searchParams: Promise<{ engine?: string }>;
}) {
  const { engine: engineParam } = await searchParams;
  const engine: Engine = engineParam === "monte_carlo" ? "monte_carlo" : "vorp";

  const live = isSupabaseConfigured();
  const [ranked, rosteredIds, trending] = live
    ? await Promise.all([getAllPlayersByValue(engine), getRosteredIds(), getTrendingMap()])
    : [[], new Set<string>(), {}];
  const players = ranked.length ? ranked : live ? await getPlayers({ limit: 1000 }) : [];

  if (!players.length) {
    return (
      <EmptyState title="Player Explorer" phase="Phase 1">
        {live
          ? "Backend connected, but no players yet. Run pipeline/player_ingest.py, then value_engine_run.py."
          : "No backend configured yet. Set NEXT_PUBLIC_SUPABASE_* and run the Sleeper ingest to light this up."}
      </EmptyState>
    );
  }

  return (
    <div className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Player Explorer</h1>
          <p className="mt-2 text-body text-ink-muted">
            {players.length.toLocaleString()} players · tiered, future-value model · superflex-aware
          </p>
        </div>
        <EngineToggle active={engine} />
      </div>

      <div className="mt-8">
        <PlayerTable
          players={players}
          rosteredIds={rosteredIds.size ? rosteredIds : undefined}
          trending={trending}
        />
      </div>
    </div>
  );
}
