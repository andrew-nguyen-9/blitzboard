import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import { UncertaintyStrip, playerUncertainty } from "@/components/uncertainty";
import type { WhyChip } from "./reasons";

export interface Recommendation {
  player: PlayerWithValue;
  reasons: WhyChip[];
  equity: number; // marginal projected starting-lineup points this pick adds
}

// Live ranked recommendations with a legible "why" (VONA / scarcity / run-risk /
// need) + equity impact + the composed uncertainty strip (range + badges). Purely
// presentational + reduced-motion by construction (static SVG/CSS from the kit).
export default function LiveRecommendations({
  recs,
  isMyPick,
  picksUntilMe,
  onDraft,
}: {
  recs: Recommendation[];
  isMyPick: boolean;
  picksUntilMe: number | null;
  onDraft?: (p: PlayerWithValue) => void;
}) {
  if (!recs.length) return null;
  return (
    <div className="glass p-4">
      <h3 className="mb-3 text-label text-ink-muted">
        RECOMMENDED{isMyPick ? " · YOUR PICK" : picksUntilMe != null ? ` · IN ${picksUntilMe}` : ""}
      </h3>
      <ol className="space-y-4">
        {recs.map(({ player, reasons, equity }, idx) => {
          const pos = player.position === "DEF" ? "DST" : player.position;
          const unc = playerUncertainty(player.value, null, "pts");
          return (
            <li key={player.id} className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="w-4 shrink-0 font-mono text-label text-ink-muted">{idx + 1}</span>
                <Link href={`/players/${player.id}`} className="min-w-0 flex-1 truncate font-medium transition hover:text-accent">
                  {player.full_name}
                </Link>
                <span className="shrink-0 text-label text-ink-muted/70">{pos}</span>
                {onDraft && isMyPick && (
                  <button
                    onClick={() => onDraft(player)}
                    className="shrink-0 rounded-full bg-accent px-2.5 py-0.5 text-label text-bg transition hover:opacity-90"
                  >
                    Draft
                  </button>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-1 pl-6">
                {reasons.map((c) => (
                  <span key={c.key} title={c.title} className="rounded-full border border-hairline px-2 py-0.5 text-label text-ink-muted">
                    {c.label}
                  </span>
                ))}
                {equity > 0 && (
                  <span title="Projected starting-lineup points this pick adds" className="rounded-full border border-accent/40 px-2 py-0.5 text-label text-accent">
                    +{equity.toFixed(1)} eq
                  </span>
                )}
              </div>
              {unc && (
                <div className="pl-6">
                  <UncertaintyStrip data={unc} showDistribution={false} className="!gap-2" />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
