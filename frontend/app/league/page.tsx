import EmptyState from "@/components/EmptyState";
import { getLeagueOverview } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";

export const metadata = { title: "League Overview" };
export const dynamic = "force-dynamic"; // reflects latest league_sync

// P3: the connected ESPN league — standings + teams. Populated by
// pipeline/league_sync.py (ESPN cookie auth). Read-only enrichment (D1).
export default async function LeaguePage() {
  const live = isSupabaseConfigured();
  const { league, teams } = live ? await getLeagueOverview() : { league: null, teams: [] };

  if (!league || !teams.length) {
    return (
      <EmptyState title="League Overview" phase="Phase 3">
        {live
          ? "League row found but no teams synced yet. Run pipeline/league_sync.py with your ESPN_S2 / ESPN_SWID cookies."
          : "Connect Supabase and run league_sync.py to pull “Smores 2025” — standings, rosters, and settings."}
      </EmptyState>
    );
  }

  const maxPF = Math.max(1, ...teams.map((t) => t.points_for));

  return (
    <div className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-display-md">{league.name ?? "League"}</h1>
          <p className="mt-2 text-body text-ink-muted">
            {league.season} · {teams.length} teams · ESPN league {league.external_id}
          </p>
        </div>
      </div>

      <div className="glass mt-8 overflow-hidden">
        <table className="w-full text-left text-body">
          <thead className="border-b border-hairline text-label text-ink-muted">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Team</th>
              <th className="px-4 py-3">Owner</th>
              <th className="px-4 py-3 text-center">Record</th>
              <th className="px-4 py-3 text-right">PF</th>
              <th className="px-4 py-3 text-right">PA</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((t, i) => (
              <tr key={t.id} className="border-b border-hairline/60 transition hover:bg-surface-elevated">
                <td className="px-4 py-3 font-mono text-ink-muted">{t.standing ?? i + 1}</td>
                <td className="px-4 py-3 font-medium">
                  {t.team_name ?? t.abbrev ?? "—"}
                  {t.division && <span className="ml-2 text-label text-ink-muted">{t.division}</span>}
                </td>
                <td className="px-4 py-3 text-ink-muted">{t.owner ?? "—"}</td>
                <td className="px-4 py-3 text-center font-mono">
                  {t.wins}-{t.losses}{t.ties ? `-${t.ties}` : ""}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-hairline sm:block">
                      <div className="h-full rounded-full bg-accent" style={{ width: `${(t.points_for / maxPF) * 100}%` }} />
                    </div>
                    <span className="font-mono text-accent">{t.points_for.toFixed(0)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono text-ink-muted">{t.points_against.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
