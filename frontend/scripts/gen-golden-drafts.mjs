// E7b golden-draft generator — freezes TODAY's draftAI behaviour into fixtures/golden_drafts/.
//
//   cd frontend && node_modules/.bin/tsx scripts/gen-golden-drafts.mjs [--check] [--row ID]
//
// Runs the CURRENT, UNMODIFIED lib/draftAI over every e7a smoke() matrix row against a fixed
// season slice with a fixed seed, and writes one JSON per row (full pick sequence + rosters).
// e10 uses these to prove a policy fit CHANGED something; e8 asserts invariants on real boards.
//
// Determinism contract: same fixtures in -> byte-identical files out. Nothing here reads the
// clock, the network, Math.random or the environment; every float that could wobble is kept out
// of the output (picks carry ids/positions only). `--check` regenerates in memory and diffs
// against the checked-in bytes (exit 1 on drift) — that is what engine/tests/test_corpus.py runs.
//
// The seed hook lives HERE, not in draftAI: mulberry32(seed) is passed in as ctx.rng, exactly the
// hook AIContext already exposes. draftAI.ts is never touched — that is the entire point.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { pickForTeam, candidatePool, norm } from "../lib/draftAI";
import { fillRoster } from "../lib/draft";
import { mulberry32 } from "../lib/snakeDraft";
import { teamOnClock } from "../lib/draft";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "..", "..", "fixtures");
const OUT_DIR = join(FIXTURES, "golden_drafts");

// Kept in lockstep with engine/blitz_engine/testing/corpus.py (GOLDEN_SEASON / GOLDEN_SEED).
const SEASON = 2024;
const SEED = 20260825;

// Mirrors leagueMatrix.toLeagueConfig's map. Inlined rather than imported because that module is
// CJS-flavoured (`__dirname`) and this script runs as ESM; the fixture JSON is the shared source.
const ELIGIBLE = {
  QB: ["QB"],
  RB: ["RB"],
  WR: ["WR"],
  TE: ["TE"],
  FLEX: ["RB", "WR", "TE"],
  SUPERFLEX: ["QB", "RB", "WR", "TE"],
  K: ["K"],
  DST: ["DST", "DEF"],
};

const matrix = JSON.parse(readFileSync(join(FIXTURES, "league_matrix.json"), "utf8"));
const slice = JSON.parse(readFileSync(join(FIXTURES, "seasons", `${SEASON}.json`), "utf8"));

const scoringKey = (scoring, tePremium) => `${scoring}:${tePremium}`;

// Starters at a position across the league set the VORP replacement level (FLEX/SUPERFLEX count
// toward every position they accept, matching how those slots actually get filled).
function replacementLevels(players, row) {
  const perTeam = {};
  for (const [slot, n] of Object.entries(row.starting_slots)) {
    for (const pos of ELIGIBLE[slot] ?? [slot]) perTeam[pos] = (perTeam[pos] ?? 0) + n;
  }
  const levels = {};
  for (const pos of ["QB", "RB", "WR", "TE", "K", "DST"]) {
    const atPos = players
      .filter((p) => p.position === pos)
      .sort((a, b) => b.projection - a.projection);
    const idx = Math.min(atPos.length - 1, Math.round((perTeam[pos] ?? 1) * row.teams));
    levels[pos] = atPos.length ? atPos[idx].projection : 0;
  }
  return levels;
}

// The season slice -> the PlayerWithValue board draftAI consumes, in the row's scoring rules.
function poolFor(row) {
  const key = scoringKey(row.scoring, row.te_premium);
  const base = slice.players.map((p) => ({
    id: p.player_id,
    full_name: p.name,
    position: p.position,
    nfl_team: p.nfl_team,
    bye_week: p.bye_week,
    injury_status: null,
    metadata: {},
    projection: p.preseason[key].projection,
    boom: p.preseason[key].boom,
    bust: p.preseason[key].bust,
  }));
  const levels = replacementLevels(base, row);
  const ranked = [...base].sort(
    (a, b) => b.projection - a.projection || (a.id < b.id ? -1 : 1),
  );
  return ranked.map((p, i) => ({
    id: p.id,
    full_name: p.full_name,
    position: p.position,
    nfl_team: p.nfl_team,
    bye_week: p.bye_week,
    injury_status: null,
    metadata: {},
    value: {
      player_id: p.id,
      engine: "vorp",
      value: p.projection,
      vor: Number((p.projection - (levels[p.position] ?? 0)).toFixed(2)),
      replacement: Number((levels[p.position] ?? 0).toFixed(2)),
      boom: p.boom,
      bust: p.bust,
      adp: null, // the store carries no ADP (see corpus.py module docs)
      rank: i + 1,
    },
  }));
}

