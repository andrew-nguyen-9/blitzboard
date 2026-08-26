import { describe, expect, it } from "vitest";
import { defaultConfig } from "@/lib/leagueConfig";
import type { PlayerWithValue } from "@/lib/types";
import {
  availablePlayerIds,
  deserializeManualDraft,
  replacePick,
  serializeManualDraft,
  type ManualDraftState,
} from "./manualDraftState";

const player = (id: string): PlayerWithValue => ({
  id,
  full_name: `Player ${id}`,
  position: "WR",
  nfl_team: "CHI",
  sleeper_id: id,
  espn_id: null,
  bye_week: null,
  age: null,
  years_exp: null,
  status: null,
  injury_status: null,
  value: null,
});

describe("manual draft state", () => {
  it("round-trips the complete autosave payload", () => {
    const state: ManualDraftState = {
      leagueId: "league-12",
      config: defaultConfig(12),
      mySlot: 6,
      picks: [{ pickNo: 1, team: 1, player: player("one") }],
      keepers: [player("kept")],
    };

    expect(deserializeManualDraft(serializeManualDraft(state))).toEqual(state);
  });

  it("replaces a past pick without changing downstream picks", () => {
    const picks = [
      { pickNo: 1, team: 1, player: player("wrong") },
      { pickNo: 2, team: 2, player: player("two") },
      { pickNo: 3, team: 3, player: player("three") },
    ];

    expect(replacePick(picks, 1, player("correct"))).toEqual([
      { pickNo: 1, team: 1, player: player("correct") },
      picks[1],
      picks[2],
    ]);
  });

  it("excludes keepers and drafted players from the available pool", () => {
    const players = [player("available"), player("drafted"), player("kept")];
    const picks = [{ pickNo: 1, team: 1, player: players[1] }];

    expect(availablePlayerIds(players, picks, [players[2]])).toEqual(["available"]);
  });
});
