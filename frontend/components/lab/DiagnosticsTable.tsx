import {
  rhatStatus,
  essStatus,
  divergenceStatus,
  overallStatus,
  byWorstFirst,
  type Status,
} from "./diagnostics";
import type { McmcDiagnostics } from "./types";

// MCMC convergence table (R̂ / ESS / divergences) for the Lab. Server Component —
// pure static markup, no animation → reduced-motion safe by construction. Status
// is carried by an ICON + word + colour (never colour alone → colourblind-safe,
// ACCESSIBILITY.md). Worst params float to the top.

const GLYPH: Record<Status, string> = { ok: "●", warn: "▲", bad: "✕", unknown: "–" };
const WORD: Record<Status, string> = { ok: "ok", warn: "watch", bad: "fail", unknown: "n/a" };
const TONE: Record<Status, string> = {
  ok: "text-pos",
  warn: "text-warn",
  bad: "text-neg",
  unknown: "text-ink-2",
};

function Cell({ value, status, fmt }: { value: number | null | undefined; status: Status; fmt: (n: number) => string }) {
  return (
    <td className="px-3 py-2 text-right font-mono tabular-nums">
      <span className={TONE[status]}>
        <span aria-hidden className="mr-1">
          {GLYPH[status]}
        </span>
        {value == null || !Number.isFinite(value) ? "—" : fmt(value)}
      </span>
      <span className="sr-only"> ({WORD[status]})</span>
    </td>
  );
}

export default function DiagnosticsTable({
  diagnostics,
  className,
}: {
  diagnostics: McmcDiagnostics;
  className?: string;
}) {
  const rows = byWorstFirst(diagnostics.params);
  const overall = overallStatus(diagnostics);
  const divStatus = divergenceStatus(diagnostics.divergences);

  if (rows.length === 0 && diagnostics.divergences == null) {
    return (
      <div
        className={`grid place-items-center rounded-[var(--radius,0.5rem)] border border-line p-6 text-label uppercase text-ink-2 ${className ?? ""}`}
        role="status"
      >
        No MCMC diagnostics yet — trigger a fit
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-label uppercase text-ink-2">MCMC convergence</span>
        <span className={`text-label uppercase ${TONE[overall]}`}>
          <span aria-hidden className="mr-1">
            {GLYPH[overall]}
          </span>
          run {WORD[overall]}
          {diagnostics.divergences != null && (
            <span className={`ml-3 ${TONE[divStatus]}`}>
              {diagnostics.divergences} divergence{diagnostics.divergences === 1 ? "" : "s"}
            </span>
          )}
        </span>
      </div>
      <div className="overflow-x-auto rounded-[var(--radius,0.5rem)] border border-line">
        <table className="w-full border-collapse text-body">
          <caption className="sr-only">
            MCMC convergence diagnostics per parameter: Gelman–Rubin R̂ and effective sample size.
          </caption>
          <thead>
            <tr className="border-b border-line text-label uppercase text-ink-2">
              <th scope="col" className="px-3 py-2 text-left">
                Parameter
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                R̂
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                ESS
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.name} className="border-b border-line/60 last:border-0">
                <th scope="row" className="px-3 py-2 text-left font-normal text-ink-1">
                  {p.name}
                </th>
                <Cell value={p.rhat} status={rhatStatus(p.rhat)} fmt={(n) => n.toFixed(3)} />
                <Cell value={p.ess} status={essStatus(p.ess)} fmt={(n) => Math.round(n).toLocaleString()} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
