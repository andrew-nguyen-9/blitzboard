import { readFileSync } from "node:fs";
import React, { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import LiveRecommendations, { recommendationClaims, type Recommendation } from "@/components/draft/LiveRecommendations";
import type { LeagueConfigKey } from "../../.orchestrator-v6/prep/C03-public-interface-v1";
import type { PlayerWithValue } from "@/lib/types";
import { buildDraftExplanation, type DraftExplanationInput } from "@/lib/v6DraftExplanation";
import { acceptedBenchShapeResolver } from "@/lib/v6DraftLiveScoring";

Object.assign(globalThis, { React });

const player = {
  id: "rb2",
  full_name: "Candidate RB",
  position: "RB",
  nfl_team: "AAA",
  bye_week: 8,
  metadata: {},
  value: {
    player_id: "rb2",
    engine: "vorp",
    value: 12,
    vor: 10,
    replacement: 100,
    boom: 25,
    bust: 5,
    adp: 20,
    rank: 18,
  },
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
    expect(source).toContain('component.name === "immediate_lineup"');
    expect(source).toContain("vona: nextTurnEdge >= 10");
    expect(source).not.toContain("vona: equity >= 10");
    const renderer = readFileSync("components/draft/LiveRecommendations.tsx", "utf8");
    expect(renderer).toContain("recommendationClaims(recommendation)");
  });

  it("renders deterministic unsupported claims and missing evidence", () => {
    const rec = recommendation("t12-superflex-half-te0.0-b4-ir0");
    expect(recommendationClaims(rec)).toEqual(recommendationClaims(rec));
    const claims = recommendationClaims(rec);
    expect(claims).toContain("Covers RB in week 8 for starter starter-rb.");
    expect(claims).toContain("League evidence: unsupported.");
    expect(claims.join(" ")).toContain("candidate-level waiver/churn evidence unavailable");
    expect(claims.join(" ")).not.toContain("accepted_c02_c03_have_no_candidate_transaction_evidence");
    expect(rec.explanation.degradedInputs).toContain("accepted_c02_c03_have_no_candidate_transaction_evidence");
    expect(claims).not.toContain("League evidence: measured.");
  });

  it("renders custom configurations as fallback, never measured", () => {
    const rec = recommendation("custom:12-team-wrte");
    const claims = recommendationClaims(rec);
    expect(claims).toContain("League evidence: fallback.");
    expect(claims.join(" ")).toContain("matching league evidence unavailable");
    expect(claims.join(" ")).not.toContain("missing_league_key");
    expect(claims).not.toContain("League evidence: measured.");
  });

  it("renders draft uncertainty as one group limitation", () => {
    const recs = [1, 2, 3, 4].map((index) => ({
      ...recommendation("t12-superflex-half-te0.0-b4-ir0"),
      player: {
        ...player,
        id: `rb${index}`,
        full_name: `Candidate RB ${index}`,
        value: { ...player.value!, player_id: `rb${index}` },
      },
    }));
    const markup = renderToStaticMarkup(createElement(LiveRecommendations, {
      recs,
      isMyPick: true,
      picksUntilMe: 3,
      onDraft: () => {},
    }));

    expect(markup.match(/href="\/players\/rb[1-4]"/g)).toHaveLength(4);
    expect(markup.match(/aria-label="Draft Candidate RB [1-4] to my team"/g)).toHaveLength(4);
    expect(markup.match(/Calibrated projection range unavailable\./g)).toHaveLength(1);
    expect(markup).not.toMatch(/P10|P50|P90|median|5pts|12pts|25pts/i);
  });

  it("keeps the decision path source-first with native names and states", () => {
    const source = readFileSync("components/draft/DraftWarRoom.tsx", "utf8");
    expect(source).toContain('aria-label="Draft input source"');
    expect(source).toContain('aria-label="Draft board view"');
    expect(source).toContain('aria-label="Filter by position"');
    expect(source).toContain('aria-label="Search available players"');
    expect(source).toContain('aria-label="Draft status"');
    expect(source).toContain('aria-label="Available player table"');
    expect(source).toContain("aria-pressed={view === v}");
    expect(source).toContain("aria-pressed={pos === p}");
    expect(source).toContain('<caption className="sr-only">Available players ranked by BlitzBoard</caption>');
    expect(source).toContain('<th scope="row"');
    expect(source).toContain("BlitzBoard rank unavailable");
    expect(source).not.toContain("p.value?.rank ?? i + 1");
    expect(source.indexOf("<LiveRecommendations")).toBeLessThan(source.indexOf("<table"));
    expect(source.match(/<LiveRecommendations/g)).toHaveLength(1);
    expect(source).toMatch(/<details[\s\S]*?<summary>Simulation tools<\/summary>[\s\S]*?Auto-draft all[\s\S]*?<\/details>/);

    for (const file of ["RosterHealthPanel.tsx", "BenchPanel.tsx"]) {
      const panel = readFileSync(`components/draft/${file}`, "utf8");
      expect(panel).not.toMatch(/aria-label=\{(?:inv\.status|band)\}|aria-label="(?:ok|warn)"/);
    }
  });
});
