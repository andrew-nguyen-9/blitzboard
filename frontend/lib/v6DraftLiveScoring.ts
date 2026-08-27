import type {
  BenchShapePosition,
  BenchShapeResolution as FrozenBenchShapeResolution,
  LeagueConfigKey,
  ResolveBenchShape,
} from "../../.orchestrator-v6/prep/C03-public-interface-v1";
import { resolveBenchShape } from "./benchShape";
import { fillRoster } from "./draft";
import {
  DEFAULT_POLICY,
  STARTABLE_WEEKS,
  availability,
  ceilingWeeks,
  injuryCover,
  marginalStarterValue,
  norm,
  proj,
  scoreBoard,
  type AIContext,
  type PolicyParams,
  type ScoredPick,
} from "./draftAI";
import { contingentValuation, weeklyByeCoverage } from "./contingency";
import { projectionCeiling } from "./valueUnits";
import type { LeagueConfig } from "./leagueConfig";
import {
  buildDraftExplanation,
  type DraftExplanationPayload,
  type ReplacementChurnEvidence,
} from "./v6DraftExplanation";
import { toDraftTrace, type DraftTrace } from "./v6DraftTrace";

/** Accepted C03 implementation adapter. C03's runtime provenance type is intentionally looser
 * than its frozen declaration; runtime/schema gates prove the discriminated shape. */
export const acceptedBenchShapeResolver: ResolveBenchShape = (key, benchSlots) =>
  resolveBenchShape(key, benchSlots) as unknown as FrozenBenchShapeResolution;

export interface LiveDraftExplanationContext {
  /** Canonical key when supported; custom/unrepresentable strings visibly fall back. */
  readonly leagueConfigKey: LeagueConfigKey | string;
  readonly replacementEvidence?: Readonly<Record<string, ReplacementChurnEvidence>>;
}

export interface ExplainedScoredPick extends ScoredPick {
  readonly explanation: DraftExplanationPayload;
  readonly trace: DraftTrace;
}

const CANONICAL_TEAMS = new Set([10, 12, 14]);

/** Derives the C03 key only when every frozen factor is represented by the live config.
 * Anything else remains a descriptive custom key and reaches the resolver's explicit fallback. */
export function deriveBenchShapeLeagueKey(config: LeagueConfig): LeagueConfigKey | string {
  const qbDedicated = config.rosterSlots.filter((slot) => slot.slot === "QB" && slot.eligible.length === 1).length;
  const qbFlex = config.rosterSlots.some((slot) => slot.slot !== "QB" && slot.eligible.includes("QB"));
  const qbMode = qbFlex ? "superflex" : qbDedicated >= 2 ? "2qb" : qbDedicated === 1 ? "1qb" : null;
  const label = config.scoringLabel.toLowerCase();
  const scoring = label.includes("half") ? "half"
    : label.includes("ppr") ? "ppr"
    : label.includes("standard") || /\bstd\b/.test(label) ? "std"
    : null;
  const tePremium = config.tePremium;
  const irSlots = config.irSlots;
  const canonical = CANONICAL_TEAMS.has(config.numTeams) && qbMode && scoring &&
    (config.benchSize === 4 || config.benchSize === 8) &&
    (tePremium === 0 || tePremium === 0.5) &&
    (irSlots === 0 || irSlots === 1);
  if (!canonical) {
    return `custom:t${config.numTeams}:b${config.benchSize}:${qbMode ?? "qb-unknown"}:${scoring ?? "scoring-unknown"}:te${config.tePremium ?? "unknown"}:ir${config.irSlots ?? "unknown"}`;
  }
  return `t${config.numTeams}-${qbMode}-${scoring}-te${tePremium.toFixed(1)}-b${config.benchSize}-ir${irSlots}` as LeagueConfigKey;
}

function shapePosition(position: string | null | undefined): BenchShapePosition {
  const normalized = norm(position);
  return (normalized === "QB" || normalized === "RB" || normalized === "WR" ||
    normalized === "TE" || normalized === "K" || normalized === "DST")
    ? normalized
    : "DST";
}

/** Scores once through the shipped policy, then decorates each candidate using C01 evidence,
 * accepted C03 provenance, and optional candidate-level C02 evidence. No simulation is added. */
