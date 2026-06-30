// NFL bye-week import (Epic 4.5). A bye is a team attribute (one per team per season), not a
// player one — Sleeper's player feed doesn't carry it, which is why players.bye_week is null.
// We derive team→bye from the nflverse schedule (the week a team plays no game) and attach it to
// every player by nfl_team, so the draft board can show the column (4.2) and the policy's
// byeCover term actually fires (4.5). Pure + framework-free; one runnable check at the bottom.

// Real 2026 byes, computed from the nflverse schedule release (games.csv, REG season: a team's
// bye = the week it has no game). nflverse uses "LA" for the Rams; we key by Sleeper's "LAR".
// ponytail: a 32-row season snapshot is the lazy correct source — deterministic, offline, and
// what the page uses. fetchTeamByes() below re-derives it live; swap the page to it per-season.
export const BYE_WEEKS_2026: Record<string, number> = {
  ARI: 14, ATL: 11, BAL: 13, BUF: 7, CAR: 5, CHI: 10, CIN: 6, CLE: 11,
  DAL: 14, DEN: 10, DET: 6, GB: 11, HOU: 8, IND: 13, JAX: 7, KC: 5,
  LAR: 11, LAC: 7, LV: 13, MIA: 6, MIN: 6, NE: 11, NO: 8, NYG: 8,
  NYJ: 13, PHI: 10, PIT: 9, SEA: 11, SF: 8, TB: 10, TEN: 9, WAS: 7,
};

const SCHEDULE_URL =
  "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv";

// nflverse abbreviations → Sleeper/our nfl_team codes (only the Rams differ).
const TEAM_ALIAS: Record<string, string> = { LA: "LAR" };
const alias = (t: string) => TEAM_ALIAS[t] ?? t;

const cache = new Map<number, Record<string, number>>();

// Parse the nflverse games CSV into a team→bye map for one season. A bye is the REG-season week a
// team appears in no game. Resolves columns by header name (resilient to column reordering).
export function parseScheduleByes(csv: string, season: number): Record<string, number> {
  const lines = csv.trim().split("\n");
  const head = lines[0].split(",");
  const ci = (name: string) => head.indexOf(name);
  const [cSeason, cType, cWeek, cAway, cHome] = [
    ci("season"), ci("game_type"), ci("week"), ci("away_team"), ci("home_team"),
  ];
  if ([cSeason, cType, cWeek, cAway, cHome].some((i) => i < 0)) return {};
  const plays = new Set<string>(); // `${team}_${week}`
  const teams = new Set<string>();
  let maxWeek = 0;
  for (let i = 1; i < lines.length; i++) {
    const r = lines[i].split(",");
    if (Number(r[cSeason]) !== season || r[cType] !== "REG") continue;
    const w = Number(r[cWeek]);
    if (w > maxWeek) maxWeek = w;
    for (const t of [alias(r[cAway]), alias(r[cHome])]) {
      teams.add(t);
      plays.add(`${t}_${w}`);
    }
  }
  const byes: Record<string, number> = {};
  for (const t of teams) {
    for (let w = 1; w <= maxWeek; w++) {
      if (!plays.has(`${t}_${w}`)) { byes[t] = w; break; }
    }
  }
  return byes;
}

// Live team→bye map for a season, derived from nflverse. Null-safe: any failure (offline, CI,
// schedule not yet posted) falls back to the baked 2026 snapshot so drafting never depends on the
// network. Cached per season. ponytail: 3s budget — the page already awaits a DB read.
export async function fetchTeamByes(season = 2026): Promise<Record<string, number>> {
  const hit = cache.get(season);
  if (hit) return hit;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 3000);
    // no-store: the 2.9MB schedule blob exceeds Next's data-cache ceiling; our module-level Map
    // memoizes it per server process instead, so we fetch at most once per cold start.
    const csv = await fetch(SCHEDULE_URL, { signal: ctrl.signal, cache: "no-store" })
      .then((r) => (r.ok ? r.text() : ""))
      .finally(() => clearTimeout(timer));
    const byes = parseScheduleByes(csv, season);
    const out = Object.keys(byes).length >= 30 ? byes : BYE_WEEKS_2026;
    cache.set(season, out);
    return out;
  } catch {
    cache.set(season, BYE_WEEKS_2026);
    return BYE_WEEKS_2026;
  }
}

// Fill bye_week from nfl_team where the player row doesn't already carry one (Sleeper rarely does).
export function attachByes<T extends { nfl_team: string | null; bye_week: number | null }>(
  players: T[],
  byes: Record<string, number> = BYE_WEEKS_2026,
): T[] {
  return players.map((p) =>
    p.bye_week == null && p.nfl_team && byes[p.nfl_team] != null
      ? { ...p, bye_week: byes[p.nfl_team] }
      : p,
  );
}
