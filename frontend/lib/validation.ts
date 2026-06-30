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

// Signup form (Epic 7). Names/phone are bounded; password is hashed server-side by Supabase
// (bcrypt) and is never stored or logged by us. `confirm` must match `password`.
export const signupInput = z
  .object({
    firstName: z.string().trim().min(1, "first name required").max(80),
    lastName: z.string().trim().min(1, "last name required").max(80),
    email: z.string().trim().email("invalid email").max(254),
    phone: z
      .string()
      .trim()
      .min(7, "invalid phone")
      .max(32)
      .regex(/^[0-9+().\-\s]+$/, "invalid phone"),
    password: z.string().min(8, "password must be at least 8 characters").max(128),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "passwords do not match",
    path: ["confirm"],
  });

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
