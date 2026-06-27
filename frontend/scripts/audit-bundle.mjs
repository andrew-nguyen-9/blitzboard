// Security guard (v2.5.2.2): the client bundle must never carry a service-role key or any
// server-only secret. Scans the built client chunks (.next/static) for forbidden tokens and
// fails the build if any appear. Only NEXT_PUBLIC_* (anon key, URLs) may ship to the client;
// the service-role key (bypasses RLS) lives solely in the pipeline/server env.
//
// Run from frontend/:  node scripts/audit-bundle.mjs   (after `npm run build`)
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";

const STATIC_DIR = ".next/static";

// Literal tokens that should never appear in a client chunk. "service_role" is the role claim
// in a Supabase service key and a giveaway for any hardcoded reference; the env names catch a
// stray inlined secret.
const FORBIDDEN = ["service_role", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SERVICE_ROLE_KEY"];

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (p.endsWith(".js")) out.push(p);
  }
  return out;
}

if (!existsSync(STATIC_DIR)) {
  console.error(`audit-bundle: ${STATIC_DIR} not found — run \`npm run build\` first.`);
  process.exit(1);
}

const files = walk(STATIC_DIR);
const hits = [];
for (const f of files) {
  const src = readFileSync(f, "utf8");
  for (const tok of FORBIDDEN) {
    if (src.includes(tok)) hits.push(`${f}: contains "${tok}"`);
  }
}

if (hits.length) {
  console.error("audit-bundle: FORBIDDEN secrets in client bundle:\n  " + hits.join("\n  "));
  process.exit(1);
}
console.log(`audit-bundle: ok — scanned ${files.length} client chunks, no service-role/secret tokens.`);
