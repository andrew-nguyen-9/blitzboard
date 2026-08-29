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
import { pickForTeam, pickHumanAdp, candidatePool, DEFAULT_POLICY } from "../lib/draftAI";
import { scoreBoardWithExplanations } from "../lib/v6DraftLiveScoring";
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
  const cachedPlayers = poolFor(year, row);
  const known = new Set(cachedPlayers.map((player) => player.id));
  const extras = (job.extra_players ?? []).filter((player) => !known.has(player.id));
  const overrides = job.player_overrides ?? {};
  let draftPlayers = cachedPlayers;
  if (extras.length || Object.keys(overrides).length) {
    const base = [
      ...cachedPlayers.map((player) => {
        const override = overrides[player.id];
        const projection = override?.projection ?? player.value.vor + player.value.replacement;
        const boom = override?.boom ?? player.value.boom;
        const bust = override?.bust ?? player.value.bust;
        if (override && (
          ![projection, boom, bust].every(Number.isFinite)
          || bust > projection
          || projection > boom
        )) {
          throw new Error(
            `player override for ${player.id} must be ordered finite bust <= projection <= boom`,
          );
        }
        return { ...player, projection, boom, bust };
      }),
      ...extras,
    ];
    const levels = replacementLevels(base, row);
    draftPlayers = [...base]
      .sort((a, b) => b.projection - a.projection || a.id.localeCompare(b.id))
      .map((player, index) => ({
        id: player.id,
        full_name: player.full_name,
        position: player.position,
        nfl_team: player.nfl_team,
        bye_week: player.bye_week,
        injury_status: null,
        metadata: {},
        value: {
          player_id: player.id,
          engine: "vorp",
          value: player.projection,
          vor: Number((player.projection - (levels[player.position] ?? 0)).toFixed(2)),
          replacement: Number((levels[player.position] ?? 0).toFixed(2)),
          boom: player.boom,
          bust: player.bust,
          adp: null,
          rank: index + 1,
        },
      }));
  }
  // Clone per job: poolFor is cached and static-fit jobs must not inherit another
  // benchmark's market snapshot. ADP is the only external input visible to human_adp.
  const players = draftPlayers.map((player) => ({
    ...player,
    value: {
      ...player.value,
      adp: Number.isFinite(job.market_adp?.[player.id]) ? job.market_adp[player.id] : null,
    },
  }));
  const arms = Object.fromEntries(
    Object.entries(job.arms).map(([name, patch]) => {
      const chooser = patch.chooser ?? "v5";
      if (chooser !== "v5" && chooser !== "human_adp") {
        throw new Error(`unknown chooser: ${chooser}`);
      }
      const availability = job.availability_by_arm?.[name];
      if (availability && Object.values(availability).some(
        (value) => !Number.isFinite(value) || value < 0 || value > 1
      )) {
        throw new Error(`availability for ${name} must contain finite probabilities in [0, 1]`);
      }
      return [name, {
        chooser,
        topK: patch.top_k ?? 8,
        policy: { ...DEFAULT_POLICY, ...(patch.policy ?? {}) },
        bench: patch.bench ?? {},
        // Market arms never receive model fields, even if a caller includes a map.
        availability: chooser === "v5" ? availability : undefined,
      }];
    }),
  );

  const picks = [];
  const recommendations = [];
  const recommendationArms = new Set(job.recommendation_arms ?? []);
  for (const name of recommendationArms) {
    if (arms[name]?.chooser !== "v5") {
      throw new Error(`recommendation trace requires a model arm: ${name}`);
    }
  }
  const taken = new Set();
  const nextPickAfter = (team, from) => {
    for (let n = from + 1; n <= total; n++) if (teamOnClock(n, row.teams) === team) return n;
    return total + 1;
  };

  while (picks.length < total) {
    const pickNo = picks.length + 1;
    const team = teamOnClock(pickNo, row.teams);
    const armName = job.assign[team - 1];
    const arm = arms[armName];
    const available = players.filter((p) => !taken.has(p.id));
    if (!available.length) break;
    const ctx = {
      // Market opponents must see the provider's complete ranked board. candidatePool
      // is projection-sorted and would breach the source-independence contract.
      pool: arm.chooser === "human_adp" ? available : candidatePool(available),
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
      availability: arm.availability,
    };
    let chosen;
    if (recommendationArms.has(armName)) {
      const ranked = withBench(arm.bench, () => scoreBoardWithExplanations(
        { ...ctx, randomness: 0 },
        { leagueConfigKey: row.id },
        arm.policy,
      ).slice(0, 4));
      // The trace mirrors the live zero-jitter board, while the synthetic draft keeps
      // its existing seeded 5% policy jitter. Zero jitter consumes no RNG, so opting in
      // cannot alter the selected pick or any downstream draft state.
      chosen = withBench(arm.bench, () => pickForTeam(ctx, arm.policy));
      const selected = chosen ?? available[0];
      recommendations.push({
        pick_no: pickNo,
        team,
        arm: armName,
        recommendation_randomness: 0,
        selected_player_id: selected.id,
        candidates: ranked.map((candidate) => ({
          player_id: candidate.player.id,
          position: candidate.player.position,
          score: candidate.score,
          market_adp: Number.isFinite(candidate.player.value?.adp)
            ? candidate.player.value.adp
            : null,
          explanation: candidate.explanation,
        })),
      });
    } else {
      chosen = arm.chooser === "human_adp"
        ? pickHumanAdp(ctx, { topK: arm.topK })
        : withBench(arm.bench, () => pickForTeam(ctx, arm.policy));
    }
    const resolved = chosen ?? available[0];
    picks.push({ pickNo, team, player: resolved, chooser: arm.chooser });
    taken.add(resolved.id);
  }

  const rosters = Array.from({ length: row.teams }, () => []);
  for (const pk of picks) rosters[pk.team - 1].push(pk.player.id);
  const result = { row_id: row.id, arm_of_seat: job.assign, rosters };
  if (job.include_picks) {
    result.picks = picks.map((pick) => ({
      pick_no: pick.pickNo,
      team: pick.team,
      player_id: pick.player.id,
      position: pick.player.position,
      chooser: pick.chooser,
      market_adp: Number.isFinite(pick.player.value?.adp) ? pick.player.value.adp : null,
    }));
  }
  if (job.recommendation_arms) result.recommendations = recommendations;
  return result;
}

const stdin = readFileSync(0, "utf8");
const req = JSON.parse(stdin);
const year = req.season ?? 2024;
process.stdout.write(
  JSON.stringify({ results: req.jobs.map((j) => draftJob(year, j)) }) + "\n",
);
