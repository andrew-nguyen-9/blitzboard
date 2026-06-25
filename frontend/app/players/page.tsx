import PlayerTable from "@/components/PlayerTable";
import EngineToggle from "@/components/EngineToggle";
import type { Engine } from "@/lib/types";

export const metadata = { title: "Player Explorer" };

// Player Explorer: the FULL ranked universe (no 500 cap), delivered as a
// precomputed CDN snapshot and loaded client-side, then sorted/filtered/searched
// in-memory with virtualized rows. This page is a thin shell; the data lives in
// the client island (PlayerTable → lib/snapshot.ts).
export default async function PlayersPage({
  searchParams,
}: {
  searchParams: Promise<{ engine?: string }>;
}) {
  const { engine: engineParam } = await searchParams;
  const engine: Engine = engineParam === "monte_carlo" ? "monte_carlo" : "vorp";

  return (
    <div className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Player Explorer</h1>
          <p className="mt-2 text-body text-ink-muted">
            The full player universe · tiered, future-value model · superflex-aware
          </p>
        </div>
        <EngineToggle active={engine} />
      </div>

      <div className="mt-8">
        <PlayerTable engine={engine} />
      </div>
    </div>
  );
}
