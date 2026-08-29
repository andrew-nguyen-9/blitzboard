// The legible "why" behind a live recommendation, in the four dimensions the
// brief calls out: VONA (value over next available) / scarcity / run-risk / need.
// Pure mapping from precomputed booleans → ordered, deduped chips, so the panel
// stays dumb and this stays unit-tested. Reasoning never colour-only: each chip
// carries a text label + title.
export type WhyKey = "vona" | "scarce" | "run" | "need" | "upside" | "value";

export interface WhyChip {
  key: WhyKey;
  label: string;
  title: string;
}

export interface ReasonInput {
  need?: boolean; // fills one of my open starter slots
  scarce?: boolean; // starter-caliber supply at the position is thin
  run?: boolean; // recent picks are concentrated at this position
  vona?: boolean; // projected lineup value over the estimated next-turn replacement
  upside?: boolean; // ceiling at least 12% above projection mean
  value?: boolean; // BlitzBoard rank is 12+ picks earlier than stored ADP
}

const CHIP: Record<WhyKey, { label: string; title: string }> = {
  vona: {
    label: "next-turn edge",
    title: "Projected lineup value over the estimated next-turn replacement; next-turn survival probability unavailable",
  },
  scarce: { label: "scarce", title: "Starter-caliber supply here is running thin" },
  run: { label: "recent run", title: "Recent picks are concentrated at this position" },
  need: { label: "fills need", title: "Fills one of your open starting slots" },
  upside: { label: "upside", title: "Projection ceiling is at least 12% above projection mean; not a probability" },
  value: {
    label: "rank/ADP gap · source/date unknown",
    title: "BlitzBoard rank is 12+ picks earlier than stored ADP; source/date unavailable",
  },
};

// Order reflects decision priority: need first, then the market forces.
const ORDER: WhyKey[] = ["need", "vona", "scarce", "run", "value", "upside"];

export function reasonChips(input: ReasonInput): WhyChip[] {
  const chips = ORDER.filter((k) => input[k]).map((k) => ({ key: k, ...CHIP[k] }));
  return chips.length ? chips : [{ key: "value", label: "board alternative", title: "One of the four current BlitzBoard options" }];
}
