import type { DraftExplanationPayload } from "./v6DraftExplanation";

export interface DraftTrace {
  readonly traceVersion: 1;
  readonly candidateId: string;
  readonly score: number;
  readonly componentValues: Readonly<Record<string, number | null>>;
  readonly leagueEvidence: DraftExplanationPayload["leagueEvidence"];
  readonly degradedInputs: readonly string[];
  readonly runtime: DraftExplanationPayload["runtime"];
}

/** Stable producer-blind trace projection: no prose, timestamps, randomness, or object identity. */
export function toDraftTrace(payload: DraftExplanationPayload): DraftTrace {
  return {
    traceVersion: 1,
    candidateId: payload.candidateId,
    score: payload.score,
    componentValues: Object.fromEntries(payload.components.map((item) => [item.name, item.value])),
    leagueEvidence: payload.leagueEvidence,
    degradedInputs: payload.degradedInputs,
    runtime: payload.runtime,
  };
}

export function serializeDraftTrace(trace: DraftTrace): string {
  return `${JSON.stringify(trace, null, 2)}\n`;
}

