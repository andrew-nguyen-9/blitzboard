// Pure roster-health logic for the war room — surfaces the W2 draft invariants
// (starters filled, bye conflicts, K/DST cap) VISIBLY so the failures in the
// reference screenshot become impossible, plus the marginal equity a pick adds.
// Framework-free so it's trivially unit-testable and reused by the panel.
import type { PlayerWithValue } from "@/lib/types";
import type { RosterSlot } from "@/lib/draft";
import { fillRoster } from "@/lib/draft";
import { norm, optimalLineupPoints } from "@/lib/draftAI";
import { BYE_WEEKS_2026 } from "@/lib/byeWeeks";

export type HealthStatus = "ok" | "warn" | "crit";

export interface HealthInvariant {
  key: string;
  label: string;
  status: HealthStatus;
  detail: string;
}

export interface ByeConflict {
  week: number;
  players: string[]; // starter names sharing this bye week
}

export interface RosterHealth {
  startersFilled: number;
  startersTotal: number;
  openSlots: string[];
  byeConflicts: ByeConflict[];
  kCount: number;
  dstCount: number;
  invariants: HealthInvariant[];
}

// Bye week from the row, falling back to the baked 2026 schedule by nfl_team —
// mirrors draftAI.resolveBye (not exported there) so reasoning fires even when a
// row didn't carry bye_week.
export function resolveBye(p: PlayerWithValue | null | undefined): number | null {
  if (!p) return null;
  return p.bye_week ?? (p.nfl_team ? BYE_WEEKS_2026[p.nfl_team] ?? null : null);
}

// The marginal projected starting-lineup points a candidate adds — the "equity
// impact" of a pick. Reuses the same optimal-lineup fill the policy scores on, so
// the number the drafter sees is the number the recommendation is built from.
export function equityImpact(
  teamPicks: PlayerWithValue[],
  cand: PlayerWithValue,
  roster: RosterSlot[],
): number {
  const base = optimalLineupPoints(teamPicks, roster);
  return Math.max(0, optimalLineupPoints([...teamPicks, cand], roster) - base);
}

// Compute the visible health of MY roster given the players I've drafted.
export function rosterHealth(
  teamPicks: PlayerWithValue[],
  roster: RosterSlot[],
): RosterHealth {
  const fill = fillRoster(teamPicks, roster);
  const starters = fill.starters
    .map((s) => s.player)
    .filter((p): p is PlayerWithValue => !!p);
  const startersTotal = roster.length;
  const startersFilled = starters.length;
  const openSlots = fill.starters.filter((s) => !s.player).map((s) => s.slot);

  // Bye conflict = 2+ STARTERS off the same week → that week's lineup has holes.
  const byWeek = new Map<number, string[]>();
  for (const s of starters) {
    const bye = resolveBye(s);
    if (bye == null) continue;
    (byWeek.get(bye) ?? byWeek.set(bye, []).get(bye)!).push(s.full_name);
  }
  const byeConflicts: ByeConflict[] = [...byWeek.entries()]
    .filter(([, players]) => players.length >= 2)
    .map(([week, players]) => ({ week, players }))
    .sort((a, b) => b.players.length - a.players.length);

  const kCount = teamPicks.filter((p) => norm(p.position) === "K").length;
  const dstCount = teamPicks.filter((p) => norm(p.position) === "DST").length;

  const hasKSlot = roster.some((s) => s.slot === "K");
  const hasDstSlot = roster.some((s) => s.slot === "DST");

  const invariants: HealthInvariant[] = [
    {
      key: "starters",
      label: "Starters filled",
      status: startersFilled >= startersTotal ? "ok" : startersFilled >= startersTotal - 2 ? "warn" : "crit",
      detail: `${startersFilled}/${startersTotal}${openSlots.length ? ` · open: ${openSlots.join(", ")}` : ""}`,
    },
    {
      key: "byes",
      label: "Bye coverage",
      status: byeConflicts.length === 0 ? "ok" : byeConflicts.some((c) => c.players.length >= 3) ? "crit" : "warn",
      detail: byeConflicts.length
        ? byeConflicts.map((c) => `wk ${c.week}: ${c.players.length} starters`).join(" · ")
        : "no stacked byes",
    },
    {
      key: "kdst",
      label: "K/DST cap",
      status: kCount > 1 || dstCount > 1 ? "warn" : "ok",
      detail:
        kCount > 1 || dstCount > 1
          ? `over-drafted (K ${kCount}, DST ${dstCount})`
          : hasKSlot || hasDstSlot
            ? `K ${kCount} · DST ${dstCount} (draft late)`
            : "not started in this league",
    },
  ];

  return { startersFilled, startersTotal, openSlots, byeConflicts, kCount, dstCount, invariants };
}
