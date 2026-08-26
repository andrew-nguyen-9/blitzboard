// e10 evaluation bridge — drives the REAL TypeScript draft policy from Python.
//
//   cd frontend && node_modules/.bin/tsx scripts/draft-eval.mjs < jobs.json > out.json
//
// v5-architecture §5 is binding: the static fit must score `lib/draftAI.ts` + `lib/benchScore.ts`
// themselves, never a Python re-implementation (two copies of the formula silently drift — the
// failure mode this cycle exists to end). e5's `static_proxy` seat is a stand-in; this replaces it.
//
// Contract — stdin ONE json object:
//   { season, jobs: [ { row, seed, arms: {A: patch, B: patch}, assign: ["A","B",...] } ] }
// where `row` is an e7a league_matrix row, `assign[t]` names the arm seat t+1 plays, and a
// `patch` is { policy?: <PolicyParams subset>, bench?: { SF_MULTIPLIER?, SF_RB_WEIGHTS?,
// SF_WR_WEIGHTS?, SF_QB_WEIGHTS?, GENERAL_WEIGHTS?, GENERAL_PENALTIES? } }.
// stdout ONE json object: { results: [ { row_id, arm_of_seat, rosters: [[player_id,...]] } ] }.
//
// Cost: ONE node process per BATCH of drafts (never per pick, and not even per draft — the tsx
// compile is ~1 s and would otherwise dominate). Fully deterministic: same stdin -> same stdout.
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { pickForTeam, candidatePool, DEFAULT_POLICY } from "../lib/draftAI";
import {
  GENERAL_WEIGHTS,
  GENERAL_PENALTIES,
  SF_QB_WEIGHTS,
  SF_RB_WEIGHTS,
  SF_WR_WEIGHTS,
  SF_MULTIPLIER,
} from "../lib/benchScore";
import { mulberry32 } from "../lib/snakeDraft";
import { teamOnClock } from "../lib/draft";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "..", "..", "fixtures");

// Mirrors leagueMatrix.toLeagueConfig (inlined for the same ESM/CJS reason as gen-golden-drafts).
const ELIGIBLE = {
  QB: ["QB"], RB: ["RB"], WR: ["WR"], TE: ["TE"],
  FLEX: ["RB", "WR", "TE"], SUPERFLEX: ["QB", "RB", "WR", "TE"],
  K: ["K"], DST: ["DST", "DEF"],
};

// benchScore's tables are module consts with no injection seam (they are shipped constants, not
// runtime config). The harness mutates them around each draft and restores after.
// ponytail: mutate-and-restore beats threading a config object through 8 call sites for a fit rig.
const BENCH_TABLES = {
  GENERAL_WEIGHTS, GENERAL_PENALTIES,
  SF_QB_WEIGHTS, SF_RB_WEIGHTS, SF_WR_WEIGHTS, SF_MULTIPLIER,
};
function withBench(patch, fn) {
  const saved = Object.fromEntries(
    Object.entries(BENCH_TABLES).map(([k, v]) => [k, { ...v }]),
  );
  try {
    for (const [k, v] of Object.entries(patch ?? {})) Object.assign(BENCH_TABLES[k], v);
    return fn();
  } finally {
    for (const [k, v] of Object.entries(saved)) {
      for (const key of Object.keys(BENCH_TABLES[k])) delete BENCH_TABLES[k][key];
      Object.assign(BENCH_TABLES[k], v);
    }
  }
}

const sliceCache = new Map();
const season = (year) => {
  if (!sliceCache.has(year)) {
    sliceCache.set(year, JSON.parse(readFileSync(join(FIXTURES, "seasons", `${year}.json`), "utf8")));
  }
  return sliceCache.get(year);
};

// Starters at a position across the league set the VORP replacement level (identical to
// gen-golden-drafts.mjs so a fit is measured on the same board the goldens froze).
function replacementLevels(players, row) {
  const perTeam = {};
  for (const [slot, n] of Object.entries(row.starting_slots)) {
    for (const pos of ELIGIBLE[slot] ?? [slot]) perTeam[pos] = (perTeam[pos] ?? 0) + n;
  }
  const levels = {};
  for (const pos of ["QB", "RB", "WR", "TE", "K", "DST"]) {
    const atPos = players.filter((p) => p.position === pos).sort((a, b) => b.projection - a.projection);
    const idx = Math.min(atPos.length - 1, Math.round((perTeam[pos] ?? 1) * row.teams));
    levels[pos] = atPos.length ? atPos[idx].projection : 0;
  }
  return levels;
}

