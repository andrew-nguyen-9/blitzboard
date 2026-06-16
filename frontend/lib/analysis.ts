// Post-draft analysis — turns the pick log + league config into per-team grades,
// projected points, positional strength, key players, and a plain-English
// strategy read. Powers both the end-of-draft card and the standalone analysis
// page. Pure + framework-free so it runs on the server or client unchanged.
import type { PlayerWithValue } from "./types";
import { fillRoster, type RosterFill } from "./draft";
import type { MappedPick } from "./sleeperDraft";
import type { LeagueConfig } from "./leagueConfig";

function norm(pos: string | null | undefined): string {
  return pos === "DEF" ? "DST" : pos ?? "?";
}

export interface ValueEvent {
  player: PlayerWithValue;
  team: number;
  teamName: string;
  pickNo: number;
  adp: number;
  delta: number; // adp - pickNo; positive = steal (fell), negative = reach
}

export interface TeamAnalysis {
  slot: number;
  name: string;
  picks: PlayerWithValue[];
  roster: RosterFill;
  projectedPoints: number;
  rank: number; // 1 = best projected starters
  grade: string;
  posStrength: { pos: string; total: number; rankPct: number }[];
  keyPlayers: PlayerWithValue[];
  strategy: string;
  notes: string[];
}

export interface DraftAnalysis {
  teams: TeamAnalysis[];
  leagueAvgPoints: number;
  steals: ValueEvent[];
  reaches: ValueEvent[];
  complete: boolean;
  totalSpots: number;
}

const CORE_POS = ["QB", "RB", "WR", "TE", "K", "DST"];

function gradeFor(pct: number, completeness: number): string {
  // blend projected-points percentile with how full the starting lineup is
  const s = pct * 0.8 + completeness * 0.2;
  if (s >= 0.92) return "A+";
  if (s >= 0.8) return "A";
  if (s >= 0.68) return "B+";
  if (s >= 0.55) return "B";
  if (s >= 0.42) return "C+";
  if (s >= 0.3) return "C";
  if (s >= 0.18) return "D";
  return "F";
}

function strategyFor(picks: PlayerWithValue[]): { label: string; notes: string[] } {
  const early = picks.slice(0, 5).map((p) => norm(p.position));
  const rbEarly = early.slice(0, 3).filter((p) => p === "RB").length;
  const wrEarly = early.slice(0, 3).filter((p) => p === "WR").length;
  const qbEarly = early.filter((p) => p === "QB").length;
  const firstRbRound = picks.findIndex((p) => norm(p.position) === "RB");
  const notes: string[] = [];
  let label = "Balanced";

  if (rbEarly >= 2) {
    label = "Robust RB";
    notes.push("Loaded the backfield early — strong floor, thinner at WR.");
  } else if (firstRbRound === -1 || firstRbRound >= 4) {
    label = "Zero RB";
    notes.push("Punted early RB for elite WR/TE value — needs RB hits on the bench.");
  } else if (rbEarly === 1 && wrEarly >= 1 && firstRbRound <= 1) {
    label = "Hero RB";
    notes.push("Anchor RB up top, then leaned receivers.");
  } else if (wrEarly >= 2) {
    label = "WR-centric";
    notes.push("Receiver-heavy build — reliable points, watch RB depth.");
  }
  if (qbEarly >= 2) {
    label = `${label} · Early QB`;
    notes.push("Secured two starting QBs early — big edge in superflex.");
  }
  return { label, notes };
}

export function analyzeDraft(picks: MappedPick[], config: LeagueConfig): DraftAnalysis {
  const { numTeams, rosterSlots, benchSize, teams } = config;
  const totalSpots = (rosterSlots.length + benchSize) * numTeams;
  const nameFor = (slot: number) => teams.find((t) => t.slot === slot)?.name ?? `Team ${slot}`;

  // group picks by team
  const byTeam = new Map<number, PlayerWithValue[]>();
  for (let s = 1; s <= numTeams; s++) byTeam.set(s, []);
  for (const pk of picks) byTeam.get(pk.team)?.push(pk.player);

  // position totals per team (projected value), for strength ranking
  const posTotals: Record<string, number[]> = {};
  for (const pos of CORE_POS) posTotals[pos] = [];

  const base = Array.from(byTeam.entries()).map(([slot, tp]) => {
    const roster = fillRoster(tp, rosterSlots);
    const perPos: Record<string, number> = {};
    for (const p of tp) {
      const pos = norm(p.position);
      perPos[pos] = (perPos[pos] ?? 0) + (p.value?.value ?? 0);
    }
    for (const pos of CORE_POS) posTotals[pos].push(perPos[pos] ?? 0);
    return { slot, picks: tp, roster, perPos };
  });

  // rank by projected starters
  const sortedPts = [...base].map((b) => b.roster.projectedPoints).sort((a, b) => b - a);
  const leagueAvgPoints = sortedPts.reduce((s, v) => s + v, 0) / (numTeams || 1);
  const maxPts = sortedPts[0] || 1;
  const minPts = sortedPts[sortedPts.length - 1] || 0;

  const teamsOut: TeamAnalysis[] = base
    .map((b) => {
      const rank = sortedPts.indexOf(b.roster.projectedPoints) + 1;
      const pct = maxPts === minPts ? 1 : (b.roster.projectedPoints - minPts) / (maxPts - minPts);
      const filledStarters = b.roster.starters.filter((s) => s.player).length;
      const completeness = filledStarters / (rosterSlots.length || 1);
      const posStrength = CORE_POS.map((pos) => {
        const total = b.perPos[pos] ?? 0;
        const sorted = [...posTotals[pos]].sort((x, y) => y - x);
        const rankPct = sorted.length ? 1 - sorted.indexOf(total) / Math.max(1, sorted.length - 1) : 0;
        return { pos, total, rankPct };
      }).filter((s) => s.total > 0);
      const keyPlayers = [...b.picks]
        .sort((x, y) => (y.value?.vor ?? -999) - (x.value?.vor ?? -999))
        .slice(0, 3);
      const { label, notes } = strategyFor(b.picks);
      if (b.roster.needs.length) notes.push(`Still light at: ${b.roster.needs.join(", ")}.`);
      return {
        slot: b.slot,
        name: nameFor(b.slot),
        picks: b.picks,
        roster: b.roster,
        projectedPoints: b.roster.projectedPoints,
        rank,
        grade: gradeFor(pct, completeness),
        posStrength,
        keyPlayers,
        strategy: label,
        notes,
      };
    })
    .sort((a, b) => a.rank - b.rank);

  // steals & reaches vs ADP
  const events: ValueEvent[] = picks
    .filter((pk) => pk.player.value?.adp != null && (pk.player.value?.adp ?? 0) > 0)
    .map((pk) => ({
      player: pk.player,
      team: pk.team,
      teamName: nameFor(pk.team),
      pickNo: pk.pickNo,
      adp: pk.player.value!.adp as number,
      delta: (pk.player.value!.adp as number) - pk.pickNo,
    }));
  const steals = [...events].sort((a, b) => b.delta - a.delta).slice(0, 6);
  const reaches = [...events].sort((a, b) => a.delta - b.delta).slice(0, 6);

  return {
    teams: teamsOut,
    leagueAvgPoints,
    steals,
    reaches,
    complete: picks.length >= totalSpots,
    totalSpots,
  };
}
