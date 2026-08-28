import { describe, expect, it } from "vitest";
import type { RosterSlot } from "./draft";
import { scoreBoard, type AIContext } from "./draftAI";
import { defaultTeams, type LeagueConfig } from "./leagueConfig";
import { formatDraftExplanation, type ReplacementChurnEvidence } from "./v6DraftExplanation";
import { deriveBenchShapeLeagueKey, scoreBoardWithExplanations } from "./v6DraftLiveScoring";
import type { PlayerWithValue } from "./types";

function player(id: string, position: string, projection: number, options: {
  bye?: number | null;
  team?: string;
  depth?: number;
  boom?: number | null;
} = {}): PlayerWithValue {
  return {
    id,
    full_name: id,
    position,
    nfl_team: options.team ?? "AAA",
    bye_week: options.bye === undefined ? 8 : options.bye,
    injury_status: null,
    metadata: { depth_chart_order: options.depth ?? 1 },
    value: {
      player_id: id,
      engine: "vorp",
      value: projection,
      vor: projection - 100,
      replacement: 100,
      boom: options.boom === undefined ? projection - 80 : options.boom,
      bust: projection - 140,
      adp: null,
      rank: null,
    },
  } as PlayerWithValue;
}

const SLOTS: RosterSlot[] = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "WR", eligible: ["WR"] },
  { slot: "TE", eligible: ["TE"] },
  { slot: "FLEX", eligible: ["RB", "WR", "TE"] },
  { slot: "OP", eligible: ["QB", "RB", "WR", "TE"] },
];

function context(): AIContext {
  const teamPicks = [
    player("qb1", "QB", 300, { bye: 9 }),
    player("rb1", "RB", 230, { bye: 7, depth: 1 }),
    player("wr1", "WR", 220, { bye: 10 }),
    player("te1", "TE", 170, { bye: 11 }),
  ];
  const pool = [
    player("rb2", "RB", 190, { bye: 8, depth: 2 }),
    player("wr2", "WR", 180, { bye: 6 }),
  ];
  return {
    pool,
    teamPicks,
    roster: SLOTS,
    benchSize: 4,
    allPicks: [],
    numTeams: 12,
    picksUntilNext: 11,
    round: 8,
    totalRounds: 10,
    randomness: 0,
  };
}

