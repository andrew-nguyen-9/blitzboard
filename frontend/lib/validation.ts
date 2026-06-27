// Server-boundary input validation (v2.5.5). Every server action / route handler that takes
// untrusted input validates it here with zod before touching the database — never trust the
// client's shape. Pair with SameSite=Lax cookies + isSameOrigin() for CSRF defense-in-depth.
import { z } from "zod";

export const platformSchema = z.enum(["espn", "sleeper"]);

// Credential vault write: a non-empty secret, bounded so a giant body can't be forced through.
export const credentialInput = z.object({
  platform: platformSchema,
  secret: z.string().min(1, "secret required").max(8192),
});

export const leagueMetaInput = z.object({
  platform: z.enum(["espn", "sleeper", "manual"]),
  external_league_id: z.string().max(64).nullable(),
  season: z.string().max(8).nullable(),
  name: z.string().min(1).max(120),
});

export const sleeperUsername = z
  .string()
  .trim()
  .min(1)
  .max(64)
  .regex(/^[a-zA-Z0-9_]+$/, "invalid username");

export const sleeperLeagueId = z.string().trim().regex(/^\d+$/, "invalid league id");

export type Validated<T> = { ok: true; data: T } | { ok: false; error: string };

// Validate input against a schema; returns a discriminated result (never throws).
export function validate<T>(schema: z.ZodType<T>, input: unknown): Validated<T> {
  const r = schema.safeParse(input);
  if (r.success) return { ok: true, data: r.data };
  return { ok: false, error: r.error.issues[0]?.message ?? "invalid input" };
}

// CSRF guard: a mutating request must originate from our own site. SameSite=Lax already blocks
// most cross-site cookie sends; this rejects a forged Origin on top. A missing Origin (same-site
// navigations, server actions) is allowed — those are covered by SameSite + Next's own checks.
export function isSameOrigin(req: { headers: { get(name: string): string | null } }): boolean {
  const origin = req.headers.get("origin");
  if (!origin) return true;
  const host = req.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}
