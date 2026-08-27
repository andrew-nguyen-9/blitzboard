import type {
  BenchShapeEvidenceStatus,
  BenchShapePosition,
  BenchShapeProvenance,
  BenchShapeResolution,
  LeagueConfigKey,
  ResolveBenchShape,
} from "../../.orchestrator-v6/prep/C03-public-interface-v1";

export type DraftComponentName =
  | "immediate_lineup"
  | "bye_absence_coverage"
  | "contingent_role"
  | "breakout_option"
  | "waiver_replacement_churn"
  | "redundancy_cost";

export type ExplanationEvidenceState =
  | BenchShapeEvidenceStatus
  | "fallback";

export interface CoveredAssignmentEvidence {
  readonly week: number;
  readonly slot: string;
  readonly starterId: string;
}

export interface ImmediateLineupEvidence {
  readonly value: number;
  readonly slot: string | null;
  readonly replacedStarterId: string | null;
  readonly evidenceIds: readonly string[];
  readonly degradedInputs?: readonly string[];
}

export interface CoverageEvidence {
  readonly expectedStarts: number;
  readonly covered: readonly CoveredAssignmentEvidence[];
  readonly degraded: boolean;
  readonly degradedInputs?: readonly string[];
}

export interface ContingentEvidence {
  readonly starterId: string | null;
  readonly eligible: boolean;
  readonly evidence: string;
  readonly inheritanceProb: number | null;
  readonly expectedValue: number | null;
  readonly degradedReason: string | null;
  readonly evidenceIds: readonly string[];
}

export interface BreakoutEvidence {
  readonly value: number | null;
  readonly basis: string | null;
  readonly evidenceIds: readonly string[];
  readonly degradedInputs?: readonly string[];
}

export interface AcceptedC02OutcomeRef {
  readonly producerCommit: "417af276dd4438d8a35f38d08bfc26206044925e";
  readonly seed: number;
  readonly seats: readonly number[];
  readonly field:
    | "per_season"
    | "per_season_h2h"
    | "per_season_playoff"
    | "per_season_champ";
  readonly nSeasons: number;
}

export type ReplacementChurnEvidence =
  | {
      readonly kind: "candidate_transaction";
      readonly evidenceId: string;
      readonly addedPlayerId: string;
      readonly droppedPlayerId: string | null;
      readonly remainingHorizonGain: number;
      readonly transactionCost: number;
      readonly netValue: number;
      readonly outcomeRefs: readonly AcceptedC02OutcomeRef[];
    }
  | {
      readonly kind: "aggregate_only";
      readonly emergencyAdds: number;
      readonly upsideAdds: number;
      readonly waiverAdds: number;
      readonly waiverCost: number;
      readonly outcomeRef: AcceptedC02OutcomeRef;
    }
  | { readonly kind: "missing"; readonly reason: string };

export interface DraftExplanationInput {
  readonly candidateId: string;
  readonly candidatePosition: BenchShapePosition;
  readonly ownedAtPosition: number;
  readonly leagueConfigKey: LeagueConfigKey;
  readonly benchSlots: number;
  readonly resolveBenchShape: ResolveBenchShape;
  readonly immediate: ImmediateLineupEvidence;
  readonly coverage: CoverageEvidence;
  readonly contingent: ContingentEvidence;
  readonly breakout: BreakoutEvidence;
  readonly replacement: ReplacementChurnEvidence;
}

export interface DraftScoreComponent {
  readonly name: DraftComponentName;
  /** Signed contribution to total score; null means no defensible numeric value. */
  readonly value: number | null;
  readonly state: ExplanationEvidenceState;
  readonly evidenceIds: readonly string[];
  readonly degradedInputs: readonly string[];
}

export interface LeagueEvidencePresentation {
  readonly leagueConfigKey: LeagueConfigKey;
  readonly artifactEvidenceStatus: BenchShapeEvidenceStatus;
  readonly presentationState: ExplanationEvidenceState;
  readonly degraded: boolean;
  readonly degradedReason: BenchShapeResolution["degradedReason"];
  readonly provenance: BenchShapeProvenance;
}

export interface DraftExplanationPayload {
  readonly candidateId: string;
  readonly score: number;
  readonly components: readonly DraftScoreComponent[];
  readonly leagueEvidence: LeagueEvidencePresentation;
  readonly coveredAssignments: readonly CoveredAssignmentEvidence[];
  readonly contingent: ContingentEvidence;
  readonly upsideBasis: { readonly basis: string; readonly evidenceIds: readonly string[] } | null;
  readonly replacementChurn: ReplacementChurnEvidence;
  readonly degradedInputs: readonly string[];
  readonly runtime: {
    readonly resolverCalls: 1;
    readonly simulationTrials: 0;
    readonly seasonRollouts: 0;
    readonly monteCarloSamples: 0;
  };
}

function finite(value: number | null): value is number {
  return value != null && Number.isFinite(value);
}

function presentationState(resolution: BenchShapeResolution): ExplanationEvidenceState {
  if (resolution.degraded && resolution.degradedReason !== "unsupported_evidence") return "fallback";
  return resolution.evidenceStatus;
}

function component(
  name: DraftComponentName,
  value: number | null,
  state: ExplanationEvidenceState,
  evidenceIds: readonly string[],
  degradedInputs: readonly string[] = [],
): DraftScoreComponent {
  return { name, value: finite(value) ? value : null, state, evidenceIds, degradedInputs };
}

