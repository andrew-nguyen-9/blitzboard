import { test, expect } from "vitest";
import { cursorTipClass, cursorTipContent, cursorTipOffset } from "./CursorTooltip";

const row = { label: "Rank", value: "#1" };

test("show with rows → populated; empty/null → nothing (hide)", () => {
  expect(cursorTipContent({ title: "X", rows: [row] })).toEqual({ title: "X", rows: [row] });
  expect(cursorTipContent({ title: "X", rows: [] })).toBeNull();
  expect(cursorTipContent(null)).toBeNull();
});

test("reduced-motion branch adds no transition class", () => {
  expect(cursorTipClass(true)).not.toContain("transition");
  expect(cursorTipClass(false)).toContain("transition-opacity");
});

test("offset trails the cursor, flips at the right/bottom edge", () => {
  expect(cursorTipOffset(10, 10, 100, 50, 800, 600)).toEqual({ x: 24, y: 24 });
  // near right/bottom: flip to the opposite side, never off-screen
  expect(cursorTipOffset(790, 590, 100, 50, 800, 600)).toEqual({ x: 676, y: 526 });
  expect(cursorTipOffset(5, 5, 100, 50, 40, 30)).toEqual({ x: 0, y: 0 });
});
