// SMS one-time-code interface for phone-based 2FA. The seam exists so a provider (Twilio,
// MessageBird, AWS SNS, …) can be dropped in without touching call sites — but no provider is
// wired in v3. TOTP is the only live second factor; this path stays inert until SMS_PROVIDER
// is set. Supabase's phone-factor challenge would route its code through sendSmsOtp().
//
// ponytail: interface + unconfigured guard only. Upgrade path: set SMS_PROVIDER, return a
// concrete SmsSender from getSmsSender(), and enable phone factors in Supabase Auth.
export interface SmsSender {
  /** Deliver a message to an E.164 phone number. Throws on transport failure. */
  send(toE164: string, message: string): Promise<void>;
}

export function isSmsConfigured(): boolean {
  return Boolean(process.env.SMS_PROVIDER);
}

// The configured SMS sender, or null when no provider is wired (the v3 default).
export function getSmsSender(): SmsSender | null {
  if (!isSmsConfigured()) return null;
  // ponytail: provider flag flipped but no integration written yet — fail loud rather than
  // silently dropping a security code. Replace with the real sender when SMS 2FA ships.
  throw new Error("SMS_PROVIDER is set but no SMS sender implementation is wired.");
}

// Sends a verification code over SMS. Rejects when SMS 2FA is unconfigured (v3 default),
// so callers never assume a code was delivered.
export async function sendSmsOtp(toE164: string, code: string): Promise<void> {
  const sender = getSmsSender();
  if (!sender) throw new Error("SMS 2FA is not configured (no SMS provider).");
  await sender.send(toE164, `Your BlitzBoard verification code is ${code}`);
}
