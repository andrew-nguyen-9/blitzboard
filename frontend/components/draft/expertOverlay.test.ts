import { describe, expect, it } from "vitest";
import type { PlayerWithValue } from "@/lib/types";
import {
  disagreement,
  matchExpertBoard,
  normalizeExpertName,
  normalizeExpertPosition,
} from "./expertOverlay";

const player = (id: string, name: string, position: "QB" | "RB" | "WR" | "TE" | "K" | "DEF"): PlayerWithValue => ({
  id, sleeper_id: id, espn_id: null, full_name: name, position, nfl_team: null,
  bye_week: null, age: null, years_exp: null, status: null, injury_status: null, value: null,
});
const entry = (name: string, position: string, modelRank = 10) => ({
  name, position, modelRank, marketAdp: 12, risk: "LOW", upside: "HIGH", tier: 1, note: "",
});
const data = (entries: ReturnType<typeof entry>[]) => ({
  version: 1, asOf: "2026-08-26", provenance: "test", boards: { "11": "shared", "12": "shared" }, sharedBoard: entries,
}) as never;

describe("expert overlay", () => {
  it("normalizes punctuation, suffixes, accents, and DEF/DST", () => {
    expect(normalizeExpertName("D'Andre Swift Jr.")).toBe("d andre swift");
    expect(normalizeExpertName("José Núñez III")).toBe("jose nunez");
    expect(normalizeExpertPosition("DEF")).toBe("DST");
  });

  it("matches one normalized name and position", () => {
    const result = matchExpertBoard([player("1", "D'Andre Swift", "RB")], 12, data([entry("D’Andre Swift Jr.", "RB")]))!;
    expect(result.byPlayerId.get("1")?.modelRank).toBe(10);
    expect(result.unmatched).toEqual([]);
  });

  it("surfaces unmatched and ambiguous names without selecting either", () => {
    const players = [player("1", "Chris Jones", "RB"), player("2", "Chris Jones", "RB")];
    const result = matchExpertBoard(players, 12, data([entry("Chris Jones", "RB"), entry("Missing Guy", "WR")]))!;
    expect(result.byPlayerId.size).toBe(0);
    expect(result.ambiguous).toEqual(["Chris Jones"]);
    expect(result.unmatched).toEqual(["Missing Guy"]);
  });

  it("flags only disagreements of at least 24 ranks", () => {
    expect(disagreement(40, 16)).toBe("opportunity");
    expect(disagreement(16, 40)).toBe("landmine");
    expect(disagreement(39, 16)).toBeNull();
  });

  it("is a no-op outside the extracted team counts", () => {
    expect(matchExpertBoard([], 10, data([]))).toBeNull();
    expect(matchExpertBoard([], 12, { boards: {} } as never)).toBeNull();
  });
});
