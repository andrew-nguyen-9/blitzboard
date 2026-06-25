// Smoke: the bridge is deterministic per seed, drafts 12 full rosters, no dup picks.
// Run from frontend/: node scripts/draftSim.smoke.mjs
import { spawnSync } from "node:child_process";

const players = Array.from({ length: 200 }, (_, i) => ({
  id: `pl${i}`,
  full_name: `Player ${i}`,
  position: ["QB", "RB", "WR", "TE", "K", "DST"][i % 6],
  bye_week: (i % 14) + 1,
  nfl_team: `T${i % 32}`,
  metadata: {},
  value: { vor: 200 - i, replacement: 50, boom: 220 - i, bust: 180 - i, adp: i + 1, rank: i + 1 },
}));
const input = JSON.stringify({ players, numTeams: 12, seed: 42, policy: "v2" });
const run = () => {
  const r = spawnSync("node_modules/.bin/tsx", ["scripts/draftSim.ts"], { input, encoding: "utf8" });
  if (r.status !== 0) {
    console.error("draftSim exited", r.status, r.stderr);
    process.exit(1);
  }
  return JSON.parse(r.stdout);
};

const a = run();
const b = run();
if (JSON.stringify(a) !== JSON.stringify(b)) {
  console.error("NON-DETERMINISTIC");
  process.exit(1);
}
if (a.rosters.length !== 12) {
  console.error("wrong team count", a.rosters.length);
  process.exit(1);
}
const drafted = a.rosters.flat();
if (new Set(drafted).size !== drafted.length) {
  console.error("duplicate picks");
  process.exit(1);
}
console.log(`ok draftSim.smoke (12 teams × ${a.rosters[0].length} picks, deterministic)`);
