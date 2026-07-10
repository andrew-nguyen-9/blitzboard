import EmptyState from "@/components/EmptyState";
import BettingBoard from "@/components/BettingBoard";
import { getBettingMarkets } from "./odds";

export const metadata = { title: "Betting Markets" };
export const dynamic = "force-dynamic"; // live lines — never serve a stale slate

// E5 — sports-betting war room. Aggregates the live free-tier NFL slate (The Odds
// API) into biggest/most-backed bets, shootouts, and a suggested parlay. Betting
// is a LIGHT, acknowledged signal here — a separate view, NOT folded into player
// value (that lives in the bounded, logged BettingFactor). No ODDS_API_KEY →
// graceful empty state; the app builds and renders with no key.
export default async function BettingPage() {
  const { configured, games, error } = await getBettingMarkets();

  if (!configured) {
    return (
      <EmptyState title="Betting Markets" phase="v4 · E5">
        Set <code className="text-accent">ODDS_API_KEY</code> (The Odds API free tier, ~500 req/mo)
        in the server environment to light up live NFL lines, biggest bets, and parlays. Betting is
        a small acknowledged signal — never silently folded into player value.
      </EmptyState>
    );
  }

  if (!games.length) {
    return (
      <EmptyState title="Betting Markets" phase="v4 · E5">
        {error
          ? `Odds feed is unavailable right now (${error}). It will reappear automatically once the market is back.`
          : "No NFL games are currently on the board — check back closer to kickoff for live lines."}
      </EmptyState>
    );
  }

  return (
    <div className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          {/* F1 §Primitives → Glow: the accent word carries the charged neon signal. */}
          <h1 className="font-display text-display-md">
            Betting <span className="neon-text">markets</span>
          </h1>
          <p className="mt-2 text-body text-ink-muted">
            Live NFL lines · consensus across US books · biggest bets, shootouts &amp; parlays
          </p>
        </div>
        <span className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted">
          {games.length} live {games.length === 1 ? "game" : "games"}
        </span>
      </div>

      <div className="mt-8">
        <BettingBoard games={games} />
      </div>
    </div>
  );
}
