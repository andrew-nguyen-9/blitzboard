import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import type {
  BenchShapePosition,
  BenchShapeResolution,
  LeagueConfigKey,
  ResolveBenchShape,
} from "../../.orchestrator-v6/prep/C03-public-interface-v1";
import {
  buildDraftExplanation,
  formatDraftExplanation,
  type AcceptedC02OutcomeRef,
  type DraftExplanationInput,
} from "./v6DraftExplanation";
import { serializeDraftTrace, toDraftTrace } from "./v6DraftTrace";

const KEY: LeagueConfigKey = "t12-superflex-half-te0.0-b4-ir0";
const POSITIONS: readonly BenchShapePosition[] = ["QB", "RB", "WR", "TE", "K", "DST"];

function counts(benchSlots: number) {
  return { QB: 1, RB: benchSlots - 1, WR: 0, TE: 0, K: 0, DST: 0 };
}

function curves() {
  return Object.fromEntries(POSITIONS.map((position) => [position, [0, 1, 2, 3, 4]])) as unknown as BenchShapeResolution["softMarginalCosts"];
}

function unsupportedResolution(
  reason: BenchShapeResolution["degradedReason"] = "missing_league_key",
): BenchShapeResolution {
  return {
    leagueConfigKey: KEY,
    evidenceStatus: "unsupported",
    composition: counts(4),
    softMarginalCosts: curves(),
    provenance: { kind: "unsupported", reason: reason ?? "unsupported" },
    degraded: true,
    degradedReason: reason,
    hardCaps: null,
  };
}

const C02_REF: AcceptedC02OutcomeRef = {
  producerCommit: "417af276dd4438d8a35f38d08bfc26206044925e",
  seed: 20260825,
  seats: [0, 1],
  field: "per_season",
  nSeasons: 8,
};

function input(resolveBenchShape: ResolveBenchShape): DraftExplanationInput {
  return {
    candidateId: "candidate-rb",
    candidatePosition: "RB",
    ownedAtPosition: 1,
    leagueConfigKey: KEY,
    benchSlots: 4,
    resolveBenchShape,
    immediate: { value: 3, slot: "FLEX", replacedStarterId: "starter-flex", evidenceIds: ["lineup"] },
    coverage: {
      expectedStarts: 1,
      covered: [{ week: 8, slot: "RB", starterId: "starter-rb" }],
      degraded: false,
    },
    contingent: {
      starterId: "starter-rb",
      eligible: true,
      evidence: "authoritative_depth",
      inheritanceProb: 0.25,
      expectedValue: 4,
      degradedReason: null,
      evidenceIds: ["depth-feed"],
    },
    breakout: { value: 2, basis: "ceiling_vor", evidenceIds: ["projection"] },
    replacement: {
      kind: "candidate_transaction",
      evidenceId: "transaction-1",
      addedPlayerId: "candidate-rb",
      droppedPlayerId: "bench-rb",
      remainingHorizonGain: 3,
      transactionCost: 1,
      netValue: 2,
      outcomeRefs: [C02_REF],
    },
  };
}

