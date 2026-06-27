// League-rules detection (v2.5.4.2): turn a platform's raw league settings into a normalized
// rules object the ValueEngine can consume. The acceptance is detection — superflex,
// distance-based kicking, yardage-based D/ST, and FAAB waivers — surfaced for the user to
// confirm/edit before the rules drive value. Pure + framework-free, tested against fixtures.
// (The import *flow* — fetching settings via our proxy — lives in leagueImport.ts.)
import type { RosterSlot } from "./draft";
import { rosterFromSleeper } from "./leagueConfig";

export interface ImportedRules {
  source: "sleeper" | "espn";
  league_size: number;
  waiver_type: "faab" | "rolling" | "reverse" | "unknown";
  superflex: boolean;
  distance_kicking: boolean; // field goals scored by distance bucket
  yardage_dst: boolean; // defense scored by yards allowed
  ppr: number; // points per reception (0 | 0.5 | 1, or league value)
  roster_slots: RosterSlot[];
  bench: number;
  scoring_label: string;
}

// ── Sleeper (public API: GET /v1/league/{id}) ──────────────────────────────
export interface SleeperLeague {
  total_rosters?: number;
  roster_positions?: string[];
  scoring_settings?: Record<string, number>;
  settings?: { waiver_type?: number; waiver_budget?: number; num_teams?: number };
}

function sleeperWaiver(s: SleeperLeague["settings"]): ImportedRules["waiver_type"] {
  if (!s) return "unknown";
  if (s.waiver_type === 2 || (s.waiver_budget ?? 0) > 0) return "faab";
  if (s.waiver_type === 1) return "reverse";
  if (s.waiver_type === 0) return "rolling";
  return "unknown";
}

export function parseSleeperRules(league: SleeperLeague): ImportedRules {
  const positions = league.roster_positions ?? [];
  const scoring = league.scoring_settings ?? {};
  const { slots, bench } = rosterFromSleeper(positions);
  const superflex = positions.includes("SUPER_FLEX");
  // Distance kicking: Sleeper splits made FGs into distance buckets (fgm_0_19, fgm_50p, …).
  const distance_kicking = Object.keys(scoring).some((k) => /^fgm_\d/.test(k) || k === "fgm_50p");
  // Yardage D/ST: keys for yards-allowed bands (yds_allow*) rather than only points-allowed.
  const yardage_dst = Object.keys(scoring).some((k) => k.startsWith("yds_allow"));
  const ppr = scoring.rec ?? 0;
  const pprLabel = ppr >= 1 ? "PPR" : ppr >= 0.5 ? "Half-PPR" : "Standard";
  return {
    source: "sleeper",
    league_size: league.total_rosters ?? league.settings?.num_teams ?? 12,
    waiver_type: sleeperWaiver(league.settings),
    superflex,
    distance_kicking,
    yardage_dst,
    ppr,
    roster_slots: slots,
    bench,
    scoring_label: `${pprLabel}${superflex ? " · Superflex" : ""}`,
  };
}

// ── ESPN (Fantasy API league settings) ─────────────────────────────────────
// ESPN encodes slots and stats as numeric ids. The constants below are the stable ones we
// need for detection; the user confirms/edits before anything drives value.
const ESPN_SUPERFLEX_SLOT = 7; // "OP" (QB/RB/WR/TE)
const ESPN_BENCH_SLOT = 20;
const ESPN_FG_DISTANCE_STATS = [201, 202, 203, 204, 205, 206, 213, 214, 215, 216, 217, 218];
const ESPN_DST_YARDS_STATS = [127, 128];

export interface EspnLeague {
  settings?: {
    size?: number;
    rosterSettings?: { lineupSlotCounts?: Record<string, number> };
    scoringSettings?: { scoringItems?: { statId: number }[] };
    acquisitionSettings?: { isUsingAcquisitionBudget?: boolean; acquisitionBudget?: number };
  };
}

const ESPN_SLOT_MAP: Record<number, { slot: string; eligible: string[] }> = {
  0: { slot: "QB", eligible: ["QB"] },
  2: { slot: "RB", eligible: ["RB"] },
  4: { slot: "WR", eligible: ["WR"] },
  6: { slot: "TE", eligible: ["TE"] },
  23: { slot: "FLEX", eligible: ["RB", "WR", "TE"] },
  7: { slot: "OP", eligible: ["QB", "RB", "WR", "TE"] },
  16: { slot: "DST", eligible: ["DST", "DEF"] },
  17: { slot: "K", eligible: ["K"] },
};

export function parseEspnRules(league: EspnLeague): ImportedRules {
  const s = league.settings ?? {};
  const counts = s.rosterSettings?.lineupSlotCounts ?? {};
  const slots: RosterSlot[] = [];
  let bench = 0;
  for (const [id, n] of Object.entries(counts)) {
    const num = Number(id);
    const count = Number(n) || 0;
    if (num === ESPN_BENCH_SLOT) {
      bench += count;
      continue;
    }
    const m = ESPN_SLOT_MAP[num];
    if (m) for (let i = 0; i < count; i++) slots.push({ slot: m.slot, eligible: m.eligible });
  }
  const superflex = (counts[String(ESPN_SUPERFLEX_SLOT)] ?? 0) > 0;
  const statIds = new Set((s.scoringSettings?.scoringItems ?? []).map((i) => i.statId));
  const distance_kicking = ESPN_FG_DISTANCE_STATS.some((id) => statIds.has(id));
  const yardage_dst = ESPN_DST_YARDS_STATS.some((id) => statIds.has(id));
  const faab =
    !!s.acquisitionSettings?.isUsingAcquisitionBudget || (s.acquisitionSettings?.acquisitionBudget ?? 0) > 0;
  return {
    source: "espn",
    league_size: s.size ?? 12,
    waiver_type: faab ? "faab" : "unknown",
    superflex,
    distance_kicking,
    yardage_dst,
    ppr: 0, // ESPN PPR is a scoring item (statId 53); left for the confirm screen to refine
    roster_slots: slots,
    bench,
    scoring_label: superflex ? "Superflex" : "Standard",
  };
}
