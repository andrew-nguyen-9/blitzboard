import { NextResponse } from "next/server";

// Server-side proxy for Sleeper live draft picks. Keeps the browser off Sleeper's
// API directly (no CORS surprises) and centralizes the fetch. No caching — this is
// a live feed. Sleeper's draft API is public, no auth.
export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ draftId: string }> },
) {
  const { draftId } = await params;
  try {
    const r = await fetch(`https://api.sleeper.app/v1/draft/${draftId}/picks`, {
      cache: "no-store",
    });
    if (!r.ok) {
      return NextResponse.json({ error: `sleeper ${r.status}` }, { status: r.status });
    }
    return NextResponse.json(await r.json());
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "fetch failed" }, { status: 502 });
  }
}
