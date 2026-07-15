// E7 — Full-draft end-to-end simulation.
//
// E1–E6 each ship their own unit tests; this file adds the single **full superflex
// auto-draft** that proves the whole cycle green end-to-end: every team, over many
// seeds, lands the *ideal* superflex bench composition. It reuses the shared draft
// harness (runSnakeDraft + mulberry32 + fillRoster from draft.ts) and the live
// DEFAULT_POLICY chooser (pickForTeam, with E5's bench-quality fold baked in) — no
// bespoke engine, so a red assertion here is a real product defect (see E7 boundary).
//
// Asserted per team, end-to-end:
//   • ≥2 QB rostered            (superflex: QB + OP startable slots need real depth)
//   • ≥1 RB benched             (RB lottery ticket)
//   • ≥1 WR benched             (WR breakout)
//   • ≤1 K benched  &  ≤1 DST benched   (no dead K/DST pileup — never 2+ of either)
import { describe, it, expect } from "vitest";
import { pickForTeam, norm } from "./draftAI";
import { SUPERFLEX_ROSTER, fillRoster } from "./draft";
import { runSnakeDraft, mulberry32 } from "./snakeDraft";
import type { PlayerWithValue } from "./types";

// Player factory — mirrors draftAI.fixtures.test.ts (value-fields in `value`,
// player-fields on the row; proj = vor + replacement).
function mk(
  id: string,
  position: string,
  projPts: number,
  opts: { bye_week?: number | null; nfl_team?: string | null } = {},
): PlayerWithValue {
  const { bye_week = null, nfl_team = null } = opts;
  return {
    id,
    full_name: id,
    position,
    nfl_team,
    bye_week,
    injury_status: null,
    metadata: {},
    value: {
      player_id: id, engine: "vorp", value: projPts, vor: projPts, replacement: 0,
      boom: projPts, bust: projPts, adp: null, rank: null,
    },
  } as PlayerWithValue;
}

// A realistic superflex board: enough depth at every position for 12 teams to each
// fill 10 starters + 6 bench, with the position counts/curves the fixtures suite uses.
function realisticPool(): PlayerWithValue[] {
  const spec: [string, number, number, number][] = [
    ["QB", 60, 300, 120], ["RB", 110, 290, 40], ["WR", 130, 285, 30],
    ["TE", 45, 230, 50], ["K", 24, 140, 118], ["DST", 24, 135, 108],
  ];
  const players: PlayerWithValue[] = [];
  let n = 0;
  for (const [pos, count, top, bot] of spec) {
    for (let k = 0; k < count; k++) {
      const projPts = Math.round(top - ((top - bot) * k) / Math.max(1, count - 1));
      players.push(mk(`${pos}${k}`, pos, projPts, { bye_week: (n % 14) + 1, nfl_team: `T${n % 32}` }));
      n++;
    }
  }
  return players;
}

describe("E7: full 12-team superflex auto-draft → ideal bench composition end-to-end", () => {
  const SEEDS = [1, 7, 42, 100, 314, 2718];

  it.each(SEEDS)(
    "seed %s: every team ≥2 QB, ≥1 RB + ≥1 WR benched, no team benches 2+ K or 2+ DST",
    (seed) => {
      const players = realisticPool();
      const byId = new Map(players.map((p) => [p.id, p]));
      // Default chooser = pickForTeam @ DEFAULT_POLICY — the live, E5-integrated policy.
      const picks = runSnakeDraft(players, { numTeams: 12, rng: mulberry32(seed), randomness: 0 });

      for (let t = 1; t <= 12; t++) {
        const roster = picks.filter((pk) => pk.team === t).map((pk) => byId.get(pk.player.id)!);
        const qbRostered = roster.filter((p) => norm(p.position) === "QB").length;
        expect(qbRostered, `team ${t} QB rostered`).toBeGreaterThanOrEqual(2);

        const bench = fillRoster(roster, SUPERFLEX_ROSTER).bench;
        const benchCount = (pos: string) => bench.filter((p) => norm(p.position) === pos).length;
        expect(benchCount("RB"), `team ${t} bench RB`).toBeGreaterThanOrEqual(1);
        expect(benchCount("WR"), `team ${t} bench WR`).toBeGreaterThanOrEqual(1);
        expect(benchCount("K"), `team ${t} bench K`).toBeLessThanOrEqual(1);
        expect(benchCount("DST"), `team ${t} bench DST`).toBeLessThanOrEqual(1);
      }
    },
  );
});