describe("C04 live scoring and explanation integration", () => {
  it("preserves shipped ranking and numeric scores exactly", () => {
    const ctx = context();
    const shipped = scoreBoard(ctx);
    const explained = scoreBoardWithExplanations(ctx, {
      leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0",
    });
    expect(explained.map((pick) => pick.player.id)).toEqual(shipped.map((pick) => pick.player.id));
    expect(explained.map((pick) => pick.score)).toEqual(shipped.map((pick) => pick.score));
  });

  it("decorates every shipped score with six structured components and an exact reconciliation", () => {
    const picks = scoreBoardWithExplanations(context(), {
      leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0",
    });
    expect(picks).toHaveLength(2);
    for (const pick of picks) {
      expect(pick.explanation.components.map((component) => component.name)).toEqual([
        "immediate_lineup",
        "bye_absence_coverage",
        "contingent_role",
        "breakout_option",
        "waiver_replacement_churn",
        "redundancy_cost",
      ]);
      expect(pick.explanation.score).toBe(pick.score);
      expect(pick.explanation.componentTotal + pick.explanation.legacyPolicyResidual).toBeCloseTo(pick.score);
      expect(pick.trace.score).toBe(pick.score);
    }
  });

  it("presents accepted C03 canonical rows as unsupported and degraded", () => {
    const [pick] = scoreBoardWithExplanations(context(), {
      leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0",
    });
    expect(pick.explanation.leagueEvidence).toMatchObject({
      artifactEvidenceStatus: "unsupported",
      presentationState: "unsupported",
      degraded: true,
      degradedReason: "unsupported_evidence",
    });
    expect(formatDraftExplanation(pick.explanation)).toContain("League evidence: unsupported.");
  });

  it("degrades custom/unrepresentable league keys through the accepted resolver fallback", () => {
    const [pick] = scoreBoardWithExplanations(context(), { leagueConfigKey: "custom:12-team-wrte" });
    expect(pick.explanation.leagueEvidence).toMatchObject({
      artifactEvidenceStatus: "unsupported",
      presentationState: "fallback",
      degradedReason: "missing_league_key",
    });
  });

  it("does not invent candidate transaction value when accepted C02/C03 lacks it", () => {
    const [pick] = scoreBoardWithExplanations(context(), {
      leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0",
    });
    const replacement = pick.explanation.components.find((component) => component.name === "waiver_replacement_churn");
    expect(replacement).toMatchObject({
      value: null,
      state: "unsupported",
      degradedInputs: ["accepted_c02_c03_have_no_candidate_transaction_evidence"],
    });
  });

  it("adapts explicit candidate evidence when supplied without browser recomputation", () => {
    const evidence: ReplacementChurnEvidence = {
      kind: "candidate_transaction",
      evidenceId: "external-candidate-transaction",
      addedPlayerId: "rb2",
      droppedPlayerId: "old-rb",
      remainingHorizonGain: 5,
      transactionCost: 2,
      netValue: 3,
      outcomeRefs: [],
    };
    const pick = scoreBoardWithExplanations(context(), {
      leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0",
      replacementEvidence: { rb2: evidence },
    }).find((item) => item.player.id === "rb2")!;
    expect(pick.explanation.replacementChurn).toBe(evidence);
    expect(pick.explanation.components.find((component) => component.name === "waiver_replacement_churn")).toMatchObject({
      value: 3,
      evidenceIds: ["external-candidate-transaction"],
    });
  });

  it("keeps per-pick browser runtime deterministic and simulation-free", () => {
    const first = scoreBoardWithExplanations(context(), { leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0" });
    const second = scoreBoardWithExplanations(context(), { leagueConfigKey: "t12-superflex-half-te0.0-b4-ir0" });
    expect(first.map((pick) => pick.trace)).toEqual(second.map((pick) => pick.trace));
    for (const pick of first) {
      expect(pick.explanation.runtime).toEqual({
        resolverCalls: 1,
        simulationTrials: 0,
        seasonRollouts: 0,
        monteCarloSamples: 0,
      });
    }
  });
});

describe("deriveBenchShapeLeagueKey", () => {
  function config(overrides: Partial<LeagueConfig> = {}): LeagueConfig {
    return {
      source: "manual",
      leagueId: null,
      name: "test",
      numTeams: 12,
      rosterSlots: SLOTS,
      benchSize: 4,
      tePremium: 0.5,
      irSlots: 1,
      scoringLabel: "Half-PPR · Superflex",
      teams: defaultTeams(12),
      ...overrides,
    };
  }

  it("derives every frozen factor from the actual normalized configuration", () => {
    expect(deriveBenchShapeLeagueKey(config())).toBe("t12-superflex-half-te0.5-b4-ir1");
    expect(deriveBenchShapeLeagueKey(config({
      rosterSlots: SLOTS.filter((slot) => slot.slot !== "OP"),
      scoringLabel: "Standard",
      tePremium: 0,
      irSlots: 0,
    }))).toBe("t12-1qb-std-te0.0-b4-ir0");
    expect(deriveBenchShapeLeagueKey(config({
      rosterSlots: [{ slot: "QB", eligible: ["QB"] }, { slot: "QB", eligible: ["QB"] }],
      scoringLabel: "PPR",
    }))).toBe("t12-2qb-ppr-te0.5-b4-ir1");
  });

  it.each([
    ["unsupported teams", { numTeams: 8 }],
    ["unsupported bench", { benchSize: 6 }],
    ["missing TE evidence", { tePremium: undefined }],
    ["missing IR evidence", { irSlots: undefined }],
    ["custom scoring", { scoringLabel: "Custom" }],
  ] as const)("falls back explicitly for %s", (_label, override) => {
    expect(deriveBenchShapeLeagueKey(config(override))).toMatch(/^custom:/);
  });
});
