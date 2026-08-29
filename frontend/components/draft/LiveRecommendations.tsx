import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import type { WhyChip } from "./reasons";
import { formatDraftExplanation, type DraftExplanationPayload } from "@/lib/v6DraftExplanation";

export interface Recommendation {
  player: PlayerWithValue;
  reasons: WhyChip[];
  equity: number; // marginal projected starting-lineup points this pick adds
  explanation: DraftExplanationPayload;
}

export function recommendationClaims(recommendation: Recommendation): readonly string[] {
  return formatDraftExplanation(recommendation.explanation);
}

function compactReason(recommendation: Recommendation): string {
  const immediate = recommendation.explanation.components.find(({ name }) => name === "immediate_lineup")?.value ?? 0;
  const chip = recommendation.reasons.find(({ key, label }) =>
    label !== "rank/ADP gap · source/date unknown" && (key !== "vona" || immediate !== 0),
  );
  return chip?.title
    ?? recommendationClaims(recommendation).find((claim) => !claim.startsWith("League evidence:") && !claim.startsWith("Limitations:"))
    ?? "One of the four current BlitzBoard options";
}

function evidenceLimited(recommendation: Recommendation): boolean {
  return recommendation.explanation.degradedInputs.length > 0
    || recommendation.explanation.leagueEvidence.presentationState !== "measured";
}

// Live ranked recommendations with a legible "why" (VONA / scarcity / run-risk /
// need) + equity impact. Purely presentational + reduced-motion by construction.
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
  const limited = recs.some(evidenceLimited);
  return (
    <div className="glass p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-label text-ink-muted">
          RECOMMENDED{isMyPick ? " · YOUR PICK" : picksUntilMe != null ? ` · IN ${picksUntilMe}` : ""}
        </h2>
        {limited && <p className="text-label text-ink-muted"><span className="text-ink">Limited evidence</span> · support varies by candidate</p>}
      </div>
      <ol className="space-y-2">
        {recs.map((recommendation, idx) => {
          const { player, equity } = recommendation;
          const pos = player.position === "DEF" ? "DST" : player.position;
          return (
            <li key={player.id} className={`rounded-xl border p-2 ${idx === 0 ? "border-accent/40" : "border-hairline"}`}>
              <div className="flex items-center gap-2">
                <span className="w-4 shrink-0 font-mono text-label text-ink-muted">{idx + 1}</span>
                <span className="w-[4.75rem] shrink-0 text-label text-ink-muted">{idx === 0 ? "Primary" : "Alternative"}</span>
                <Link href={`/players/${player.id}`} className="min-w-0 flex-1 truncate font-medium transition hover:text-accent">
                  {player.full_name}
                </Link>
                <span className="shrink-0 text-label text-ink-muted/70">{pos}</span>
                {onDraft && isMyPick && (
                  <button
                    aria-label={`Draft ${player.full_name} to my team`}
                    onClick={() => onDraft(player)}
                    className="min-h-11 min-w-11 shrink-0 rounded-full bg-accent px-2.5 py-0.5 text-label text-bg transition hover:opacity-90"
                  >
                    Draft
                  </button>
                )}
              </div>
              <p className="mt-1 text-label text-ink-muted" aria-label={`Summary for ${player.full_name}`}>{compactReason(recommendation)}</p>
              {equity > 0 && <p className="text-label text-accent">+{equity.toFixed(1)} projected lineup pts</p>}
            </li>
          );
        })}
      </ol>
      <details className="mt-3 text-label">
        <summary>
          Full evidence for {recs.length} candidates
          <span className="ml-2 text-ink-muted">· Calibrated projection range unavailable.</span>
        </summary>
        <div className="mt-3 space-y-4">
          {recs.map((recommendation) => (
            <section key={recommendation.player.id} aria-labelledby={`evidence-${recommendation.player.id}`}>
              <h3 id={`evidence-${recommendation.player.id}`} className="font-medium text-ink">{recommendation.player.full_name}</h3>
              <p className="text-ink-muted">Candidate evidence: {evidenceLimited(recommendation) ? "limited" : "measured"}.</p>
              {recommendation.reasons.map((reason) => <p key={reason.key} className="text-ink-muted">{reason.label}: {reason.title}</p>)}
              {recommendation.equity > 0 && <p className="text-ink-muted">Projected starting-lineup points added: {recommendation.equity.toFixed(1)}.</p>}
              {recommendationClaims(recommendation).map((claim) => <p key={claim} className="text-ink-muted">{claim}</p>)}
            </section>
          ))}
        </div>
      </details>
    </div>
  );
}
