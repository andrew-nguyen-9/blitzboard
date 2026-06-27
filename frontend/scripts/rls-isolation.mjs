// RLS isolation proof (v2.5.2.1) — proves user A cannot read or write user B's rows.
//
// GATED: needs a live Supabase project. Run with the project URL + keys in env:
//   NEXT_PUBLIC_SUPABASE_URL=... NEXT_PUBLIC_SUPABASE_ANON_KEY=... \
//   SUPABASE_SERVICE_ROLE_KEY=... node scripts/rls-isolation.mjs
//
// The service-role key is used ONLY here (a server-side test) to create two throwaway users;
// the isolation assertions run through the ANON key + each user's session, exactly as the app
// does. Exits non-zero on any isolation failure. Cleans up the test users afterward.
import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const service = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !anon || !service) {
  console.error("rls-isolation: set NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY");
  process.exit(2);
}

const admin = createClient(url, service, { auth: { autoRefreshToken: false, persistSession: false } });
const pw = "Test!" + Math.random().toString(36).slice(2) + "Aa1";
const stamp = Date.now();
const emails = [`rlstest+a-${stamp}@example.com`, `rlstest+b-${stamp}@example.com`];
const failures = [];
const ids = [];

function check(cond, msg) {
  if (cond) console.log(`  ok: ${msg}`);
  else { console.error(`  FAIL: ${msg}`); failures.push(msg); }
}

async function signedInClient(email) {
  const c = createClient(url, anon, { auth: { autoRefreshToken: false, persistSession: false } });
  const { error } = await c.auth.signInWithPassword({ email, password: pw });
  if (error) throw new Error(`sign-in ${email}: ${error.message}`);
  return c;
}

try {
  // create two confirmed users (the signup trigger creates their accounts rows)
  for (const email of emails) {
    const { data, error } = await admin.auth.admin.createUser({ email, password: pw, email_confirm: true });
    if (error) throw new Error(`createUser ${email}: ${error.message}`);
    ids.push(data.user.id);
  }
  const [idA, idB] = ids;
  const a = await signedInClient(emails[0]);

  // A reads its own row
  const ownRow = await a.from("accounts").select("user_id").eq("user_id", idA).maybeSingle();
  check(ownRow.data?.user_id === idA, "A can read its own accounts row");

  // A cannot read B's row (RLS returns 0 rows, not an error)
  const bRow = await a.from("accounts").select("user_id").eq("user_id", idB).maybeSingle();
  check(!bRow.data, "A cannot read B's accounts row");

  // A's unfiltered select returns ONLY A's row
  const all = await a.from("accounts").select("user_id");
  check(Array.isArray(all.data) && all.data.length === 1 && all.data[0].user_id === idA,
    "A's unfiltered select returns only its own row");

  // A cannot write B's row (update affects 0 rows under RLS)
  const upd = await a.from("accounts").update({ display_name: "hijacked" }).eq("user_id", idB).select();
  check(Array.isArray(upd.data) && upd.data.length === 0, "A cannot update B's accounts row");
} catch (e) {
  console.error("rls-isolation error:", e.message);
  failures.push(e.message);
} finally {
  for (const id of ids) await admin.auth.admin.deleteUser(id).catch(() => {});
}

if (failures.length) { console.error(`\nrls-isolation: ${failures.length} FAILURE(S)`); process.exit(1); }
console.log("\nrls-isolation: PASS — cross-user reads and writes are denied by RLS.");
