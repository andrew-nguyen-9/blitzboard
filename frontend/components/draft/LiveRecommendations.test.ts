import React, { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { LeagueConfigKey } from "../../../.orchestrator-v6/prep/C03-public-interface-v1";
import type { PlayerWithValue } from "@/lib/types";
import { buildDraftExplanation, type DraftExplanationInput } from "@/lib/v6DraftExplanation";
import { acceptedBenchShapeResolver } from "@/lib/v6DraftLiveScoring";
import LiveRecommendations, { recommendationClaims, type Recommendation } from "./LiveRecommendations";
import type { WhyChip } from "./reasons";

Object.assign(globalThis, { React });

const nextTurn: WhyChip = {
  key: "vona",
  label: "next-turn edge",
  title: "Projected lineup value over the estimated next-turn replacement; next-turn survival probability unavailable",
};
const recentRun: WhyChip = {
  key: "run",
  label: "recent run",
  title: "Recent picks are concentrated at this position",
};
const rankGap: WhyChip = {
  key: "value",
  label: "rank/ADP gap · source/date unknown",
  title: "BlitzBoard rank is 12+ picks earlier than stored ADP; source/date unavailable",
};
const alternative: WhyChip = {
  key: "value",
  label: "board alternative",
  title: "One of the four current BlitzBoard options",
};

function recommendation(index: number, reasons: WhyChip[], immediate = index): Recommendation {
  const id = `candidate-${index}`;
  const player = {
    id,
    full_name: `Candidate ${index}`,
    position: ["RB", "WR", "QB", "TE"][index - 1],
    nfl_team: "AAA",
    bye_week: 8,
    metadata: {},
    value: {
      player_id: id,
      engine: "vorp",
      value: 20 - index,
      vor: 10 - index,
      replacement: 100,
      boom: 25,
      bust: 5,
      adp: index === 3 ? null : 20 + index,
      rank: index,
    },
  } as PlayerWithValue;
  const input: DraftExplanationInput = {
    candidateId: id,
    candidatePosition: player.position as "QB" | "RB" | "WR" | "TE",
    ownedAtPosition: 1,
    leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0" as LeagueConfigKey,
    benchSlots: 4,
    resolveBenchShape: acceptedBenchShapeResolver,
    immediate: { value: immediate, slot: "FLEX", replacedStarterId: `starter-${index}`, evidenceIds: [`immediate-${index}`] },
    coverage: {
      expectedStarts: 1,
      value: 2,
      covered: [{ week: 8 + index, slot: "FLEX", starterId: `starter-${index}` }],
      degraded: false,
    },
    contingent: {
      starterId: null,
      eligible: false,
      evidence: "none",
      inheritanceProb: null,
      expectedValue: 0,
      degradedReason: null,
      evidenceIds: [],
    },
    breakout: { value: null, basis: null, evidenceIds: [], degradedInputs: ["missing_ceiling"] },
    replacement: { kind: "missing", reason: "accepted_c02_c03_have_no_candidate_transaction_evidence" },
    scoredTotal: 100 - index,
  };
  return { player, reasons, equity: index === 1 ? 10 : 0, explanation: buildDraftExplanation(input) };
}

const recs = [
  recommendation(1, [nextTurn, rankGap]),
  recommendation(2, [recentRun]),
  recommendation(3, [rankGap], 0),
  recommendation(4, [alternative], 0),
];

function render(input = recs, props: Partial<Parameters<typeof LiveRecommendations>[0]> = {}) {
  return renderToStaticMarkup(createElement(LiveRecommendations, {
    recs: input,
    isMyPick: true,
    picksUntilMe: 0,
    onDraft: () => {},
    ...props,
  }));
}

describe("compact live recommendations", () => {
  it("keeps four candidates ordered with one primary and three alternatives", () => {
    const markup = render();
    expect(markup.match(/<ol/g)).toHaveLength(1);
    expect(markup.match(/<li/g)).toHaveLength(4);
    expect([...markup.matchAll(/href="\/players\/(candidate-[1-4])"/g)].map((match) => match[1])).toEqual([
      "candidate-1", "candidate-2", "candidate-3", "candidate-4",
    ]);
    expect(markup.match(/>Primary</g)).toHaveLength(1);
    expect(markup.match(/>Alternative</g)).toHaveLength(3);
  });

  it("uses only fidelity-eligible visible summaries", () => {
    const compact = render().split("<details")[0];
    expect(compact).toContain(nextTurn.title);
    expect(compact).toContain(recentRun.title);
    expect(compact).toContain("Covers FLEX in week 11 for starter starter-3.");
    expect(compact).toContain(alternative.title);
    expect(compact).not.toContain(rankGap.title);
    expect(compact).toContain("+10.0 projected lineup pts");
    expect(compact).not.toContain(" eq");
  });

  it("keeps every full claim and reason in one native disclosure", () => {
    const markup = render();
    const expanded = markup.slice(markup.indexOf("<details"));
    expect(markup.match(/<details/g)).toHaveLength(1);
    expect(markup).toContain("Full evidence for 4 candidates");
    for (const rec of recs) {
      expect(expanded).toContain(rec.player.full_name);
      for (const reason of rec.reasons) expect(expanded).toContain(`${reason.label}: ${reason.title}`);
      for (const claim of recommendationClaims(rec)) expect(expanded).toContain(claim);
    }
    expect(expanded).toContain("Calibrated projection range unavailable.");
    expect(markup).not.toMatch(/P10|P50|P90|median|5pts|12pts|25pts/i);
  });

  it("shows one group limitation and gates player-specific draft actions", () => {
    const markup = render();
    expect(markup.match(/Limited evidence/g)).toHaveLength(1);
    expect(markup.match(/aria-label="Draft Candidate [1-4] to my team"/g)).toHaveLength(4);
    expect(render(recs, { isMyPick: false })).not.toContain("aria-label=\"Draft Candidate");

    const measured = recs.map((rec) => ({
      ...rec,
      explanation: {
        ...rec.explanation,
        degradedInputs: [],
        leagueEvidence: { ...rec.explanation.leagueEvidence, presentationState: "measured" as const, degraded: false },
      },
    }));
    expect(render(measured)).not.toContain("Limited evidence");
  });

  it("retains mixed-ADP candidates in early, middle, and late positions", () => {
    for (const missingIndex of [0, 1, 3]) {
      const shaped = recs.map((rec, index) => ({
        ...rec,
        player: { ...rec.player, value: { ...rec.player.value!, adp: index === missingIndex ? null : 20 + index } },
      }));
      const markup = render(shaped);
      expect(markup.match(/href="\/players\/candidate-[1-4]"/g)).toHaveLength(4);
    }
  });

  it("cuts default explanation rows by at least half without deleting expanded claims", () => {
    const markup = render();
    const compact = markup.split("<details")[0];
    const baselineRows = recs.reduce((total, rec) => total + recommendationClaims(rec).length, 0);
    expect(compact.match(/aria-label="Summary for Candidate [1-4]"/g)).toHaveLength(4);
    expect(4).toBeLessThanOrEqual(baselineRows / 2);
  });
});
