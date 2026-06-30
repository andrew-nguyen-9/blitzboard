import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { getMyLeagues } from "@/lib/queries.auth";
import LeagueManager, { type ConnectedLeague } from "@/components/LeagueManager";

export const metadata = { title: "My Leagues" };
export const dynamic = "force-dynamic"; // reflects the latest connected leagues

// Epic 8: the authed Leagues surface — connect up to 3 leagues (Sleeper + ESPN), pick the
// active one. Session-gated only (no connected league required — this is where you add them).
export default async function LeaguesPage() {
  const sb = await getServerSupabase();
  if (!sb) redirect("/login?next=/leagues");
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) redirect("/login?next=/leagues");

  const leagues = (await getMyLeagues()) as ConnectedLeague[];

  return (
    <div className="py-12">
      <div className="mb-8">
        <h1 className="font-display text-display-md">My Leagues</h1>
        <p className="mt-2 text-body text-ink-muted">
          Connect up to three leagues. Your active league drives the draft board, waiver scope, and trade context.
        </p>
      </div>
      <LeagueManager leagues={leagues} />
    </div>
  );
}
