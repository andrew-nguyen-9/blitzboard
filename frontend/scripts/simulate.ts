// Offline draft simulator harness — runs the REAL draftAI for a 12-team snake and
// reports per-slot team strength, measured two ways:
//   • shaped value sum  (the draft-priority metric)
//   • projected points  (vor + replacement = real fantasy points — the honest one)
// Run: npx tsx scripts/simulate.ts
import { readFileSync } from "node:fs";
import { createClient } from "@supabase/supabase-js";
import { runSnakeDraft } from "../lib/snakeDraft";
import { fillRoster, SUPERFLEX_ROSTER, BENCH_SIZE } from "../lib/draft";
import type { PlayerWithValue } from "../lib/types";

// load env from .env.local
const env: Record<string, string> = {};
for (const line of readFileSync(new URL("../.env.local", import.meta.url), "utf8").split("\n")) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}
const sb = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

async function loadPlayers(): Promise<PlayerWithValue[]> {
  const out: PlayerWithValue[] = [];
  for (let start = 0; ; start += 1000) {
    const { data } = await sb
      .from("player_value")
      .select("value,vor,replacement,boom,bust,adp,rank,player_id,players!inner(id,full_name,position,nfl_team,bye_week,age,years_exp,sleeper_id,espn_id,injury_status,metadata)")
      .eq("engine", "vorp").order("rank").range(start, start + 999);
    const rows = data ?? [];
    for (const r of rows as any[]) out.push({ ...(r.players), value: { player_id: r.player_id, engine: "vorp", value: r.value, vor: r.vor, replacement: r.replacement, boom: r.boom, bust: r.bust, adp: r.adp, rank: r.rank } });
    if (rows.length < 1000) break;
  }
  return out;
}

const points = (p: PlayerWithValue) => (p.value?.vor ?? 0) + (p.value?.replacement ?? 0);

function lineupPoints(roster: PlayerWithValue[]): number {
  // sum projected POINTS of the optimal starting lineup (need-aware)
  const fill = fillRoster(roster, SUPERFLEX_ROSTER);
  return fill.starters.reduce((s, slot) => s + (slot.player ? points(slot.player) : 0), 0);
}

async function main() {
  const numTeams = 12;
  const ROSTER_SPOTS = SUPERFLEX_ROSTER.length + BENCH_SIZE;
  const totalSpots = numTeams * ROSTER_SPOTS;
  const players = await loadPlayers();
  console.log(`loaded ${players.length} players · ${numTeams} teams × ${ROSTER_SPOTS} = ${totalSpots} picks\n`);

  const picks = runSnakeDraft(players, { numTeams });

  // per-team measures
  console.log("slot  startPts   shapedVal   roster(starters)");
  const rows: { slot: number; pts: number; shaped: number }[] = [];
  for (let slot = 1; slot <= numTeams; slot++) {
    const roster = picks.filter((p) => p.team === slot).map((p) => p.player);
    const pts = lineupPoints(roster);
    const shaped = fillRoster(roster, SUPERFLEX_ROSTER).projectedPoints;
    rows.push({ slot, pts, shaped });
    const starters = fillRoster(roster, SUPERFLEX_ROSTER).starters.filter((s) => s.player).map((s) => `${s.slot}:${s.player!.full_name.split(" ").pop()}`).join(" ");
    console.log(`${String(slot).padStart(3)}  ${pts.toFixed(0).padStart(8)}  ${shaped.toFixed(0).padStart(10)}   ${starters}`);
  }
  const early = rows.slice(0, 5), late = rows.slice(5);
  const avg = (a: typeof rows, k: "pts" | "shaped") => a.reduce((s, r) => s + r[k], 0) / a.length;
  console.log(`\nPROJECTED POINTS — early(1-5) avg ${avg(early, "pts").toFixed(0)} · late(6-12) avg ${avg(late, "pts").toFixed(0)} · spread ${(avg(early, "pts") - avg(late, "pts")).toFixed(0)}`);
  console.log(`SHAPED VALUE   — early(1-5) avg ${avg(early, "shaped").toFixed(0)} · late(6-12) avg ${avg(late, "shaped").toFixed(0)} · spread ${(avg(early, "shaped") - avg(late, "shaped")).toFixed(0)}`);
}
main();