export function scoreBoardWithExplanations(
  ctx: AIContext,
  live: LiveDraftExplanationContext,
  params: PolicyParams = DEFAULT_POLICY,
): ExplainedScoredPick[] {
  const scored = scoreBoard(ctx, params);
  const fill = fillRoster(ctx.teamPicks, ctx.roster);
  const starters = fill.starters.map((slot) => slot.player).filter((player): player is NonNullable<typeof player> => !!player);
  const starterIds = new Set(starters.map((player) => player.id));
  const ownedBench = ctx.teamPicks.filter((player) => !starterIds.has(player.id));

  return scored.map((pick) => {
    const candidate = pick.player;
    const position = shapePosition(candidate.position);
    const samePosition = ctx.teamPicks
      .filter((player) => norm(player.position) === position)
      .sort((a, b) => proj(b) - proj(a));
    const coveredStarter = samePosition[0] ?? null;
    const role = contingentValuation(candidate, coveredStarter);
    const coverage = weeklyByeCoverage(candidate, fill.starters, ctx.roster, ownedBench);
    const marginalStarter = starters
      .filter((player) => norm(player.position) === position)
      .sort((a, b) => proj(a) - proj(b))[0];
    const marginalProjection = marginalStarter ? proj(marginalStarter) : 0;
    const mean = proj(candidate);
    const boom = projectionCeiling(candidate) ?? mean;
    const valuePerGame = ((1 - params.boomWeight) * mean + params.boomWeight * boom) / STARTABLE_WEEKS;
    const available = availability(candidate, params);
    const coverageValue = params.benchByeWeight * coverage.expectedStarts * valuePerGame * available;
    const contingentStarts = injuryCover(candidate, coveredStarter, role, params);
    const contingentValue = params.benchInjuryWeight * contingentStarts * valuePerGame * available;
    const breakoutStarts = ceilingWeeks(candidate, marginalProjection, params);
    const breakoutValue = params.benchCeilingWeight * breakoutStarts * valuePerGame * available;
    const immediateValue = marginalStarterValue(candidate, ctx, params);
    const withCandidate = fillRoster([...ctx.teamPicks, candidate], ctx.roster);
    const candidateAssignment = withCandidate.starters.find((assignment) => assignment.player?.id === candidate.id);
    const afterStarterIds = new Set(withCandidate.starters.flatMap((assignment) => assignment.player ? [assignment.player.id] : []));
    const displacedStarter = starters.find((starter) => !afterStarterIds.has(starter.id));
    const replacement = live.replacementEvidence?.[candidate.id] ?? {
      kind: "missing" as const,
      reason: "accepted_c02_c03_have_no_candidate_transaction_evidence",
    };

    const explanation = buildDraftExplanation({
      candidateId: candidate.id,
      candidatePosition: position,
      ownedAtPosition: ownedBench.filter((player) => norm(player.position) === position).length,
      leagueConfigKey: live.leagueConfigKey as LeagueConfigKey,
      benchSlots: ctx.benchSize,
      resolveBenchShape: acceptedBenchShapeResolver,
      scoredTotal: pick.score,
      immediate: {
        value: immediateValue,
        slot: immediateValue > 0 ? candidateAssignment?.slot ?? null : null,
        replacedStarterId: immediateValue > 0 ? displacedStarter?.id ?? null : null,
        evidenceIds: ["draftAI:marginalStarterValue"],
      },
      coverage: {
        expectedStarts: coverage.expectedStarts,
        value: coverageValue,
        covered: coverage.covered,
        degraded: coverage.degraded,
        degradedInputs: coverage.degraded ? ["missing_bye_metadata"] : [],
      },
      contingent: {
        starterId: role.starterId,
        eligible: role.eligible,
        evidence: role.evidence?.kind ?? role.status,
        inheritanceProb: role.eligible ? role.inheritanceProb : null,
        expectedValue: role.eligible ? contingentValue : 0,
        degradedReason: role.degradedReason,
        evidenceIds: role.evidence ? [`contingency:${role.evidence.kind}`] : [],
      },
      breakout: {
        value: breakoutValue,
        basis: candidate.value?.boom == null ? null : "ceiling_vor_to_raw_projection",
        evidenceIds: candidate.value?.boom == null ? [] : ["value.boom", "value.replacement"],
        degradedInputs: candidate.value?.boom == null ? ["missing_ceiling"] : [],
      },
      replacement,
    });
    return { ...pick, explanation, trace: toDraftTrace(explanation) };
  });
}
