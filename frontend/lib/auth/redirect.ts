// Open-redirect guard: only allow same-origin relative paths as post-auth targets.
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/")) return "/";
  if (next.startsWith("//") || next.startsWith("/\\")) return "/";
  return next;
}

// Routes that require an authenticated session. Unauth → middleware redirects to
// /login?next=<path> (return-to), so they land back here after signing in.
// ponytail: a single-prefix list, not a route-config system — add prefixes here as the authed plane grows.
const PROTECTED_PREFIXES = ["/league"];

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
}
