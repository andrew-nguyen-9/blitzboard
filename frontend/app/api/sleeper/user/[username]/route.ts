import { NextResponse } from "next/server";

// Resolve a Sleeper username → user_id, then list that user's NFL leagues for a
// season. Sleeper's read API is fully public (no auth/OAuth), so a username is
// all the "login" we need. ?season=YYYY overrides the default.
export const dynamic = "force-dynamic";

const BASE = "https://api.sleeper.app/v1";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ username: string }> },
) {
  const { username } = await params;
  const season = new URL(req.url).searchParams.get("season") || String(new Date().getFullYear());
  try {
    const ur = await fetch(`${BASE}/user/${encodeURIComponent(username)}`, { cache: "no-store" });
    if (!ur.ok) return NextResponse.json({ error: `user ${ur.status}` }, { status: ur.status });
    const user = await ur.json();
    if (!user?.user_id) return NextResponse.json({ error: "username not found" }, { status: 404 });

    const lr = await fetch(`${BASE}/user/${user.user_id}/leagues/nfl/${season}`, { cache: "no-store" });
    const leagues = lr.ok ? await lr.json() : [];
    return NextResponse.json({
      user: { id: user.user_id, username: user.username, displayName: user.display_name },
      season,
      leagues: (leagues ?? []).map((l: any) => ({
        leagueId: l.league_id,
        name: l.name,
        numTeams: l.total_rosters,
        draftId: l.draft_id ?? null,
        status: l.status,
      })),
    });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "fetch failed" }, { status: 502 });
  }
}
