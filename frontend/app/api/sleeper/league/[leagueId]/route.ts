import { NextResponse } from "next/server";
import {
  rosterFromSleeper,
  scoringLabelFromSleeper,
  defaultTeams,
  type LeagueConfig,
} from "@/lib/leagueConfig";

// One call → a fully normalized LeagueConfig for a Sleeper league: roster shape,
// scoring summary, team count, team names (with draft slots), and the draft id.
// This is the "minimal setup" path — the client hands us a league_id (picked from
// the username lookup) and gets back everything the draft board needs.
export const dynamic = "force-dynamic";

const BASE = "https://api.sleeper.app/v1";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ leagueId: string }> },
) {
  const { leagueId } = await params;
  try {
    const lr = await fetch(`${BASE}/league/${leagueId}`, { cache: "no-store" });
    if (!lr.ok) return NextResponse.json({ error: `league ${lr.status}` }, { status: lr.status });
    const league = await lr.json();

    const [usersRes, draftRes] = await Promise.all([
      fetch(`${BASE}/league/${leagueId}/users`, { cache: "no-store" }),
      league.draft_id
        ? fetch(`${BASE}/draft/${league.draft_id}`, { cache: "no-store" })
        : Promise.resolve(null as any),
    ]);
    const users: any[] = usersRes?.ok ? await usersRes.json() : [];
    const draft: any = draftRes?.ok ? await draftRes.json() : null;

    const positions: string[] = league.roster_positions ?? [];
    const { slots, bench } = rosterFromSleeper(positions);
    const numTeams = league.total_rosters ?? draft?.settings?.teams ?? 12;

    // Map draft slot → owner via draft_order (user_id → slot); name via users[].
    const userById = new Map(users.map((u) => [u.user_id, u]));
    const draftOrder: Record<string, number> = draft?.draft_order ?? {};
    const teams = defaultTeams(numTeams).map((t) => {
      const ownerId = Object.keys(draftOrder).find((uid) => draftOrder[uid] === t.slot);
      const u = ownerId ? userById.get(ownerId) : undefined;
      const name = u?.metadata?.team_name || u?.display_name || t.name;
      return { slot: t.slot, name, owner: u?.display_name };
    });

    const config: LeagueConfig = {
      source: "sleeper",
      leagueId,
      name: league.name ?? "Sleeper League",
      numTeams,
      rosterSlots: slots,
      benchSize: bench,
      scoringLabel: scoringLabelFromSleeper(league.scoring_settings, positions),
      teams,
      draftId: league.draft_id ?? null,
      draftType: draft?.type ?? "snake",
    };
    return NextResponse.json(config);
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "fetch failed" }, { status: 502 });
  }
}
