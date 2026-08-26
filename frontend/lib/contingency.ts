// C01 — the ONE public implementation of candidate-aware bye coverage and structured
// contingent-role valuation. Consumed by BOTH draftAI (draft-time bench value) and
// benchScore (roster bench score); no other copy of either rule may exist.
//
// Replaces two v5 defects:
//  - draftAI.byeCover / benchScore.byeCoverage scored byes without ever checking the
//    candidate's own bye or whether the candidate can legally start in the vacated slot.
//  - benchScore.handcuffValue / draftAI's same-team boolean inferred "handcuff" from
//    positional depth alone, with no team/succession evidence.
import type { PlayerWithValue } from "./types";
import type { RosterSlot } from "./draft";
import { projectionMean } from "./valueUnits";

const normPos = (p: string | null | undefined) => (p === "DEF" ? "DST" : (p ?? "?"));

// ── candidate-aware weekly bye coverage ────────────────────────────────────

export interface StarterSlot {
  slot: string;
  player: PlayerWithValue | null;
}

/** One starter-bye hole the candidate is matched into: which week, which lineup slot,
 * and which absent starter it stands in for. Derived from the winning matching
 * assignment, so it is deterministic and explainable (C04). */
export interface ByeCoverRecord {
  week: number;
  slot: string;
  starterId: string;
}

export interface ByeCoverage {
  /** Expected bye-driven starts the candidate adds: one per covered week (a candidate
   * can occupy at most one slot per week, so weeks = starts). */
  expectedStarts: number;
  /** The covered holes, ascending by week, from the actual matching assignment. */
  covered: ByeCoverRecord[];
  /** A bye is unknown somewhere it could change the answer: on the candidate, on a
   * starter at a slot the candidate could cover, or on an owned bench body that could
   * occupy any hole (making the baseline matching conditional on missing metadata). */
  degraded: boolean;
}

/** Max bipartite matching, bodies → holes (tiny inputs: augmenting-path DFS).
 * Bodies are placed in input order and a placed body never becomes unmatched, so the
 * result is deterministic and a prefix of the body list reproduces its own matching. */
