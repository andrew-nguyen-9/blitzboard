import { NextResponse } from "next/server";

// Server-side proxy for ESPN's UNOFFICIAL live draft feed (D4/D7 — the fragile one).
// Cookie auth (espn_s2 + SWID) lives in server env, never the browser. Returns a
// normalized { picks, meta } so the client maps by espn_id. Any failure surfaces as
// an error the board turns into a "fall back to manual" prompt.
export const dynamic = "force-dynamic";

const BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const leagueId = url.searchParams.get("leagueId") || process.env.ESPN_LEAGUE_ID;
  const season = url.searchParams.get("season") || process.env.ESPN_SEASON || "2025";
  const s2 = process.env.ESPN_S2;
  const swid = process.env.ESPN_SWID;

  if (!leagueId) {
    return NextResponse.json({ error: "no ESPN league id (set ESPN_LEAGUE_ID)" }, { status: 400 });
  }

  const headers: Record<string, string> = {};
  if (s2 && swid) headers["Cookie"] = `SWID=${swid}; espn_s2=${s2}`;

  try {
    const r = await fetch(
      `${BASE}/${season}/segments/0/leagues/${leagueId}?view=mDraftDetail&view=mSettings`,
      { headers, cache: "no-store" },
    );
    if (!r.ok) {
      return NextResponse.json({ error: `espn ${r.status}` }, { status: r.status });
    }
    const data = await r.json();
    const detail = data?.draftDetail ?? {};
    const picks = (detail.picks ?? [])
      .filter((p: any) => p?.playerId && p?.overallPickNumber)
      .map((p: any) => ({ pickNo: p.overallPickNumber, espnId: String(p.playerId) }))
      .sort((a: any, b: any) => a.pickNo - b.pickNo);
    const meta = {
      teams: data?.settings?.size ?? null,
      status: detail.inProgress ? "drafting" : detail.drafted ? "complete" : "pre",
    };
    return NextResponse.json({ picks, meta });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "fetch failed" }, { status: 502 });
  }
}
