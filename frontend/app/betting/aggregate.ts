// E5 — pure betting-market aggregation. No I/O, no env, no server-only imports:
// fully unit-testable (aggregate.test.ts) and safe to import from a Client
// Component. `odds.ts` fetches the raw slate; this turns it into the board's
// derived views (biggest bets, over/unders, suggested parlays).

// Shape of one event as The Odds API v4 returns it (fields we use).
export interface RawEvent {
  id: string;
  commence_time?: string;
  home_team?: string;
  away_team?: string;
  bookmakers?: {
    key?: string;
    markets?: { key?: string; outcomes?: { name?: string; price?: number; point?: number }[] }[];
  }[];
}

// A normalized consensus game — mirrors the pipeline `betting_odds` row.
export interface Game {
  id: string;
  commenceTime: string | null;
  home: string;
  away: string;
  favorite: string; // team the market favors (lower/negative spread)
  underdog: string;
  spread: number; // absolute favorite spread, e.g. 3.5
  total: number | null; // over/under
  favMoneyline: number | null; // American odds on the favorite
  favWinProb: number; // implied probability [0,1], vig included
}

function median(xs: number[]): number | null {
  const v = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

// American moneyline → implied win probability (vig-inclusive).
export function impliedProb(ml: number): number {
  return ml < 0 ? -ml / (-ml + 100) : 100 / (ml + 100);
}

// American → decimal, for parlay math.
export function toDecimal(ml: number): number {
  return ml < 0 ? 1 + 100 / -ml : 1 + ml / 100;
}

// Decimal → American, for displaying a combined parlay price.
export function toAmerican(dec: number): number {
  return dec >= 2 ? Math.round((dec - 1) * 100) : Math.round(-100 / (dec - 1));
}

// Raw slate → consensus games. Median spread/total, mean moneyline across books.
// Games with no usable market are dropped (degrade-safe).
export function normalizeEvents(raw: unknown): Game[] {
  if (!Array.isArray(raw)) return [];
  const games: Game[] = [];
  for (const ev of raw as RawEvent[]) {
    if (!ev?.id || !ev.home_team || !ev.away_team) continue;
    const home = ev.home_team;
    const away = ev.away_team;
    const homeSpreads: number[] = [];
    const totals: number[] = [];
    const homeML: number[] = [];
    const awayML: number[] = [];
    for (const bk of ev.bookmakers ?? []) {
      for (const mkt of bk.markets ?? []) {
        for (const o of mkt.outcomes ?? []) {
          if (mkt.key === "spreads" && o.name === home && o.point != null) homeSpreads.push(o.point);
          else if (mkt.key === "totals" && o.name === "Over" && o.point != null) totals.push(o.point);
          else if (mkt.key === "h2h" && o.price != null) {
            if (o.name === home) homeML.push(o.price);
            else if (o.name === away) awayML.push(o.price);
          }
        }
      }
    }
    const homeSpread = median(homeSpreads);
    const total = median(totals);
    const hml = homeML.length ? Math.round(homeML.reduce((a, b) => a + b, 0) / homeML.length) : null;
    const aml = awayML.length ? Math.round(awayML.reduce((a, b) => a + b, 0) / awayML.length) : null;
    if (homeSpread == null && hml == null) continue; // need a favorite signal

    // Favorite = negative home spread → home favored; else away. Fall back to ML.
    const homeFav = homeSpread != null ? homeSpread <= 0 : (hml ?? 0) < (aml ?? 0);
    const favMoneyline = homeFav ? hml : aml;
    games.push({
      id: ev.id,
      commenceTime: ev.commence_time ?? null,
      home,
      away,
      favorite: homeFav ? home : away,
      underdog: homeFav ? away : home,
      spread: homeSpread != null ? Math.abs(homeSpread) : 0,
      total,
      favMoneyline,
      favWinProb: favMoneyline != null ? impliedProb(favMoneyline) : 0.5,
    });
  }
  return games;
}

// "Biggest / most-backed" bets — the free tier has no popularity field, so we
// proxy it by market conviction (implied favorite win probability). Documented
// on the page.
export function biggestBets(games: Game[], n = 6): Game[] {
  return [...games].sort((a, b) => b.favWinProb - a.favWinProb).slice(0, n);
}

// Highest-scoring games (shootouts / popular overs).
export function topTotals(games: Game[], n = 6): Game[] {
  return [...games].filter((g) => g.total != null).sort((a, b) => (b.total ?? 0) - (a.total ?? 0)).slice(0, n);
}

export interface Parlay {
  label: string;
  legs: { pick: string; moneyline: number }[];
  decimal: number;
  american: number;
  combinedProb: number;
}

// A single "chalk" parlay from the N most-favored moneyline picks. Combined
// decimal odds multiply; combined implied prob is the product of the legs'.
export function chalkParlay(games: Game[], legs = 3): Parlay | null {
  const picks = biggestBets(games, legs).filter((g) => g.favMoneyline != null);
  if (picks.length < 2) return null;
  const dec = picks.reduce((acc, g) => acc * toDecimal(g.favMoneyline!), 1);
  const prob = picks.reduce((acc, g) => acc * g.favWinProb, 1);
  return {
    label: `${picks.length}-leg favorites`,
    legs: picks.map((g) => ({ pick: g.favorite, moneyline: g.favMoneyline! })),
    decimal: dec,
    american: toAmerican(dec),
    combinedProb: prob,
  };
}
