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
    include: [
      "lib/**/*.test.ts",
      "components/**/*.test.ts",
      "app/**/*.test.ts",
    ],
  },
});
