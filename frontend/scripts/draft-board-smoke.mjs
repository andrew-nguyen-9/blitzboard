import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";

const HOST = "127.0.0.1";
const POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"];

function players() {
  let rank = 0;
  return POSITIONS.flatMap((position) =>
    Array.from({ length: 16 }, (_, index) => {
      rank += 1;
      const id = `synthetic-${position.toLowerCase()}-${index + 1}`;
      return {
        player_id: id,
        engine: "vorp",
        value: 300 - rank,
        vor: 200 - rank,
        replacement: 100,
        boom: 220 - rank,
        bust: 160 - rank,
        adp: rank + 8,
        rank: rank === 12 ? null : rank,
        predictability: null,
        players: {
          id,
          sleeper_id: id,
          espn_id: null,
          full_name: position === "QB" && index === 0
            ? "Synthetic Quarterback With A Deliberately Long Name 01"
            : `Synthetic ${position} ${String(index + 1).padStart(2, "0")}`,
          position,
          nfl_team: ["BUF", "KC", "PHI", "SF"][index % 4],
          bye_week: 7 + (index % 4),
          age: 25,
          years_exp: 3,
          status: "active",
          injury_status: null,
          metadata: { depth_chart_order: 1 },
        },
      };
    }),
  );
}

async function listen(server) {
  server.listen(0, HOST);
  await once(server, "listening");
  return server.address().port;
}

async function freePort() {
  const server = createServer();
  const port = await listen(server);
  await new Promise((resolve) => server.close(resolve));
  return port;
}

function mockSupabase(rows) {
  return createServer((req, res) => {
    res.setHeader("access-control-allow-origin", "*");
    res.setHeader("content-type", "application/json");
    if (req.method === "OPTIONS") return res.end();
    if (req.url?.startsWith("/rest/v1/player_value")) return res.end(JSON.stringify(rows));
    if (req.url?.startsWith("/rest/v1/user_leagues")) return res.end("[]");
    if (req.url?.startsWith("/auth/v1/user")) {
      res.statusCode = 401;
      return res.end('{"message":"synthetic signed-out fixture"}');
    }
    res.end("[]");
  });
}

