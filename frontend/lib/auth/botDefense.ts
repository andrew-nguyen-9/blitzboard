// Auth-route bot defense (Epic 7) — server-only. Replicates the portfolio-website pattern:
// hCaptcha (env-gated) with a self-hosted honeypot/timing/math fallback that works when the
// hCaptcha script is blocked, plus a per-instance rate limit and a Vercel BotID seam.
//
// Threat model: defense-in-depth on the public signup endpoint. None of these are a single
// point of failure — a request must clear the rate limit AND a human check.

// ── Rate limit ──────────────────────────────────────────────────────────────
// Fixed window, keyed by IP. ponytail: in-memory + per-instance — fine for a single Vercel
// function instance; swap for Upstash/KV (`@upstash/ratelimit`) if you scale to many instances
// or need durable counts across cold starts.
const WINDOW_MS = 60_000;
const MAX_HITS = 5;
const hits = new Map<string, { count: number; reset: number }>();

export function rateLimit(key: string, max = MAX_HITS, windowMs = WINDOW_MS): boolean {
  const now = Date.now();
  const e = hits.get(key);
  if (!e || now > e.reset) {
    hits.set(key, { count: 1, reset: now + windowMs });
    return true;
  }
  if (e.count >= max) return false;
  e.count += 1;
  return true;
}

// ── hCaptcha ────────────────────────────────────────────────────────────────
// Verifies a token against hCaptcha's siteverify. Env-gated: with no HCAPTCHA_SECRET we skip
// verification (local/offline dev, or before keys are provisioned) rather than block signups.
export async function verifyHCaptcha(
  token: string | undefined,
  env: Record<string, string | undefined> = process.env,
): Promise<boolean> {
  const secret = env.HCAPTCHA_SECRET;
  if (!secret) return true; // not configured → skip
  if (!token) return false;
  const res = await fetch("https://hcaptcha.com/siteverify", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ secret, response: token }),
  });
  const data = (await res.json()) as { success: boolean };
  return data.success === true;
}

// ── Self-hosted fallback ──────────────────────────────────────────────────────
// Used when hCaptcha's script is blocked (NoScript, Privacy Badger, ad blockers) or no site
// key is set. Honeypot must be empty, the form must have been open long enough to be human,
// and the arithmetic answer must be correct.
export type Fallback = { honeypot?: string; answer?: number; a?: number; b?: number; elapsedMs?: number };

export function verifyFallback(fb: Fallback | undefined): boolean {
  if (!fb) return false;
  const { honeypot, answer, a, b, elapsedMs } = fb;
  if (honeypot && honeypot.trim() !== "") return false;
  if (typeof elapsedMs !== "number" || elapsedMs < 2000) return false;
  if (typeof a !== "number" || typeof b !== "number" || typeof answer !== "number") return false;
  if (a < 0 || a > 9 || b < 0 || b > 9) return false;
  return answer === a + b;
}

// ── Vercel BotID ──────────────────────────────────────────────────────────────
// ponytail: BotID is a deploy-time gate — the `botid` package only functions on Vercel with
// Bot Management enabled in the dashboard, so it's stubbed to a no-op here to keep the build
// clean and local/offline dev unblocked. Upgrade path: `npm i botid`, wrap next.config with
// `withBotId`, then here `const { checkBotId } = await import("botid/server"); const v = await
// checkBotId(); return !v.isBot;`.
export async function verifyBotId(): Promise<boolean> {
  return true;
}

// ── Orchestrator ──────────────────────────────────────────────────────────────
// hCaptcha when a token is present, else the self-hosted fallback. With neither, allow only
// when hCaptcha isn't configured (mirrors the reference contact route).
export async function humanCheck(
  input: { hCaptchaToken?: string; fallback?: Fallback },
  env: Record<string, string | undefined> = process.env,
): Promise<boolean> {
  if (input.hCaptchaToken) return verifyHCaptcha(input.hCaptchaToken, env);
  if (input.fallback) return verifyFallback(input.fallback);
  return !env.HCAPTCHA_SECRET;
}
