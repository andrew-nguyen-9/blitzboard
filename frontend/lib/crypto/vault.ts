// Credential-vault encryption (v2.5.3). App-layer AES-256-GCM: the ESPN/Sleeper secrets are
// encrypted at rest with a 32-byte master key held only in server env (CREDENTIAL_VAULT_KEY,
// base64) — never in the repo or the client bundle. GCM gives authenticated encryption, so a
// tampered ciphertext fails to decrypt rather than silently returning garbage.
//
// Server-only (uses node:crypto + the master key). Never import from a client component.
import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

const ALG = "aes-256-gcm";
const IV_LEN = 12; // 96-bit nonce, the GCM standard
const KEY_LEN = 32; // AES-256

// Load and validate the master key from env. Returns null when unset so the app stays
// offline-safe (a missing key disables the vault, it doesn't crash the build).
export function loadMasterKey(env: Record<string, string | undefined> = process.env): Buffer | null {
  const b64 = env.CREDENTIAL_VAULT_KEY;
  if (!b64) return null;
  const key = Buffer.from(b64, "base64");
  if (key.length !== KEY_LEN) {
    throw new Error(`CREDENTIAL_VAULT_KEY must decode to ${KEY_LEN} bytes (got ${key.length})`);
  }
  return key;
}

// Encrypt plaintext → "iv.tag.ciphertext" (each base64). A fresh random IV per call means the
// same input never yields the same ciphertext (no equality leak across stored credentials).
export function encryptSecret(plaintext: string, key: Buffer): string {
  const iv = randomBytes(IV_LEN);
  const cipher = createCipheriv(ALG, key, iv);
  const ct = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [iv, tag, ct].map((b) => b.toString("base64")).join(".");
}

// Decrypt "iv.tag.ciphertext" back to plaintext. Throws on a wrong key or any tampering
// (the GCM auth tag won't verify) and on a malformed payload — never returns garbage.
export function decryptSecret(packed: string, key: Buffer): string {
  const parts = packed.split(".");
  if (parts.length !== 3 || parts.some((p) => !p)) throw new Error("malformed ciphertext");
  const [iv, tag, ct] = parts.map((p) => Buffer.from(p, "base64"));
  const decipher = createDecipheriv(ALG, key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(ct), decipher.final()]).toString("utf8");
}

// A non-reversible display hint for the UI ("connected ✓" surfaces this, never the secret).
export function maskHint(plaintext: string): string {
  const tail = plaintext.slice(-4);
  return "••••" + tail;
}