describe("C04 consumer of frozen C03 ResolveBenchShape", () => {
  it("calls the frozen resolver exactly once with league key and bench size", () => {
    const calls: [LeagueConfigKey, number][] = [];
    const resolver: ResolveBenchShape = (key, benchSlots) => {
      calls.push([key, benchSlots]);
      return unsupportedResolution();
    };
    const payload = buildDraftExplanation(input(resolver));
    expect(calls).toEqual([[KEY, 4]]);
    expect(payload.runtime).toEqual({ resolverCalls: 1, simulationTrials: 0, seasonRollouts: 0, monteCarloSamples: 0 });
  });

  it("maps degraded resolver failures to visible fallback provenance", () => {
    const payload = buildDraftExplanation(input(() => unsupportedResolution("source_hash_mismatch")));
    expect(payload.leagueEvidence).toMatchObject({
      artifactEvidenceStatus: "unsupported",
      presentationState: "fallback",
      degraded: true,
      degradedReason: "source_hash_mismatch",
    });
    expect(payload.degradedInputs).toContain("source_hash_mismatch");
    expect(formatDraftExplanation(payload)).toContain("League evidence: fallback.");
  });

  it("preserves honest unsupported evidence instead of calling it measured", () => {
    const payload = buildDraftExplanation(input(() => unsupportedResolution("unsupported_evidence")));
    expect(payload.leagueEvidence.presentationState).toBe("unsupported");
    expect(payload.leagueEvidence.provenance.kind).toBe("unsupported");
    expect(formatDraftExplanation(payload)).not.toContain("League evidence: measured.");
  });

  it("uses deep soft costs without imposing a positional cap", () => {
    const args = input(() => unsupportedResolution());
    const payload = buildDraftExplanation({ ...args, ownedAtPosition: 99 });
    expect(payload.components.find((item) => item.name === "redundancy_cost")?.value).toBe(-4);
    expect(payload.leagueEvidence).not.toHaveProperty("hardCaps");
    expect(payload.score).toBeTypeOf("number");
  });

  it("adapts candidate transaction evidence without rerunning C02", () => {
    const payload = buildDraftExplanation(input(() => unsupportedResolution()));
    const replacement = payload.components.find((item) => item.name === "waiver_replacement_churn");
    expect(replacement).toMatchObject({ value: 2, state: "measured", evidenceIds: ["transaction-1"] });
    expect(formatDraftExplanation(payload)).toContain("Replacement/churn value: 2.00.");
  });

  it("degrades accepted C02 aggregate counters instead of inventing candidate value", () => {
    const args = input(() => unsupportedResolution());
    const payload = buildDraftExplanation({
      ...args,
      replacement: {
        kind: "aggregate_only",
        emergencyAdds: 1,
        upsideAdds: 2,
        waiverAdds: 3,
        waiverCost: 1,
        outcomeRef: C02_REF,
      },
    });
    expect(payload.components.find((item) => item.name === "waiver_replacement_churn")).toMatchObject({
      value: null,
      state: "fallback",
      degradedInputs: ["aggregate_only_no_candidate_transactions"],
    });
  });

  it("formats only claims supported by structured fields", () => {
    const args = input(() => unsupportedResolution());
    const payload = buildDraftExplanation({
      ...args,
      contingent: { ...args.contingent, eligible: false, expectedValue: null, starterId: null },
      breakout: { value: null, basis: null, evidenceIds: [], degradedInputs: ["missing_ceiling"] },
    });
    const text = formatDraftExplanation(payload).join(" ");
    expect(text).not.toContain("Contingent behind");
    expect(text).not.toContain("Upside basis");
    expect(text).toContain("missing_ceiling");
  });

  it("produces deterministic producer-blind traces", () => {
    const args = input(() => unsupportedResolution());
    const first = serializeDraftTrace(toDraftTrace(buildDraftExplanation(args)));
    const second = serializeDraftTrace(toDraftTrace(buildDraftExplanation(args)));
    expect(first).toBe(second);
    expect(first).not.toMatch(/timestamp|Math\.random/i);
    expect(JSON.parse(first).runtime).toEqual({
      resolverCalls: 1,
      simulationTrials: 0,
      seasonRollouts: 0,
      monteCarloSamples: 0,
    });
  });

  it("keeps the C04 browser adapter free of simulation and runtime-only APIs", () => {
    const explanation = readFileSync(new URL("./v6DraftExplanation.ts", import.meta.url), "utf8");
    const trace = readFileSync(new URL("./v6DraftTrace.ts", import.meta.url), "utf8");
    for (const source of [explanation, trace]) {
      expect(source).not.toMatch(/from\s+["'][^"']*(season_eval|simulation|monte.?carlo)/i);
      expect(source).not.toMatch(/node:|readFile|createHash|process\.|fetch\(|Math\.random/);
    }
  });
});

describe.skip("C04 measured C03 artifact acceptance — waiting for producer and C03 PASS", () => {
  it("consumes a canonical measured row and presents measured provenance", () => {});
  it("consumes an interpolated row without presenting it as measured", () => {});
  it("matches canonical and browser-safe artifact trace results", () => {});
});