function matchAssign(bodyHoles: number[][], nHoles: number): { size: number; holeOwner: number[] } {
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
  return { size, holeOwner };
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
  const holesByWeek = new Map<number, { slot: string; starterId: string }[]>();
  for (const s of starters) {
    if (s.player == null || s.player.id === cand.id) continue; // a starter cannot cover its own absence
    const bye = s.player.bye_week;
    if (bye == null) {
      if (canStart(cand, s.slot)) degraded = true; // a hole the candidate might cover is unknowable
      continue;
    }
    holesByWeek.set(bye, [...(holesByWeek.get(bye) ?? []), { slot: s.slot, starterId: s.player.id }]);
  }
  if (cand.bye_week == null) return { expectedStarts: 0, covered: [], degraded };

  const bench = ownedBench.filter((b) => b.id !== cand.id);
  // A bye-less owned body that could occupy any hole is excluded from the baseline
  // matching, so every marginal verdict is conditional on its missing bye → degraded.
  const allHoles = [...holesByWeek.values()].flat();
  if (bench.some((b) => b.bye_week == null && allHoles.some((h) => canStart(b, h.slot)))) {
    degraded = true;
  }

  const covered: ByeCoverRecord[] = [];
  for (const [week, holes] of holesByWeek) {
    if (week === cand.bye_week) continue;
    const usable = bench.filter((b) => b.bye_week != null && b.bye_week !== week);
    const edges = (p: PlayerWithValue) =>
      holes.flatMap((hole, h) => (canStart(p, hole.slot) ? [h] : []));
    const without = matchAssign(usable.map(edges), holes.length).size;
    const withCand = matchAssign([...usable.map(edges), edges(cand)], holes.length);
    if (withCand.size > without) {
      // The first |usable| placements reproduce the baseline exactly (same edges, same
      // order), so a larger matching means the candidate body itself holds a hole.
      const h = withCand.holeOwner.indexOf(usable.length);
      covered.push({ week, slot: holes[h].slot, starterId: holes[h].starterId });
    }
  }
  covered.sort((a, b) => a.week - b.week);
  return { expectedStarts: covered.length, covered, degraded };
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
 * RB succession (same team + authoritative direct-backup depth behind an unambiguous
 * depth-1 starter), QB only with the same authoritative feed depth on both sides, WR/TE
 * only with explicit role-transfer evidence (`metadata.role_transfer`, a non-empty
 * source string). Succession never crosses positions, and everything else — including
 * same-roster positional depth, the v5 inference — is NOT evidence.
 */
export function contingentRole(cand: PlayerWithValue, starter: PlayerWithValue | null): ContingentRole {
  const pos = normPos(cand.position);
  if (pos === "K" || pos === "DST") return { status: "not-applicable", evidence: null };
  if (!starter || starter.id === cand.id) return NONE;
  if (normPos(starter.position) !== pos) return NONE; // cross-position pairing is never succession
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

  // QB and RB require the feed's depth chart on BOTH sides; projections are never depth
  // evidence. The candidate must be the direct backup (depth 2) of an authoritative
  // depth-1 starter — a missing or non-1 starter depth leaves the order unverifiable.
  const depth = cand.metadata?.depth_chart_order;
  if (depth == null) return { status: "ambiguous-depth", evidence: null };
  if (depth !== 2) return NONE; // only the direct backup succeeds
  const starterDepth = starter.metadata?.depth_chart_order;
  if (starterDepth !== 1) return { status: "ambiguous-depth", evidence: null };
  const kind = pos === "QB" ? "qb-authoritative-depth" : pos === "RB" ? "rb-succession" : null;
  if (kind == null) return NONE;
  return { status: "supported", evidence: { kind, starterId: starter.id, team: cand.nfl_team, depthOrder: depth } };
}

// ── shared contingent-role valuation ───────────────────────────────────────

/** P(the starter's role is vacated), from injury_status (null/active = low baseline). */
export function injuryRisk(status: string | null | undefined): number {
  const s = (status ?? "").toLowerCase();
  if (!s || s === "active" || s === "healthy") return 0.1;
  if (s.includes("question")) return 0.35;
  if (s.includes("doubt")) return 0.65;
  if (s.includes("out")) return 0.85;
  if (s.includes("ir") || s.includes("pup") || s.includes("reserve") || s.includes("suspend")) return 0.95;
  return 0.4;
}

export interface ContingentValuation {
  status: ContingentStatus;
  /** True only when structured succession evidence supports inheritance. */
  eligible: boolean;
  /** The relevant (proposed) starter, when one exists. */
  starterId: string | null;
  evidence: ContingentEvidence | null;
  /** P(the candidate inherits the role this season) = the starter's loss risk; 0 unless eligible. */
  inheritanceProb: number;
  /** Season points: inheritanceProb × the candidate's raw projection mean; 0 unless eligible. */
  expectedValue: number;
  /** Why the valuation is degraded (evidence unverifiable), else null. */
  degradedReason: string | null;
}

const DEGRADED_REASON: Partial<Record<ContingentStatus, string>> = {
  "ambiguous-depth": "depth chart order missing or non-authoritative",
  "missing-metadata": "candidate or starter NFL team metadata missing",
};

/**
 * The ONE contingent-role valuation (whether + probability + expected value). Both
 * consumers scale `expectedValue` — or its `inheritanceProb` factor onto their own
 * value scale — into their score; neither may re-decide whether a succession exists
 * nor rebuild its value from raw metadata.
 */
export function contingentValuation(
  cand: PlayerWithValue,
  starter: PlayerWithValue | null,
): ContingentValuation {
  const role = contingentRole(cand, starter);
  const eligible = role.status === "supported";
  const prob = eligible && starter ? injuryRisk(starter.injury_status) : 0;
  return {
    status: role.status,
    eligible,
    starterId: role.evidence?.starterId ?? starter?.id ?? null,
    evidence: role.evidence,
    inheritanceProb: prob,
    expectedValue: prob * projectionMean(cand),
    degradedReason: DEGRADED_REASON[role.status] ?? null,
  };
}
