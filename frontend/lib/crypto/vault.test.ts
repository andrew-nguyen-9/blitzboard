import { describe, it, expect } from "vitest";
import { randomBytes } from "node:crypto";
import { encryptSecret, decryptSecret, loadMasterKey, maskHint } from "./vault";

const key = randomBytes(32);

describe("vault encrypt/decrypt (AES-256-GCM)", () => {
  it("round-trips a secret", () => {
    const secret = "espn_s2=AEB...verylongcookie; SWID={GUID}";
    expect(decryptSecret(encryptSecret(secret, key), key)).toBe(secret);
  });

  it("produces a different ciphertext each call (random IV) for the same input", () => {
    const a = encryptSecret("same", key);
    const b = encryptSecret("same", key);
    expect(a).not.toBe(b); // random IV ⇒ no deterministic ciphertext leak
    expect(decryptSecret(a, key)).toBe("same");
    expect(decryptSecret(b, key)).toBe("same");
  });

  it("rejects a tampered ciphertext (GCM auth tag)", () => {
    const packed = encryptSecret("secret", key);
    const [iv, tag, ct] = packed.split(".");
    // flip the last byte of the ciphertext
    const buf = Buffer.from(ct, "base64");
    buf[buf.length - 1] ^= 0x01;
    const tampered = [iv, tag, buf.toString("base64")].join(".");
    expect(() => decryptSecret(tampered, key)).toThrow();
  });

  it("fails to decrypt with the wrong key", () => {
    const packed = encryptSecret("secret", key);
    expect(() => decryptSecret(packed, randomBytes(32))).toThrow();
  });

  it("rejects malformed ciphertext", () => {
    expect(() => decryptSecret("not-valid", key)).toThrow(/malformed/);
  });
});

describe("loadMasterKey", () => {
  it("returns null when unset (offline-safe)", () => {
    expect(loadMasterKey({})).toBeNull();
  });
  it("loads a 32-byte base64 key", () => {
    const k = randomBytes(32).toString("base64");
    expect(loadMasterKey({ CREDENTIAL_VAULT_KEY: k })?.length).toBe(32);
  });
  it("rejects a key of the wrong length", () => {
    expect(() => loadMasterKey({ CREDENTIAL_VAULT_KEY: randomBytes(16).toString("base64") })).toThrow();
  });
});

describe("maskHint", () => {
  it("reveals only the last 4 characters", () => {
    expect(maskHint("abcdef1234")).toBe("••••1234");
  });
  it("never returns the full secret", () => {
    expect(maskHint("supersecretvalue")).not.toContain("supersecret");
  });
});
