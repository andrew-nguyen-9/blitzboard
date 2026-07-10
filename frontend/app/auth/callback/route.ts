import { NextResponse } from "next/server";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext, resolveAuthOrigin } from "@/lib/auth/redirect";

// OAuth (and magic-link) callback: exchange the code for a session, then land on `next`.
// The redirect base is resolved proxy-safe (resolveAuthOrigin) so the session cookies set here
// are scoped to the public origin the browser is on — otherwise the round-trip appears logged out.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  // Provider-side failure (user denied, misconfigured client) → surface it, don't silently loop.
  const providerError = searchParams.get("error_description") ?? searchParams.get("error");
  const next = safeNext(searchParams.get("next"));
  const base = resolveAuthOrigin(origin, {
    forwardedHost: request.headers.get("x-forwarded-host"),
    forwardedProto: request.headers.get("x-forwarded-proto"),
  });

  if (providerError) {
    return NextResponse.redirect(`${base}/login?error=${encodeURIComponent(providerError)}`);
  }
  if (code) {
    const supabase = await getServerSupabase();
    if (supabase) {
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) return NextResponse.redirect(`${base}${next}`);
    }
  }
  return NextResponse.redirect(`${base}/login?error=auth`);
}