async function waitForApp(url, child, logs) {
  for (let attempt = 0; attempt < 90; attempt += 1) {
    if (child.exitCode != null) throw new Error(`Next exited early (${child.exitCode})\n${logs.join("")}`);
    try {
      const response = await fetch(url);
      if (response.ok && (await response.text()).includes("Draft Board")) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${url}\n${logs.join("")}`);
}

async function checkViewport(browser, base, width) {
  const context = await browser.newContext({ viewport: { width, height: 812 } });
  const page = await context.newPage();
  await page.goto(`${base}/draft`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Draft Board", level: 1 }).waitFor();

  const layout = await page.evaluate(() => {
    const recommendation = document.querySelector('[aria-label="Draft recommendations"]');
    const table = document.querySelector('[aria-label="Available player table"]');
    return {
      viewport: innerWidth,
      pageWidth: document.documentElement.scrollWidth,
      recommendationBeforeTable: Boolean(recommendation && table && recommendation.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING),
      tableOverflow: table ? table.scrollWidth > table.clientWidth : false,
    };
  });
  assert.equal(layout.pageWidth, layout.viewport, `${width}px page must not overflow`);
  assert.equal(layout.recommendationBeforeTable, true, `${width}px recommendation must precede table`);
  if (width === 320) assert.equal(layout.tableOverflow, true, `${width}px table must own horizontal overflow`);

  const violations = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze()).violations;
  const blocking = violations.filter((violation) => ["serious", "critical"].includes(violation.impact) && violation.id !== "target-size");
  const targetNodes = violations.find(({ id }) => id === "target-size")?.nodes.length ?? 0;
  if (targetNodes) console.log(`${width}px target-size findings recorded: ${targetNodes}`);
  const axeSummary = blocking.flatMap(({ id, nodes }) => nodes.map((node) => `${id} ${node.target.join(" ")}: ${node.failureSummary}`));
  assert.deepEqual(blocking.map(({ id }) => id), [], `${width}px axe: ${axeSummary.join(" | ")}`);

  if (width === 1280) {
    const recommendation = await page.locator('[aria-label="Draft recommendations"]').boundingBox();
    const table = await page.locator('[aria-label="Available player table"]').boundingBox();
    assert(recommendation && table && recommendation.x > table.x, "desktop recommendation must lead the right rail");
  }
  await context.close();
}

async function checkPreferences(browser, base) {
  const context = await browser.newContext({
    viewport: { width: 320, height: 812 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto(`${base}/draft`, { waitUntil: "networkidle" });

  assert.equal(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches), true);
  const transitionSeconds = await page.getByRole("button", { name: "Manual", exact: true }).evaluate((element) => {
    const duration = getComputedStyle(element).transitionDuration;
    return Number.parseFloat(duration) / (duration.endsWith("ms") ? 1000 : 1);
  });
  assert(transitionSeconds <= 0.000001, "draft controls must collapse transitions under reduced motion");

  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark");
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  assert.equal(await page.locator("html").getAttribute("data-theme"), "light");
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 320, "light theme must not introduce page overflow");

  const lightViolations = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze()).violations;
  const lightBlocking = lightViolations.filter((violation) => ["serious", "critical"].includes(violation.impact) && violation.id !== "target-size");
  const lightSummary = lightBlocking.flatMap(({ id, nodes }) => nodes.map((node) => `${id} ${node.target.join(" ")}: ${node.failureSummary}`));
  assert.deepEqual(lightBlocking.map(({ id }) => id), [], `light theme must retain the populated board axe baseline: ${lightSummary.join(" | ")}`);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark");
  await page.evaluate(() => localStorage.setItem("ffdt-a11y-contrast", "high"));
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(await page.locator("html").getAttribute("data-contrast"), "high");
  const contrastViolations = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze()).violations;
  const contrastBlocking = contrastViolations.filter((violation) => ["serious", "critical"].includes(violation.impact) && violation.id !== "target-size");
  assert.deepEqual(contrastBlocking.map(({ id }) => id), [], "high-contrast preference must retain the populated board axe baseline");
  await context.close();
}

async function checkSleeperState(browser, base, stalled) {
  const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const page = await context.newPage();
  await page.route("**/api/sleeper/draft/**", async (route) => {
    if (stalled) return route.fulfill({ status: 503, contentType: "application/json", body: '{"error":"synthetic feed stall"}' });
    const body = route.request().url().endsWith("/picks")
      ? "[]"
      : '{"draft_id":"synthetic-live","status":"drafting","type":"snake","settings":{"teams":12,"rounds":16}}';
    return route.fulfill({ status: 200, contentType: "application/json", body });
  });
  await page.goto(`${base}/draft`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Sleeper Live" }).click();
  await page.getByLabel("Sleeper draft ID").fill("synthetic-live");
  await page.getByLabel("Sleeper draft ID").press("Enter");

  if (stalled) {
    const alert = page.getByRole("alert").filter({ hasText: "feed stalled" });
    await alert.waitFor();
    assert.match(await alert.textContent(), /SLEEPER feed stalled \(picks 503\)/);
    const fallback = page.getByRole("button", { name: /Switch to manual/ });
    await fallback.focus();
    await page.keyboard.press("Enter");
    assert.equal(await page.getByRole("button", { name: "Manual", exact: true }).getAttribute("aria-pressed"), "true");
    await alert.waitFor({ state: "hidden" });
  } else {
    const state = page.getByText("Sleeper live", { exact: true });
    await state.waitFor();
    assert.equal(await state.getAttribute("aria-live"), "polite");
  }
  await context.close();
}

async function exerciseDraft(browser, base) {
  const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const page = await context.newPage();
  await page.goto(`${base}/draft`, { waitUntil: "networkidle" });
  const recommendationRegion = page.locator('[aria-label="Draft recommendations"]');
  await recommendationRegion.scrollIntoViewIfNeeded();
  const compactBox = await recommendationRegion.boundingBox();
  assert(compactBox && compactBox.height <= 812, "compact recommendation region must fit a 375x812 decision viewport");
  console.log(`375px compact recommendation region recorded: ${Math.ceil(compactBox.height)}px high`);
  await recommendationRegion.getByText("Primary", { exact: true }).waitFor();
  assert.equal(await recommendationRegion.getByText("Alternative", { exact: true }).count(), 3);
  await recommendationRegion.getByText("Limited evidence", { exact: true }).waitFor();
  const evidenceSummary = recommendationRegion.getByText("Full evidence for 4 candidates", { exact: false });
  await evidenceSummary.waitFor();
  assert.equal(await page.getByRole("button", { name: "Manual", exact: true }).getAttribute("aria-pressed"), "true");
  assert.equal(await page.getByRole("button", { name: "board", exact: true }).getAttribute("aria-pressed"), "true");
  await page.getByRole("button", { name: "Sleeper Live" }).click();
  await page.getByLabel("Sleeper draft ID").waitFor();
  await page.getByRole("button", { name: "ESPN Live" }).click();
  await page.getByLabel("ESPN league ID").waitFor();
  await page.getByRole("button", { name: "Manual", exact: true }).click();

  const status = page.getByRole("status", { name: "Draft status" });
  assert.equal(await status.getAttribute("aria-live"), "polite");
  assert.equal(await status.getAttribute("aria-atomic"), "true");
  await page.getByRole("button", { name: "Sim to my pick" }).click();
  await status.getByText("YOUR PICK", { exact: true }).waitFor();

  const snapshot = await page.evaluate(() => JSON.parse(localStorage.getItem("ffdt:draft:v1")));
  assert.equal(snapshot.picks.length, 5);
  assert.equal(new Set(snapshot.picks.map((pick) => pick.player.id)).size, 5);
  assert.deepEqual(snapshot.picks.map((pick) => pick.team), [1, 2, 3, 4, 5]);

  const recommendationDraft = page.locator('[aria-label="Draft recommendations"]').getByRole("button", { name: /^Draft .+ to my team$/ }).first();
  const tableDraft = page.locator('[aria-label="Available player table"] button').first();
  for (const [label, locator] of [["recommendation", recommendationDraft], ["table", tableDraft]]) {
    const box = await locator.boundingBox();
    assert(box && box.width >= 44 && box.height >= 44, `${label} action must meet the 44px product goal`);
  }

  const actionBeforeDisclosure = await recommendationDraft.boundingBox();
  await evidenceSummary.click();
  await recommendationRegion.getByRole("heading", { name: /Synthetic/ }).first().waitFor();
  const actionAfterDisclosure = await recommendationDraft.boundingBox();
  assert.equal(actionAfterDisclosure?.y, actionBeforeDisclosure?.y, "opening full evidence must not move the draft action");
  await evidenceSummary.click();

  await page.getByLabel("Search available players").fill("Synthetic QB 12");
  const missingRankRow = page.getByRole("row", { name: /Synthetic QB 12/ });
  await missingRankRow.getByText("BlitzBoard rank unavailable").waitFor();
  await page.getByRole("columnheader", { name: "BlitzBoard rank" }).waitFor();
  await page.getByRole("columnheader", { name: "Projected fantasy points" }).waitFor();
  await page.getByLabel("Search available players").fill("not-a-synthetic-player");
  await page.getByText("No players match.", { exact: true }).waitFor();
  await page.getByLabel("Search available players").fill("");
  await page.getByRole("button", { name: "WR", exact: true }).focus();
  await page.keyboard.press("Space");
  assert.equal(await page.getByRole("button", { name: "WR", exact: true }).getAttribute("aria-pressed"), "true");
  await page.getByRole("button", { name: "ALL", exact: true }).click();

  await recommendationDraft.click();
  await page.getByRole("button", { name: "Undo" }).click();
  await page.getByText("YOUR PICK", { exact: true }).waitFor();
  await page.getByText("Simulation tools", { exact: true }).click();
  await page.getByRole("button", { name: "Auto-draft all" }).waitFor();

  await page.evaluate(() => {
    document.body.tabIndex = -1;
    document.body.focus();
  });
  let reachedRecommendation = false;
  for (let index = 0; index < 40; index += 1) {
    await page.keyboard.press("Tab");
    const state = await page.evaluate(() => ({
      recommendation: Boolean(document.activeElement?.closest('[aria-label="Draft recommendations"]')),
      table: Boolean(document.activeElement?.closest('[aria-label="Available player table"]')),
    }));
    assert.equal(state.table && !reachedRecommendation, false, "table action must not precede recommendation focus");
    if (state.recommendation) reachedRecommendation = true;
  }
  assert.equal(reachedRecommendation, true, "keyboard traversal must reach recommendations before the table");
  await context.close();
}

const rows = players();
const supabase = mockSupabase(rows);
const supabasePort = await listen(supabase);
const appPort = await freePort();
const logs = [];
const fetchGuard = `data:text/javascript,${encodeURIComponent(`
  const realFetch = globalThis.fetch;
  globalThis.fetch = (input, ...args) => {
    const url = typeof input === "string" ? input : input.url;
    return url.includes("nflverse-data/releases/download/schedules/games.csv")
      ? Promise.resolve(new Response("", { status: 503 }))
      : realFetch(input, ...args);
  };
`)}`;
const next = spawn("npm", ["run", "dev", "--", "--hostname", HOST, "--port", String(appPort)], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    NEXT_PUBLIC_SUPABASE_URL: `http://${HOST}:${supabasePort}`,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "synthetic-anon-key",
    NEXT_PUBLIC_SITE_URL: `http://${HOST}:${appPort}`,
    NODE_OPTIONS: [process.env.NODE_OPTIONS, `--import=${fetchGuard}`].filter(Boolean).join(" "),
  },
  stdio: ["ignore", "pipe", "pipe"],
});
next.stdout.on("data", (chunk) => logs.push(chunk.toString()));
next.stderr.on("data", (chunk) => logs.push(chunk.toString()));

let browser;
try {
  const base = `http://${HOST}:${appPort}`;
  await waitForApp(`${base}/draft`, next, logs);
  browser = await chromium.launch();
  for (const width of [320, 375, 640, 1280]) await checkViewport(browser, base, width);
  await checkPreferences(browser, base);
  await checkSleeperState(browser, base, false);
  await checkSleeperState(browser, base, true);
  await exerciseDraft(browser, base);
  console.log("draft board smoke: 96 synthetic players, 4 viewports, themes, high contrast, reduced motion, synthetic feed states, axe, and interactions passed");
  console.log("manual QA limits: 320 CSS px represents 200% reflow; native browser zoom, VoiceOver speech, and the 192-pick complete state remain unverified");
} finally {
  await browser?.close();
  next.kill("SIGTERM");
  await Promise.race([once(next, "exit"), new Promise((resolve) => setTimeout(resolve, 5000))]);
  await new Promise((resolve) => supabase.close(resolve));
}
