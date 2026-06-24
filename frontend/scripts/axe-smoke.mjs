// Accessibility smoke test: load the running app and assert no serious/critical
// axe violations on the shell routes. Non-blocking in CI until the shell is
// remediated in v2.0.3 (see .github/workflows/ci.yml), then flipped to blocking.
//
// Usage: BASE_URL=http://localhost:3000 node scripts/axe-smoke.mjs
import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const ROUTES = ["/"]; // expand as the shell grows; v2.0.3 adds the full shell audit
const BLOCKING_IMPACTS = new Set(["serious", "critical"]);

const browser = await chromium.launch();
const context = await browser.newContext();
let violationCount = 0;

for (const route of ROUTES) {
  const page = await context.newPage();
  await page.goto(BASE + route, { waitUntil: "networkidle" });

  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();

  const blocking = violations.filter((v) => BLOCKING_IMPACTS.has(v.impact));
  for (const v of blocking) {
    console.log(`✗ ${route} [${v.impact}] ${v.id}: ${v.help} — ${v.nodes.length} node(s)`);
  }
  violationCount += blocking.length;
  await page.close();
}

await browser.close();
console.log(
  violationCount
    ? `\naxe smoke: ${violationCount} serious/critical violation(s)`
    : "axe smoke: clean",
);
process.exit(violationCount ? 1 : 0);
