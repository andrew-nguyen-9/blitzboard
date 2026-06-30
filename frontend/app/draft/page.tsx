import EmptyState from "@/components/EmptyState";
import DraftRoom from "@/components/DraftRoom";
import { getAllPlayersByValue } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import { fetchTeamByes, attachByes } from "@/lib/byeWeeks";

export const metadata = { title: "Draft Board" };

// P2: one board, two pick-input adapters (D7). The OFFLINE MANUAL board is the
// always-works default shown here; ESPN/Sleeper live-sync layers on top later
// and degrades back to this exact board on any feed stall.
export default async function DraftPage() {
  const live = isSupabaseConfigured();
  // Import NFL byes from the schedule and attach by nfl_team (4.5) so the Bye column (4.2) fills
  // and the draft policy's bye-cover term has data. Falls back to a baked snapshot when offline.
  const players = live
    ? attachByes(await getAllPlayersByValue("vorp"), await fetchTeamByes())
    : [];

  if (!players.length) {
    return (
      <EmptyState title="Draft Board" phase="Phase 2">
        {live
          ? "Connected, but no player values yet. Run pipeline/value_engine_run.py to populate the board."
          : "No backend yet. Set Supabase keys and run the pipeline, then the live draft board lights up."}
      </EmptyState>
    );
  }

  return (
    <div className="py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Draft Board</h1>
          <p className="mt-2 text-body text-ink-muted">
            Superflex-aware best-available · manual · Sleeper &amp; ESPN live-sync (auto-fallback to manual)
          </p>
        </div>
        <span
          className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted"
          title="Manual is the always-works default. Sleeper (reliable) + ESPN (best-effort) live-sync layer on top; any feed stall falls back to manual."
        >
          Manual · Sleeper · ESPN
        </span>
      </div>
      <DraftRoom players={players} />
    </div>
  );
}
