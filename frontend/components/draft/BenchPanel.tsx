import type { BenchHealth, DropRank } from "@/lib/benchScore";
import type { BenchPanelEntry } from "@/lib/types";
import type { HealthStatus } from "./rosterHealth";

// Same DOT palette RosterHealthPanel uses (ok/warn/crit) so the two war-room
// panels read as one system.
const DOT: Record<HealthStatus, string> = {
  ok: "#33D17A",
  warn: "#E0A33A",
  crit: "#E0573A",
};

// Bench value 0-100 → a health band. Deep benches with real contingent value sit
// green; a body scoring near replacement is the first to cut (crit).
export function benchBand(score: number): HealthStatus {
  return score >= 55 ? "ok" : score >= 30 ? "warn" : "crit";
}

// dropPriority is already sorted worst→best, so index 0 is the first body to
// drop. Flag it (only when there's a real choice — a lone benchwarmer isn't a cut).
export function buildBenchEntries(drops: DropRank[]): BenchPanelEntry[] {
  return drops.map((d, i) => ({
    id: d.id,
    name: d.player.full_name,
    position: d.player.position === "DEF" ? "DST" : d.player.position ?? "—",
    score: d.score,
    dropFirst: i === 0 && drops.length > 1,
  }));
}

// Human labels for the benchScore term names carried in `coverage` (degraded /
// neutral-filled signals). Falls back to a spaced-out camelCase split.
const SIGNAL_LABELS: Record<string, string> = {
  Upside: "Upside",
  OpportunityTrend: "Opportunity trend",
  Opportunity: "Opportunity",
  HandcuffValue: "Handcuff value",
  PositionalScarcity: "Positional scarcity",
  PlayoffSchedule: "Playoff schedule",
  WeeklyFlexValue: "Weekly flex value",
  WeeklyProj: "Weekly projection",
  ByeCoverage: "Bye coverage",
  ReplacementDifficulty: "Replacement difficulty",
  StartingProb: "Starting prob",
  StartingProbability: "Starting prob",
  JobSecurity: "Job security",
  Schedule: "Schedule",
  TargetShare: "Target share",
  RouteParticipation: "Route participation",
  TradeValue: "Trade value",
};
export function humanizeSignal(term: string): string {
  return SIGNAL_LABELS[term] ?? term.replace(/([a-z])([A-Z])/g, "$1 $2");
}

// War-room Bench panel — surfaces each bench body's BenchScore, the drop order
// (worst first), and a checklist of which scoring signals are degraded (missing
// trends/schedule data → neutral fills). Prop-driven + static, so it's
// reduced-motion-safe by construction (no animation). Mirrors RosterHealthPanel.
export default function BenchPanel({
  health,
  drops,
  superflex,
}: {
  health: BenchHealth;
  drops: DropRank[];
  superflex?: boolean;
}) {
  const entries = buildBenchEntries(drops);

  return (
    <div className="glass p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-label text-ink-muted">BENCH VALUE</h3>
        {superflex && (
          <span className="rounded-full border border-hairline px-2 py-0.5 text-label text-ink-muted">
            superflex
          </span>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="text-label text-ink-muted">No bench players yet.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map((e) => {
            const band = benchBand(e.score);
            return (
              <li key={e.id} className="flex items-center gap-2 text-body">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: DOT[band] }}
                  aria-label={band}
                />
                <span className="min-w-0 flex-1 truncate text-ink">
                  {e.name}
                  <span className="ml-1.5 text-label text-ink-muted">{e.position}</span>
                </span>
                {e.dropFirst && (
                  <span className="text-label text-ink-muted" title="Lowest bench value — first to drop">
                    drop first
                  </span>
                )}
                <span className="font-mono text-ink">{e.score.toFixed(0)}</span>
              </li>
            );
          })}
        </ul>
      )}

      {/* signal checklist — which inputs the bench scores are missing */}
      <div className="mt-3 border-t border-hairline pt-3">
        {entries.length > 0 && (
          <div className="mb-2 flex items-center justify-between text-label text-ink-muted">
            <span>Mean bench value</span>
            <span className="font-mono text-ink">{health.score.toFixed(0)}</span>
          </div>
        )}
        {health.coverage.length === 0 ? (
          <div className="flex items-center gap-2 text-label text-ink-muted">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: DOT.ok }} aria-label="ok" />
            All signals live
          </div>
        ) : (
          <ul className="space-y-1">
            <li className="text-label text-ink-muted">Signals degraded (neutral fill):</li>
            {health.coverage.map((term) => (
              <li key={term} className="flex items-center gap-2 text-label text-ink-muted">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: DOT.warn }} aria-label="warn" />
                {humanizeSignal(term)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