function replacementComponent(evidence: ReplacementChurnEvidence): DraftScoreComponent {
  if (evidence.kind === "candidate_transaction") {
    return component(
      "waiver_replacement_churn",
      evidence.netValue,
      "measured",
      [evidence.evidenceId],
    );
  }
  if (evidence.kind === "aggregate_only") {
    return component(
      "waiver_replacement_churn",
      null,
      "fallback",
      [formatC02OutcomeRef(evidence.outcomeRef)],
      ["aggregate_only_no_candidate_transactions"],
    );
  }
  return component("waiver_replacement_churn", null, "unsupported", [], [evidence.reason]);
}

export function formatC02OutcomeRef(ref: AcceptedC02OutcomeRef): string {
  return [
    ref.producerCommit,
    ref.seed,
    ref.field,
    [...ref.seats].join(","),
    ref.nSeasons,
  ].join(":");
}

/** Pure C04 consumer of the frozen C03 resolver. It performs one lookup and no simulation. */
export function buildDraftExplanation(input: DraftExplanationInput): DraftExplanationPayload {
  const shape = input.resolveBenchShape(input.leagueConfigKey, input.benchSlots);
  const shapeState = presentationState(shape);
  const curve = shape.softMarginalCosts[input.candidatePosition];
  const curveIndex = Math.min(Math.max(0, input.ownedAtPosition), curve.length - 1);
  const marginalCost = curve[curveIndex];
  const shapeDegraded = shape.degraded ? [shape.degradedReason ?? "unsupported_evidence"] : [];

  const components: DraftScoreComponent[] = [
    component(
      "immediate_lineup",
      input.immediate.value,
      input.immediate.degradedInputs?.length ? "fallback" : "measured",
      input.immediate.evidenceIds,
      input.immediate.degradedInputs,
    ),
    component(
      "bye_absence_coverage",
      input.coverage.expectedStarts,
      input.coverage.degraded ? "fallback" : "measured",
      input.coverage.covered.map((item) => `week:${item.week}:slot:${item.slot}:starter:${item.starterId}`),
      input.coverage.degradedInputs,
    ),
    component(
      "contingent_role",
      input.contingent.eligible ? input.contingent.expectedValue : 0,
      input.contingent.degradedReason ? "fallback" : "measured",
      input.contingent.evidenceIds,
      input.contingent.degradedReason ? [input.contingent.degradedReason] : [],
    ),
    component(
      "breakout_option",
      input.breakout.value,
      input.breakout.degradedInputs?.length ? "fallback" : "measured",
      input.breakout.evidenceIds,
      input.breakout.degradedInputs,
    ),
    replacementComponent(input.replacement),
    // C03 shape is a soft cost only. A deep position remains legal and receives the final
    // finite curve value; no candidate is rejected and hardCaps is never consulted.
    component("redundancy_cost", -marginalCost, shapeState, [], shapeDegraded),
  ];
  const degradedInputs = [...new Set(components.flatMap((item) => item.degradedInputs))];
  const score = components.reduce((sum, item) => sum + (item.value ?? 0), 0);

  return {
    candidateId: input.candidateId,
    score,
    components,
    leagueEvidence: {
      leagueConfigKey: shape.leagueConfigKey,
      artifactEvidenceStatus: shape.evidenceStatus,
      presentationState: shapeState,
      degraded: shape.degraded,
      degradedReason: shape.degradedReason,
      provenance: shape.provenance,
    },
    coveredAssignments: input.coverage.covered,
    contingent: input.contingent,
    upsideBasis: input.breakout.basis
      ? { basis: input.breakout.basis, evidenceIds: input.breakout.evidenceIds }
      : null,
    replacementChurn: input.replacement,
    degradedInputs,
    runtime: { resolverCalls: 1, simulationTrials: 0, seasonRollouts: 0, monteCarloSamples: 0 },
  };
}

/** UI-independent, deterministic text derived only from structured payload fields. */
export function formatDraftExplanation(payload: DraftExplanationPayload): readonly string[] {
  const lines: string[] = [];
  const immediate = payload.components.find((item) => item.name === "immediate_lineup");
  if (immediate?.value) lines.push(`Immediate lineup contribution: ${immediate.value.toFixed(2)}.`);
  for (const covered of payload.coveredAssignments) {
    lines.push(`Covers ${covered.slot} in week ${covered.week} for starter ${covered.starterId}.`);
  }
  if (payload.contingent.eligible && payload.contingent.starterId) {
    const probability = payload.contingent.inheritanceProb;
    lines.push(
      probability == null
        ? `Contingent behind ${payload.contingent.starterId}; probability unavailable.`
        : `Contingent behind ${payload.contingent.starterId} at ${(probability * 100).toFixed(1)}%.`,
    );
  }
  if (payload.upsideBasis) lines.push(`Upside basis: ${payload.upsideBasis.basis}.`);
  if (payload.replacementChurn.kind === "candidate_transaction") {
    lines.push(`Replacement/churn value: ${payload.replacementChurn.netValue.toFixed(2)}.`);
  }
  const redundancy = payload.components.find((item) => item.name === "redundancy_cost");
  if (redundancy?.value != null) lines.push(`Soft redundancy cost: ${Math.abs(redundancy.value).toFixed(2)}.`);
  lines.push(`League evidence: ${payload.leagueEvidence.presentationState}.`);
  if (payload.degradedInputs.length) lines.push(`Degraded inputs: ${payload.degradedInputs.join(", ")}.`);
  return lines;
}

