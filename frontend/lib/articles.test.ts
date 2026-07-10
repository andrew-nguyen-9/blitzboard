import { describe, expect, it } from "vitest";
import { articleBlocks, articleDate } from "./articles";

describe("articleBlocks", () => {
  it("splits blank-line paragraphs into text blocks", () => {
    const blocks = articleBlocks("First para.\n\nSecond para.");
    expect(blocks).toEqual([
      { kind: "text", text: "First para." },
      { kind: "text", text: "Second para." },
    ]);
  });

  it("coalesces consecutive '- ' lines into one list", () => {
    const blocks = articleBlocks("Windy venues:\n- BUF: 22 mph\n- CHI: 18 mph");
    expect(blocks).toEqual([
      { kind: "text", text: "Windy venues:" },
      { kind: "list", items: ["BUF: 22 mph", "CHI: 18 mph"] },
    ]);
  });

  it("handles the real pace-body shape (lead-in + two lists)", () => {
    const body = "Fastest:\n- BUF: 26.0s/play\n- DET: 24.5s/play\n\nSlowest:\n- TEN: 30.0s/play";
    expect(articleBlocks(body)).toEqual([
      { kind: "text", text: "Fastest:" },
      { kind: "list", items: ["BUF: 26.0s/play", "DET: 24.5s/play"] },
      { kind: "text", text: "Slowest:" },
      { kind: "list", items: ["TEN: 30.0s/play"] },
    ]);
  });

  it("is empty-safe", () => {
    expect(articleBlocks("")).toEqual([]);
    // @ts-expect-error guarding a null body at runtime
    expect(articleBlocks(null)).toEqual([]);
  });
});

describe("articleDate", () => {
  it("formats an ISO date and no-ops on falsy/garbage", () => {
    expect(articleDate("2025-09-10T12:00:00+00:00")).toMatch(/Sep 10, 2025|Sep 9, 2025/);
    expect(articleDate(null)).toBe("");
    expect(articleDate("not-a-date")).toBe("");
  });
});
