import { defineConfig } from "vitest/config";

// Unit tests target pure logic (viz geometry, number formatting) — node env,
// no DOM. Component behavior is covered by the Playwright/axe QA harness.
export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts", "components/**/*.test.ts"],
  },
});