const poolCache = new Map();
function poolFor(year, row) {
  const ck = `${year}|${row.id}`;
  if (poolCache.has(ck)) return poolCache.get(ck);
  const key = `${row.scoring}:${row.te_premium}`;
  const base = season(year).players.map((p) => ({
    id: p.player_id, full_name: p.name, position: p.position, nfl_team: p.nfl_team,
    bye_week: p.bye_week,
    projection: p.preseason[key].projection, boom: p.preseason[key].boom, bust: p.preseason[key].bust,
  }));
  const levels = replacementLevels(base, row);
  const ranked = [...base].sort((a, b) => b.projection - a.projection || (a.id < b.id ? -1 : 1));
  const out = ranked.map((p, i) => ({
    id: p.id, full_name: p.full_name, position: p.position, nfl_team: p.nfl_team,
    bye_week: p.bye_week, injury_status: null, metadata: {},
    value: {
      player_id: p.id, engine: "vorp", value: p.projection,
      vor: Number((p.projection - (levels[p.position] ?? 0)).toFixed(2)),
      replacement: Number((levels[p.position] ?? 0).toFixed(2)),
      boom: p.boom, bust: p.bust, adp: null, rank: i + 1,
    },
  }));
  poolCache.set(ck, out);
  return out;
}

// One snake draft where seat t plays arm `assign[t-1]`. Mirrored-half-league A/B (e6's method):
// both arms sit in the SAME draft, so the per-seat paired difference cancels the draft-slot effect.
function draftJob(year, job) {
  const row = job.row;
  const roster = Object.entries(row.starting_slots).flatMap(([slot, n]) =>
    Array.from({ length: n }, () => ({ slot, eligible: ELIGIBLE[slot] ?? [slot] })),
  );
  const rounds = roster.length + row.bench_slots;
  const total = row.teams * rounds;
  const rng = mulberry32(job.seed);
  const players = poolFor(year, row);
  const arms = Object.fromEntries(
    Object.entries(job.arms).map(([name, patch]) => [
      name, { policy: { ...DEFAULT_POLICY, ...(patch.policy ?? {}) }, bench: patch.bench ?? {} },
    ]),
  );

  const picks = [];
  const taken = new Set();
  const nextPickAfter = (team, from) => {
    for (let n = from + 1; n <= total; n++) if (teamOnClock(n, row.teams) === team) return n;
    return total + 1;
  };

  while (picks.length < total) {
    const pickNo = picks.length + 1;
    const team = teamOnClock(pickNo, row.teams);
    const arm = arms[job.assign[team - 1]];
    const available = players.filter((p) => !taken.has(p.id));
    if (!available.length) break;
    const ctx = {
      pool: candidatePool(available),
      teamPicks: picks.filter((p) => p.team === team).map((p) => p.player),
      roster,
      benchSize: row.bench_slots,
      allPicks: picks,
      numTeams: row.teams,
      picksUntilNext: nextPickAfter(team, pickNo) - pickNo,
      round: Math.ceil(pickNo / row.teams),
      totalRounds: rounds,
      randomness: 0.05,
      rng,
    };
    const chosen = withBench(arm.bench, () => pickForTeam(ctx, arm.policy)) ?? available[0];
    picks.push({ pickNo, team, player: chosen });
    taken.add(chosen.id);
  }

  const rosters = Array.from({ length: row.teams }, () => []);
  for (const pk of picks) rosters[pk.team - 1].push(pk.player.id);
  return { row_id: row.id, arm_of_seat: job.assign, rosters };
}

const stdin = readFileSync(0, "utf8");
const req = JSON.parse(stdin);
const year = req.season ?? 2024;
process.stdout.write(
  JSON.stringify({ results: req.jobs.map((j) => draftJob(year, j)) }) + "\n",
);
