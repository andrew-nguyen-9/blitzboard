// Real per-player availability (E2b) — the seam that replaces draftAI's old
// `faPenalty` + `injuryDiscount` hacks with an actual "will he take a snap" number.
// Three-tier degrade, cheapest/most-authoritative first:
//   1. the published `p_startable` from Supabase `player_availability` (queries.getAvailabilityMap,
//      itself sourced from the engine's `AvailabilityModel` — e2a).
//   2. a local estimate from signals already on the player row (free agent / injury status).
//      Mirrors `blitz_engine.survival.availability.STATUS_P` (e2a's report-status override
//      table — a fixed severity bucket, NOT one of the roster-ceiling priors e2a expects to
//      refit against e9b's roster feed) so behaviour matches until every player is published.
//   3. `NEUTRAL_AVAILABILITY` (1) — genuinely no signal, so the board never goes blank.
import type { PlayerWithValue } from "./types";

export const NEUTRAL_AVAILABILITY = 1;
// Below this, e2a's engine calls a player "effectively unavailable" (draft must never take him).
// Mirrors `blitz_engine.survival.availability.ZERO_AVAILABILITY_EPS`.
export const ZERO_AVAILABILITY_EPS = 0.01;

export type AvailabilityMap = Record<string, number>;

// Mirrors blitz_engine.survival.availability.STATUS_P (report-status override, not a fitted prior).
const STATUS_P: Record<string, number> = {
  active: 1, healthy: 1, probable: 0.95, questionable: 0.5, doubtful: 0.1,
  out: 0, inactive: 0, retired: 0, non_roster: 0, cut: 0,
  dnp: 0, ir: 0, pup: 0, nfi: 0, susp: 0, sus: 0, suspended: 0,
};
// Local proxy for e2a's FREE_AGENT roster-state ceiling until the real signal is published.
const FREE_AGENT_P = 0.02;

const INACTIVE_ROSTER_STATUSES = new Set(["inactive", "retired", "non_roster", "cut"]);

function rosterStatus(status: string | null | undefined): string {
  return (status ?? "").trim().toLowerCase().replace(/\s+/g, "_");
}

// A redraft board offers only current NFL roster members. This also removes
// historical records that Sleeper still labels Active but no longer assigns a team.
export function isDraftBoardEligible(p: PlayerWithValue): boolean {
  return p.nfl_team != null && !INACTIVE_ROSTER_STATUSES.has(rosterStatus(p.status));
}

function localEstimate(p: PlayerWithValue): number {
  const status = rosterStatus(p.status);
  if (status && STATUS_P[status] === 0) return 0;
  if (p.nfl_team == null) return FREE_AGENT_P;
  const s = (p.injury_status ?? "").trim().toLowerCase();
  return s ? (STATUS_P[s] ?? NEUTRAL_AVAILABILITY) : NEUTRAL_AVAILABILITY;
}

// The number draftAI multiplies a candidate's score by. `published` is the map read via
// queries.getAvailabilityMap(); absent/missing entry → the local estimate → neutral.
export function availabilityOf(p: PlayerWithValue, published?: AvailabilityMap | null): number {
  const real = published?.[p.id];
  return real ?? localEstimate(p);
}
