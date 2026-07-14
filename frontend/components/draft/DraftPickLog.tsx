import type { MappedPick } from "@/lib/sleeperDraft";
import type { LeagueConfig } from "@/lib/leagueConfig";
import { norm } from "@/lib/draftAI";

// Round-by-round pick log: the draft in the order it happened, one block per round with
// each pick's overall number, team, and player. Snake order is visible (rounds alternate
// direction), so you can read the AI's logic pick by pick and spot a bad one (a K/DST or
// reach) in context. Read-only audit view — complements the roster-centric "All teams".
export default function DraftPickLog({
  picks,
  config,
  mySlot,
}: {
  picks: MappedPick[];
  config: LeagueConfig;
  mySlot: number;
}) {
  const numTeams = config.numTeams;
  const teamName = (slot: number) => config.teams.find((t) => t.slot === slot)?.name ?? `Team ${slot}`;

  if (!picks.length) {
    return <div className="glass p-8 text-center text-label text-ink-muted">No picks yet — draft or auto-draft to populate the log.</div>;
  }

  // group into rounds preserving pick order
  const totalRounds = Math.ceil(picks.length / numTeams);
  const rounds = Array.from({ length: totalRounds }, (_, r) =>
    picks.filter((p) => Math.ceil(p.pickNo / numTeams) === r + 1),
  );

  return (
    <div className="space-y-4">
      {rounds.map((round, r) => (
        <div key={r} className="glass overflow-hidden">
          <div className="border-b border-hairline px-4 py-2 text-label text-ink-muted">
            ROUND {r + 1}
            <span className="ml-2 text-ink-muted/60">{r % 2 === 1 ? "← snake" : ""}</span>
          </div>
          <table className="w-full text-left text-body">
            <tbody>
              {round.map((p) => {
                const pos = norm(p.player.position);
                const late = pos === "K" || pos === "DST";
                return (
                  <tr key={p.pickNo} className={`border-b border-hairline/40 ${p.team === mySlot ? "bg-accent/5" : ""}`}>
                    <td className="w-16 px-4 py-2 font-mono text-label text-ink-muted">
                      {r + 1}.{String(((p.pickNo - 1) % numTeams) + 1).padStart(2, "0")}
                    </td>
                    <td className="w-40 px-2 py-2 text-label">
                      <span className={p.team === mySlot ? "text-accent" : "text-ink-muted"}>{teamName(p.team)}</span>
                    </td>
                    <td className="px-2 py-2 font-medium">{p.player.full_name}</td>
                    <td className="w-16 px-2 py-2 text-right text-label">
                      <span className={late ? "text-ink-muted/60" : "text-ink-muted"}>{pos}</span>
                    </td>
                    <td className="w-12 px-4 py-2 text-right text-label text-ink-muted">{p.player.nfl_team ?? "FA"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
