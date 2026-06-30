// Pure MFA decisions (mirrors gate.ts): kept free of the Supabase client so the security
// matrix is provable by unit test, independent of the network/DB.
import type { AuthenticatorAssuranceLevels, Factor } from "@supabase/supabase-js";

// After a password sign-in the session is aal1. If the user has a verified second factor,
// Supabase reports nextLevel "aal2" while currentLevel is still "aal1" → the user must clear
// a TOTP challenge before the session is fully trusted.
export function needsMfaStepUp(
  currentLevel: AuthenticatorAssuranceLevels | null,
  nextLevel: AuthenticatorAssuranceLevels | null,
): boolean {
  return nextLevel === "aal2" && currentLevel !== "aal2";
}

// The user's active (verified) TOTP factor, or null. The sign-in challenge and the
// "turn off 2FA" control both target this one.
export function verifiedTotpFactor(factors: Factor[] | undefined | null): Factor | null {
  return factors?.find((f) => f.factor_type === "totp" && f.status === "verified") ?? null;
}
