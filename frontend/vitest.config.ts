import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

// Unit tests target pure logic (viz geometry, number formatting) and server-side
// auth/data helpers (mocked) — node env, no DOM. Component behavior is covered by the
// Playwright/axe QA harness. The "@/" alias mirrors tsconfig so tests import like app code.
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    // The full 12-team auto-draft sims (draftAI.*.test.ts) run 15–30s each; the
    // 5s default made them flake as timeouts under machine load. Generous global
    // ceiling keeps the suite deterministic without per-test overrides.
    testTimeout: 60000,
    include: [
      "lib/**/*.test.ts",
      "components/**/*.test.ts",
      "app/**/*.test.ts",
    ],
  },
});
