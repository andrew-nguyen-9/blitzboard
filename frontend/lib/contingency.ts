// C01 — the ONE public implementation of candidate-aware bye coverage and structured
// contingent-role evidence. Consumed by BOTH draftAI (draft-time bench value) and
// benchScore (roster bench score); no other copy of either rule may exist.
//
// Replaces two v5 defects:
//  - draftAI.byeCover / benchScore.byeCoverage scored byes without ever checking the
//    candidate's own bye or whether the candidate can legally start in the vacated slot.
//  - benchScore.handcuffValue / draftAI's same-team boolean inferred "handcuff" from
//    positional depth alone, with no team/succession evidence.
import type { PlayerWithValue } from "./types";
import type { RosterSlot } from "./draft";

const normPos = (p: string | null | undefined) => (p === "DEF" ? "DST" : (p ?? "?"));

// ── candidate-aware weekly bye coverage ────────────────────────────────────

export interface StarterSlot {
  slot: string;
  player: PlayerWithValue | null;
}

export interface ByeCoverage {
  /** Distinct weeks (ascending) with ≥1 starter-bye hole this candidate can actually fill. */
  covered: number[];
  /** Candidate bye unknown, or a starter bye unknown at a slot the candidate could cover. */
  degraded: boolean;
}

/** Max bipartite matching size, bodies → holes (tiny inputs: augmenting-path DFS). */
function matchSize(bodyHoles: number[][], nHoles: number): number {
  const holeOwner = new Array<number>(nHoles).fill(-1);
  const tryPlace = (b: number, seen: boolean[]): boolean => {
    for (const h of bodyHoles[b]) {
      if (seen[h]) continue;
      seen[h] = true;
      if (holeOwner[h] === -1 || tryPlace(holeOwner[h], seen)) {
        holeOwner[h] = b;
        return true;
      }
    }
    return false;
  };
  let size = 0;
  for (let b = 0; b < bodyHoles.length; b++) if (tryPlace(b, new Array(nHoles).fill(false))) size++;
  return size;
}

/**
 * Maximum-matched weekly slot coverage for ONE candidate, marginal over the bench already
 * owned: per week, starter byes open (week, slot) holes; bodies (owned bench + candidate)
 * are matched to holes they can legally start in (FLEX/OP aware) and are not themselves
 * absent for (a shared bye never counts). A week is credited only when ADDING the
 * candidate grows that week's maximum matching — a hole an owned body already covers
 * earns nothing, and one candidate can never cover two simultaneous holes.
 */
export function weeklyByeCoverage(
  cand: PlayerWithValue,
  starters: StarterSlot[],
  template: RosterSlot[],
  ownedBench: PlayerWithValue[] = [],
): ByeCoverage {
  const eligibleBySlot = new Map(template.map((s) => [s.slot, s.eligible]));
  const canStart = (p: PlayerWithValue, slot: string) =>
    (eligibleBySlot.get(slot) ?? []).includes(normPos(p.position));

  let degraded = cand.bye_week == null;
  const holesByWeek = new Map<number, string[]>();
  for (const s of starters) {
    if (s.player == null || s.player.id === cand.id) continue; // a starter cannot cover its own absence
    const bye = s.player.bye_week;
    if (bye == null) {
      if (canStart(cand, s.slot)) degraded = true; // a hole the candidate might cover is unknowable
      continue;
    }
    holesByWeek.set(bye, [...(holesByWeek.get(bye) ?? []), s.slot]);
  }
  if (cand.bye_week == null) return { covered: [], degraded };

  const bench = ownedBench.filter((b) => b.id !== cand.id);
  const covered: number[] = [];
  for (const [week, slots] of holesByWeek) {
    if (week === cand.bye_week) continue;
    const usable = bench.filter((b) => b.bye_week != null && b.bye_week !== week);
    const edges = (p: PlayerWithValue) =>
      slots.flatMap((slot, h) => (canStart(p, slot) ? [h] : []));
    const without = matchSize(usable.map(edges), slots.length);
    const withCand = matchSize([...usable.map(edges), edges(cand)], slots.length);
    if (withCand > without) covered.push(week);
  }
  return { covered: covered.sort((a, b) => a - b), degraded };
}

// ── structured contingent-role evidence ────────────────────────────────────

export type ContingentEvidence =
  | { kind: "rb-succession"; starterId: string; team: string; depthOrder: number }
  | { kind: "qb-authoritative-depth"; starterId: string; team: string; depthOrder: number }
  | { kind: "explicit-role-transfer"; starterId: string; team: string; source: string };

export type ContingentStatus =
  | "supported"
  | "no-evidence"
  | "ambiguous-depth"
  | "missing-metadata"
  | "not-applicable";

export interface ContingentRole {
  status: ContingentStatus;
  evidence: ContingentEvidence | null;
}

const NONE: ContingentRole = { status: "no-evidence", evidence: null };

/**
 * Evidence that `cand` inherits a starting role if `starter` is lost. v6 initial scope:
 * RB succession (same team + authoritative direct-backup depth), QB only with
 * authoritative feed depth, WR/TE only with explicit role-transfer evidence
 * (`metadata.role_transfer`, a non-empty source string). Everything else — including
 * same-roster positional depth, the v5 inference — is NOT evidence.
 */
export function contingentRole(cand: PlayerWithValue, starter: PlayerWithValue | null): ContingentRole {
  const pos = normPos(cand.position);
  if (pos === "K" || pos === "DST") return { status: "not-applicable", evidence: null };
  if (!starter || starter.id === cand.id) return NONE;
  if (!cand.nfl_team || !starter.nfl_team) return { status: "missing-metadata", evidence: null };
  if (cand.nfl_team !== starter.nfl_team) return NONE;

  if (pos === "WR" || pos === "TE") {
    const source = cand.metadata?.role_transfer;
    if (typeof source === "string" && source.length > 0) {
      return {
        status: "supported",
        evidence: { kind: "explicit-role-transfer", starterId: starter.id, team: cand.nfl_team, source },
      };
    }
    return NONE;
  }

  // QB and RB both require the feed's depth chart; projections are never depth evidence.
  const depth = cand.metadata?.depth_chart_order;
  if (depth == null) return { status: "ambiguous-depth", evidence: null };
  if (depth !== 2) return NONE; // only the direct backup succeeds
  const kind = pos === "QB" ? "qb-authoritative-depth" : pos === "RB" ? "rb-succession" : null;
  if (kind == null) return NONE;
  return { status: "supported", evidence: { kind, starterId: starter.id, team: cand.nfl_team, depthOrder: depth } };
}
