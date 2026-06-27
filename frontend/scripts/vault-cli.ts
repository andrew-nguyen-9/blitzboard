// Ops/test CLI for the credential vault. Encrypt or decrypt a value with CREDENTIAL_VAULT_KEY,
// using the same code path as the app (lib/crypto/vault.ts). Reads the value on stdin.
//   printf '%s' "secret"      | CREDENTIAL_VAULT_KEY=... tsx scripts/vault-cli.ts encrypt
//   printf '%s' "iv.tag.ct"   | CREDENTIAL_VAULT_KEY=... tsx scripts/vault-cli.ts decrypt
import { readFileSync } from "node:fs";
import { loadMasterKey, encryptSecret, decryptSecret } from "../lib/crypto/vault";

const mode = process.argv[2];
const key = loadMasterKey();
if (!key) {
  process.stderr.write("vault-cli: set CREDENTIAL_VAULT_KEY (base64, 32 bytes)\n");
  process.exit(2);
}
const input = readFileSync(0, "utf8");
if (mode === "encrypt") process.stdout.write(encryptSecret(input, key));
else if (mode === "decrypt") process.stdout.write(decryptSecret(input, key));
else {
  process.stderr.write("vault-cli: usage: encrypt|decrypt (value on stdin)\n");
  process.exit(2);
}
