import Link from "next/link";
import type { DraftPlan, PlanPlayer, ValueFlag } from "./plan";

const FLAG: Record<ValueFlag, { label: string; cls: string } | null> = {
  value: { label: "value", cls: "text-[#33D17A]" },
  reach: { label: "reach", cls: "text-[#E0573A]" },
  fair: null,
};

function Target({ p }: { p: PlanPlayer }) {
  const flag = FLAG[p.flag];
  return (
    <div className="flex items-center gap-1.5 text-label">
      <span className="w-6 shrink-0 text-ink-muted/60">T{p.tier}</span>
      <Link href={`/players/${p.id}`} className="min-w-0 flex-1 truncate transition hover:text-accent">
        {p.name}
      </Link>
      <span className="shrink-0 text-ink-muted/70">{p.position}</span>
      {flag && <span className={`shrink-0 ${flag.cls}`}>{flag.label}</span>}
    </div>
  );
}

// Pre-draft plan + robust strategy tree: per-round primary targets with same-window
// contingencies, tiers, and ADP value/reach flags. The header exposes the re-plan
// gate — the tree only re-plans on a CONSEQUENTIAL pick, so inconsequential opponent
// picks never churn the path. Presentational + static.
export default function PreDraftPlan({
  plan,
  replanCount,
  lastTrigger,
}: {
  plan: DraftPlan | null;
  replanCount: number;
  lastTrigger?: string;
}) {
  if (!plan || !plan.rounds.length) return null;
  return (
    <div className="glass p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-label text-ink-muted">PLAN &amp; STRATEGY</h3>
        <span
          className="text-[10px] text-ink-muted/70"
          title={`Re-planned ${replanCount}× — only consequential picks trigger a re-plan${lastTrigger ? ` · last: ${lastTrigger}` : ""}`}
        >
          re-plan ×{replanCount}{lastTrigger ? ` · ${lastTrigger}` : ""}
        </span>
      </div>
      <ol className="space-y-3">
        {plan.rounds.map((r) => (
          <li key={r.pickNo} className="border-l border-hairline pl-3">
            <div className="mb-1 text-label text-ink-muted">
              R{r.round} · pick {r.pickNo}
            </div>
            <div className="space-y-1">
              {r.primary.map((p) => (
                <Target key={p.id} p={p} />
              ))}
            </div>
            {r.contingency.length > 0 && (
              <div className="mt-1.5 border-t border-hairline/50 pt-1.5">
                <div className="mb-0.5 text-[10px] uppercase tracking-wide text-ink-muted/60">if gone</div>
                <div className="space-y-1 opacity-70">
                  {r.contingency.map((p) => (
                    <Target key={p.id} p={p} />
                  ))}
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
