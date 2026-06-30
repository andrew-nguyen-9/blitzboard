import TradeCalculator from "@/components/TradeCalculator";
import { getRecentNews } from "@/lib/queries";
import { getMyLeagues } from "@/lib/queries.auth";
import { isSupabaseConfigured } from "@/lib/supabase";

export const metadata = { title: "Trade Calculator" };
export const dynamic = "force-dynamic"; // news refreshes; never serve stale

// Epic 10 (unauth): the public trade calculator — search the all-NFL player
// snapshot, stack both sides, compare by value, with an all-NFL RSS NEWS PULSE
// that refocuses to the traded players on submit. No league context. The page is
// a thin shell; the snapshot loads client-side (TradeCalculator → lib/snapshot.ts).
// Epic 8 (auth) layers a League Selector + roster multi-select + team-focused RSS.
export default async function TradesPage() {
  const live = isSupabaseConfigured();
  const [news, myLeagues] = live ? await Promise.all([getRecentNews(12), getMyLeagues()]) : [[], []];

  return (
    <div className="py-12">
      <TradeCalculator news={news} leagues={myLeagues.map((l) => ({ id: l.id, name: l.name ?? "League" }))} />
    </div>
  );
}
