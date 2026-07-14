import type { RosterHealth, HealthStatus } from "./rosterHealth";

const DOT: Record<HealthStatus, string> = {
  ok: "#33D17A",
  warn: "#E0A33A",
  crit: "#E0573A",
};

// Live roster-health panel — surfaces the W2 draft invariants VISIBLY (starters
// filled / bye conflicts / K-DST cap) plus the projected starters and the equity
// the last pick added. Prop-driven + static (reduced-motion by construction).
export default function RosterHealthPanel({
  health,
  projectedPoints,
  lastEquity,
}: {
  health: RosterHealth;
  projectedPoints: number;
  lastEquity?: number | null;
}) {
  return (
    <div className="glass p-4">
      <h3 className="mb-3 text-label text-ink-muted">ROSTER HEALTH</h3>
      <ul className="space-y-2">
        {health.invariants.map((inv) => (
          <li key={inv.key} className="flex items-start gap-2 text-body">
            <span
              className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
              style={{ background: DOT[inv.status] }}
              aria-label={inv.status}
            />
            <span className="min-w-0 flex-1">
              <span className="text-ink">{inv.label}</span>
              <span className="mt-0.5 block text-label text-ink-muted">{inv.detail}</span>
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex items-center justify-between border-t border-hairline pt-3 text-label text-ink-muted">
        <span>
          Proj starters <span className="font-mono text-ink">{projectedPoints.toFixed(0)}</span>
        </span>
        {lastEquity != null && lastEquity > 0 && (
          <span title="Equity your last pick added to the starting lineup">
            last pick <span className="font-mono text-accent">+{lastEquity.toFixed(1)}</span>
          </span>
        )}
      </div>
    </div>
  );
}
