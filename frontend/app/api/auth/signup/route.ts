import { NextRequest, NextResponse } from "next/server";
import { getServerSupabase } from "@/lib/supabase/server";
import { loadMasterKey, encryptSecret } from "@/lib/crypto/vault";
import { signupInput, validate, isSameOrigin } from "@/lib/validation";
import { rateLimit, humanCheck, verifyBotId, type Fallback } from "@/lib/auth/botDefense";

// node:crypto (envelope encryption) needs the Node runtime, not Edge.
export const runtime = "nodejs";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export async function POST(req: NextRequest) {
  // CSRF defense-in-depth on top of SameSite=Lax cookies.
  if (!isSameOrigin(req)) {
    return NextResponse.json({ error: "bad origin" }, { status: 403 });
  }

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "anon";
  if (!rateLimit(`signup:${ip}`)) {
    return NextResponse.json({ error: "Too many attempts. Please wait a minute." }, { status: 429 });
  }

  let body: {
    firstName?: string;
    lastName?: string;
    email?: string;
    phone?: string;
    password?: string;
    confirm?: string;
    hCaptchaToken?: string;
    fallback?: Fallback;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad request" }, { status: 400 });
  }

  // Bot defense: Vercel BotID seam, then hCaptcha-or-fallback human check.
  if (!(await verifyBotId())) {
    return NextResponse.json({ error: "Verification failed." }, { status: 400 });
  }
  if (!(await humanCheck({ hCaptchaToken: body.hCaptchaToken, fallback: body.fallback }))) {
    return NextResponse.json({ error: "Human verification failed. Please try again." }, { status: 400 });
  }

  const valid = validate(signupInput, {
    firstName: body.firstName,
    lastName: body.lastName,
    email: body.email,
    phone: body.phone,
    password: body.password,
    confirm: body.confirm,
  });
  if (!valid.ok) return NextResponse.json({ error: valid.error }, { status: 400 });
  const d = valid.data;

  const supabase = await getServerSupabase();
  if (!supabase) return NextResponse.json({ error: "Sign-up is unavailable offline." }, { status: 503 });

  // Envelope-encrypt the phone (sensitive PII) before it touches storage — same app-layer
  // AES-256-GCM as the credential vault, master key in server env only (ponytail: reuse
  // lib/crypto/vault). The ciphertext rides in signUp metadata; the handle_new_user trigger
  // persists it to accounts.phone_encrypted, so no post-signup session (email confirm) and no
  // service-role key are needed in the request path. No key configured → phone isn't stored.
  const key = loadMasterKey();
  const phoneEncrypted = key ? encryptSecret(d.phone, key) : null;

  const { error } = await supabase.auth.signUp({
    email: d.email,
    // Hashed server-side by Supabase (bcrypt); never stored, decrypted, or logged by us.
    password: d.password,
    options: {
      emailRedirectTo: `${SITE}/auth/confirm`,
      data: {
        full_name: `${d.firstName} ${d.lastName}`,
        first_name: d.firstName,
        last_name: d.lastName,
        phone_encrypted: phoneEncrypted,
      },
    },
  });
  if (error) return NextResponse.json({ error: error.message }, { status: 400 });

  return NextResponse.json({ ok: true });
}
