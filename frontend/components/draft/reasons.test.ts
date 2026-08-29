import { describe, it, expect } from "vitest";
import { reasonChips } from "./reasons";

describe("reasonChips", () => {
  it("maps the four brief dimensions and orders need first", () => {
    const chips = reasonChips({ need: true, vona: true, scarce: true, run: true });
    expect(chips).toEqual([
      { key: "need", label: "fills need", title: "Fills one of your open starting slots" },
      {
        key: "vona",
        label: "next-turn edge",
        title: "Projected lineup value over the estimated next-turn replacement; next-turn survival probability unavailable",
      },
      { key: "scarce", label: "scarce", title: "Starter-caliber supply here is running thin" },
      { key: "run", label: "recent run", title: "Recent picks are concentrated at this position" },
    ]);
  });

  it("falls back without claiming optimality", () => {
    expect(reasonChips({})).toEqual([
      { key: "value", label: "board alternative", title: "One of the four current BlitzBoard options" },
    ]);
  });

  it("bounds rank-gap and upside claims to their actual inputs", () => {
    expect(reasonChips({ value: true, upside: true })).toEqual([
      {
        key: "value",
        label: "rank/ADP gap · source/date unknown",
        title: "BlitzBoard rank is 12+ picks earlier than stored ADP; source/date unavailable",
      },
      {
        key: "upside",
        label: "upside",
        title: "Projection ceiling is at least 12% above projection mean; not a probability",
      },
    ]);
  });
});
