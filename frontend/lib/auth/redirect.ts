// Open-redirect guard: only allow same-origin relative paths as post-auth targets.
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/")) return "/";
  if (next.startsWith("//") || next.startsWith("/\\")) return "/";
  return next;
}

// OAuth callback origin resolution. Behind a proxy (e.g. Vercel) the callback request's URL
// origin is the INTERNAL host, not the public site — redirecting the freshly-signed-in user
// there drops the just-set session cookies (scoped to the public domain), so the OAuth round-trip
// lands "logged out". Root cause of the broken Google flow. Fix (Supabase SSR callback pattern):
// in prod honor the `x-forwarded-host`/`-proto` the proxy sets; else fall back to the configured
// NEXT_PUBLIC_SITE_URL; else the raw origin. Dev has no proxy → use the origin as-is.
export function resolveAuthOrigin(
  origin: string,
  headers: { forwardedHost?: string | null; forwardedProto?: string | null },
  env: { NODE_ENV?: string; NEXT_PUBLIC_SITE_URL?: string } = process.env,
): string {
  if (env.NODE_ENV === "development") return origin;
  if (headers.forwardedHost) {
    return `${headers.forwardedProto || "https"}://${headers.forwardedHost}`;
  }
  return env.NEXT_PUBLIC_SITE_URL || origin;
}

// Routes that require an authenticated session. Unauth → middleware redirects to
// /login?next=<path> (return-to), so they land back here after signing in.
// ponytail: a single-prefix list, not a route-config system — add prefixes here as the authed plane grows.
const PROTECTED_PREFIXES = ["/league"];

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
}
