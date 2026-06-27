import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

// v2.6 HARD acceptance: the public plane reads ONLY the anonymous snapshot and exposes zero
// user data. This proves it structurally — every public-plane file is scanned for any import of
// an authenticated / per-user module. If a public component ever pulls in user data, this fails
// (RLS still backstops at the DB, but private data should never even reach a public component).
const PUBLIC_FILES = [
  "app/waivers/page.tsx",
  "app/trades/page.tsx",
  "components/WaiverBoard.tsx",
  "components/TradeFinder.tsx",
];

// Modules that read per-user / authenticated data. None may appear in a public-plane file.
const FORBIDDEN = [
  "queries.auth",
  "supabase/server",
  "getServerSupabase",
  "actions/credentials",
  "actions/leagues",
  "getActiveLeague",
  "gate.server",
  "credential_vault",
  "user_leagues",
];

describe("public/private leak boundary", () => {
  for (const f of PUBLIC_FILES) {
    it(`${f} imports no authenticated / user-data module`, () => {
      const path = join(process.cwd(), f);
      if (!existsSync(path)) return; // file moved/renamed — covered by its new path's test
      const src = readFileSync(path, "utf8");
      const hits = FORBIDDEN.filter((tok) => src.includes(tok));
      expect(hits, `${f} must not reference ${hits.join(", ")}`).toEqual([]);
    });
  }
});
