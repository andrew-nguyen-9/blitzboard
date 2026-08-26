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
    // Exit-1-after-green fix: the auto-draft sims are synchronous CPU-bound blocks;
    // at 8 concurrent fork workers on 8 cores the worker<->main RPC starves past
    // vitest's 60s onTaskUpdate timeout ("[vitest-worker]: Timeout calling
    // \"onTaskUpdate\""), failing the run AFTER every assertion passed. Capping
    // workers at half the cores keeps the event loops responsive; reproduced 2x
    // failing at 8 workers, 2x green at 4. No test is skipped or masked.
    maxWorkers: 4,
    include: [
      "lib/**/*.test.ts",
      "components/**/*.test.ts",
      "app/**/*.test.ts",
    ],
  },
});
