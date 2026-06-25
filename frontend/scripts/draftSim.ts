// Node bridge: run one 12-team superflex snake draft through the SHARED policy
// (pickForTeam, via runSnakeDraft) for the backtest harness. Reads pool+config+seed
// on stdin, emits rosters on stdout. Deterministic per seed so the Python harness gets
// identical drafts on re-runs. The draft loop lives in lib/snakeDraft.ts and is shared
// with scripts/simulate.ts — backtest and board run the same code (D7).
// Run: node_modules/.bin/tsx scripts/draftSim.ts   (reads JSON config on stdin)
import { readFileSync } from "node:fs";
import { runSnakeDraft, mulberry32 } from "../lib/snakeDraft";
import type { PlayerWithValue } from "../lib/types";

const cfg = JSON.parse(readFileSync(0, "utf8")) as {
  players: PlayerWithValue[];
  numTeams: number;
  seed: number;
  policy: string;
};

// Only the v2 policy exists today; a future ablation (v2.4.3) will branch here. Fail
// loudly on an unknown policy so a backtest can never silently compare "v2 vs v2".
const KNOWN_POLICIES = new Set(["v2"]);
if (cfg.policy && !KNOWN_POLICIES.has(cfg.policy)) {
  process.stderr.write(`draftSim: unknown policy "${cfg.policy}" (known: ${[...KNOWN_POLICIES].join(", ")})\n`);
  process.exit(2);
}

const picks = runSnakeDraft(cfg.players, { numTeams: cfg.numTeams, rng: mulberry32(cfg.seed) });

const rosters: string[][] = Array.from({ length: cfg.numTeams }, () => []);
for (const pk of picks) rosters[pk.team - 1].push(pk.player.id);
process.stdout.write(JSON.stringify({ rosters }));
