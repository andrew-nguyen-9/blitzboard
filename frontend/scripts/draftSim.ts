// Node bridge: run one 12-team superflex snake draft through a selectable policy for the
// backtest harness. Reads pool+config+seed on stdin, emits rosters on stdout. Deterministic
// per seed so the Python harness gets identical drafts on re-runs. The draft loop lives in
// lib/snakeDraft.ts and is shared with scripts/simulate.ts — backtest and board run the same
// code (D7). Run: node_modules/.bin/tsx scripts/draftSim.ts   (reads JSON config on stdin)
import { readFileSync } from "node:fs";
import { runSnakeDraft, mulberry32 } from "../lib/snakeDraft";
import { pickForTeam, pickRawVorp, pickAdp, DEFAULT_POLICY } from "../lib/draftAI";
import type { AIContext, PolicyParams } from "../lib/draftAI";
import type { PlayerWithValue } from "../lib/types";

const cfg = JSON.parse(readFileSync(0, "utf8")) as {
  players: PlayerWithValue[];
  numTeams: number;
  seed: number;
  policy: string;
  params?: Partial<PolicyParams>; // optional override for v2 ablation runs (v2.4.3)
};

// Policy registry. "v2" runs the real policy (optionally with an ablation params override);
// "rawvorp" and "adp" are the naive baselines. Fail loudly on an unknown policy so a backtest
// can never silently compare a policy against itself.
const params: PolicyParams = { ...DEFAULT_POLICY, ...(cfg.params ?? {}) };
const CHOOSERS: Record<string, (ctx: AIContext) => PlayerWithValue | null> = {
  v2: (ctx) => pickForTeam(ctx, params),
  rawvorp: pickRawVorp,
  adp: pickAdp,
};

const chooser = CHOOSERS[cfg.policy ?? "v2"];
if (!chooser) {
  process.stderr.write(`draftSim: unknown policy "${cfg.policy}" (known: ${Object.keys(CHOOSERS).join(", ")})\n`);
  process.exit(2);
}

const picks = runSnakeDraft(cfg.players, { numTeams: cfg.numTeams, rng: mulberry32(cfg.seed), chooser });

const rosters: string[][] = Array.from({ length: cfg.numTeams }, () => []);
for (const pk of picks) rosters[pk.team - 1].push(pk.player.id);
process.stdout.write(JSON.stringify({ rosters }));
