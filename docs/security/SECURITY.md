# Security Architecture

> Requirements: Google/email login; saved ESPN/Sleeper credentials; strong hashing;
> **no third-party tool (Fiddler, DevTools network, Charles) can read another user's
> information**; site-wide optimization, speed, and hardening. Phase **v2.5** (build),
> **v2.7** (hardening + verification).

## Stack decision

- **Auth.js (NextAuth)** for sessions (per the platform decision) over **Supabase Postgres**
  for data. Providers: **Google OAuth** + **email/password** (credentials), with room for
  more OAuth later.
- Sessions are **httpOnly, Secure, SameSite=Lax cookies** holding an opaque session id (or a
  signed, short-lived JWT) — **never** a token a client script or a network sniffer can replay
  into another account. All traffic is **HTTPS/TLS only** (HSTS, preload).

## Password hashing

- Email/password accounts: **Argon2id** (preferred) or **bcrypt (cost ≥ 12)** if Argon2 isn't
  available in the runtime. Per-user salt; never store or log plaintext; constant-time compare.
- Never roll our own crypto. OAuth users have no password at all (delegated to Google).

## The threat the user named: "no inspector can see another user's data"

A network inspector can always see **its own** session's TLS-decrypted traffic (that's the
authenticated user's own data — expected). The real guarantee is **isolation**: nothing a
user (or their tools) can do exposes *another* user's data or credentials. We get that from:

1. **Row-Level Security on every user table.** Policies key every row to `auth.uid()`:
   `using (user_id = auth.uid())`. Even with a leaked anon key, a client can only ever read
   its own rows. The service-role key (bypasses RLS) lives **only** in the pipeline/server,
   never in the browser bundle.
2. **Server-side authorization on every mutation.** Server actions / route handlers re-check
   the session and ownership before touching data — never trust a client-supplied `user_id`.
3. **Encrypted credential vault** (below) — ESPN/Sleeper secrets are encrypted at rest with a
   key the client never holds, and are **never sent to the browser** after storage.
4. **No secrets in the client bundle.** Only `NEXT_PUBLIC_*` (anon key, URLs) ship to the
   client; CI checks for accidental secret exposure.

## Encrypted credential vault (ESPN `espn_s2`/`SWID`, Sleeper tokens)

- Stored in a `credential_vault` table, **encrypted with AES-256-GCM** (authenticated
  encryption) using a key from a server-only secret / KMS — **envelope encryption**: a master
  key encrypts per-user data keys. Supabase column-level encryption or app-layer encryption in
  a server action; the plaintext only exists transiently server-side when the **pipeline**
  uses it to call ESPN/Sleeper.
- The browser **writes** credentials once (over TLS, into a server action that encrypts) and
  thereafter only sees a masked "connected ✓" state — never the secret back. RLS isolates each
  vault row to its owner.
- Re-prompt/re-verify on expiry (ESPN cookies rotate); store only what's needed; allow the
  user to disconnect (hard-delete the row).

## Transport, headers, and surface hardening

- HTTPS only; **HSTS** (`max-age` + preload). Secure/httpOnly/SameSite cookies.
- **CSP** (default-src self; explicit allowlist for fonts/CDN/Rive/analytics), plus
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, frame-ancestors none.
- **CSRF**: SameSite cookies + per-form tokens / origin checks on mutations.
- **Rate limiting + bot defense** on auth + write endpoints (consider Vercel BotID).
- **Input validation** (zod) on every server boundary; parameterized queries only (no string
  SQL); output encoding to prevent XSS.
- **Audit/logging** without logging secrets or PII; structured errors (no stack traces to
  clients) — no silent failures.
- Dependency hygiene: lockfile, `npm audit`/Dependabot, pinned actions.

## Two-plane access model (recap)

- **Public plane**: anon key, RLS public-read on the player universe + public trending/trade
  snapshots. No user data.
- **Auth plane**: Auth.js session → per-user RLS rows (`accounts`, `user_leagues`,
  `credential_vault`). Gated tabs (My League, my Waivers, my Trades, Draft-with-my-rules) live
  here. See `docs/architecture/ARCHITECTURE.md`.

## Verification (v2.7 — the "Go/No-Go")

- RLS coverage test: for every user table, prove user A cannot read/write user B's rows
  (automated).
- Secret-exposure scan of the client bundle; header scan (securityheaders-style); TLS/HSTS
  check.
- Auth flows: session fixation, CSRF, password-reset, OAuth state/nonce, logout invalidation.
- Vault round-trip: confirm plaintext never returns to the client and never lands in logs.
- `ce-security-reviewer` / `security-guidance` pass on the auth + vault diffs.
