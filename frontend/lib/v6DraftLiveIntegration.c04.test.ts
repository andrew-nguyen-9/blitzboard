import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { recommendationClaims, type Recommendation } from "@/components/draft/LiveRecommendations";
import type { LeagueConfigKey } from "../../.orchestrator-v6/prep/C03-public-interface-v1";
import type { PlayerWithValue } from "@/lib/types";
import { buildDraftExplanation, type DraftExplanationInput } from "@/lib/v6DraftExplanation";
import { acceptedBenchShapeResolver } from "@/lib/v6DraftLiveScoring";

const player = {
  id: "rb2",
  full_name: "Candidate RB",
  position: "RB",
  nfl_team: "AAA",
  bye_week: 8,
  metadata: {},
  value: null,
} as PlayerWithValue;

function explanation(key: string) {
  const input: DraftExplanationInput = {
    candidateId: player.id,
    candidatePosition: "RB",
    ownedAtPosition: 1,
    leagueConfigKey: key as LeagueConfigKey,
    benchSlots: 4,
    resolveBenchShape: acceptedBenchShapeResolver,
    immediate: { value: 0, slot: null, replacedStarterId: null, evidenceIds: [] },
    coverage: {
      expectedStarts: 1,
      value: 2,
      covered: [{ week: 8, slot: "RB", starterId: "starter-rb" }],
      degraded: false,
    },
    contingent: {
      starterId: null,
      eligible: false,
      evidence: "no-evidence",
      inheritanceProb: null,
      expectedValue: 0,
      degradedReason: null,
      evidenceIds: [],
    },
    breakout: { value: null, basis: null, evidenceIds: [], degradedInputs: ["missing_ceiling"] },
    replacement: { kind: "missing", reason: "accepted_c02_c03_have_no_candidate_transaction_evidence" },
  };
  return buildDraftExplanation(input);
}

function recommendation(key: string): Recommendation {
  return { player, reasons: [], equity: 0, explanation: explanation(key) };
}

describe("C04A live structured explanations", () => {
  it("connects the recommendation path to the explained scorer exactly once", () => {
    const source = readFileSync("components/draft/DraftWarRoom.tsx", "utf8");
    expect(source.match(/scoreBoardWithExplanations\(/g)).toHaveLength(1);
    expect(source).not.toMatch(/\bscoreBoard\(/);
    expect(source).toContain("deriveBenchShapeLeagueKey(config)");
    expect(source).toContain("explanation: sp.explanation");
    const renderer = readFileSync("components/draft/LiveRecommendations.tsx", "utf8");
    expect(renderer).toContain("recommendationClaims(recommendation)");
  });

  it("renders deterministic unsupported claims and missing evidence", () => {
    const rec = recommendation("t12-superflex-half-te0.0-b4-ir0");
    expect(recommendationClaims(rec)).toEqual(recommendationClaims(rec));
    const claims = recommendationClaims(rec);
    expect(claims).toContain("Covers RB in week 8 for starter starter-rb.");
    expect(claims).toContain("League evidence: unsupported.");
    expect(claims.join(" ")).toContain("accepted_c02_c03_have_no_candidate_transaction_evidence");
    expect(claims).not.toContain("League evidence: measured.");
  });

  it("renders custom configurations as fallback, never measured", () => {
    const rec = recommendation("custom:12-team-wrte");
    const claims = recommendationClaims(rec);
    expect(claims).toContain("League evidence: fallback.");
    expect(claims.join(" ")).toContain("missing_league_key");
    expect(claims).not.toContain("League evidence: measured.");
  });
});