// The snake loop, honouring the ROW's roster shape. runSnakeDraft hardcodes SUPERFLEX_ROSTER +
// BENCH_SIZE, so the matrix's teams/starting_slots/bench_slots could not drive it; this is the
// same loop with those three read from the row. The POLICY call is untouched draftAI.
function draftRow(row) {
  const roster = Object.entries(row.starting_slots).flatMap(([slot, n]) =>
    Array.from({ length: n }, () => ({ slot, eligible: ELIGIBLE[slot] ?? [slot] })),
  );
  const rounds = roster.length + row.bench_slots;
  const total = row.teams * rounds;
  const rng = mulberry32(SEED);
  const players = poolFor(row);

  const picks = [];
  const taken = new Set();
  const nextPickAfter = (team, from) => {
    for (let n = from + 1; n <= total; n++) if (teamOnClock(n, row.teams) === team) return n;
    return total + 1;
  };

  while (picks.length < total) {
    const pickNo = picks.length + 1;
    const team = teamOnClock(pickNo, row.teams);
    const available = players.filter((p) => !taken.has(p.id));
    if (!available.length) break;
    // candidatePool() is the live UI auto-draft path (DraftWarRoom.runSim), not runSnakeDraft's
    // full-pool path — golden drafts lock the behaviour users actually get.
    const pool = candidatePool(available);
    const chosen =
      pickForTeam({
        pool,
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
      }) ?? available[0];
    picks.push({ pickNo, team, player: chosen });
    taken.add(chosen.id);
  }

  const rosters = Array.from({ length: row.teams }, () => []);
  for (const pk of picks) rosters[pk.team - 1].push(pk.player.id);

  return {
    row_id: row.id,
    season: SEASON,
    seed: SEED,
    num_teams: row.teams,
    rounds,
    starting_slots: row.starting_slots,
    bench_slots: row.bench_slots,
    scoring: row.scoring,
    te_premium: row.te_premium,
    picks: picks.map((p) => ({
      pick: p.pickNo,
      team: p.team,
      player_id: p.player.id,
      position: norm(p.player.position),
    })),
    rosters,
    // Denormalised so a consumer can assert legality without re-deriving fillRoster.
    starters: rosters.map((ids) => {
      const byId = new Map(players.map((p) => [p.id, p]));
      const filled = fillRoster(ids.map((id) => byId.get(id)), roster);
      return filled.starters.map((s) => ({ slot: s.slot, player_id: s.player?.id ?? null }));
    }),
  };
}

const args = process.argv.slice(2);
const check = args.includes("--check");
const only = args.includes("--row") ? args[args.indexOf("--row") + 1] : null;
const smokeIds = new Set(matrix.smoke);
const rows = matrix.rows.filter((r) => smokeIds.has(r.id) && (!only || r.id === only));
if (!rows.length) {
  console.error(`gen-golden-drafts: no smoke rows matched${only ? ` --row ${only}` : ""}`);
  process.exit(2);
}

mkdirSync(OUT_DIR, { recursive: true });
let drift = 0;
for (const row of rows) {
  const text = JSON.stringify(draftRow(row)) + "\n";
  const path = join(OUT_DIR, `${row.id}.json`);
  if (check) {
    let existing = null;
    try {
      existing = readFileSync(path, "utf8");
    } catch {
      /* missing counts as drift */
    }
    if (existing !== text) {
      console.error(`DRIFT ${row.id}`);
      drift++;
    }
  } else {
    writeFileSync(path, text);
  }
}
console.log(
  check
    ? drift
      ? `gen-golden-drafts --check: ${drift}/${rows.length} drifted`
      : `gen-golden-drafts --check: ${rows.length} row(s) byte-identical`
    : `gen-golden-drafts: wrote ${rows.length} row(s) to fixtures/golden_drafts/`,
);
process.exit(drift ? 1 : 0);
