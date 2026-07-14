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
  run?: boolean; // a positional run is underway → get ahead of it
  vona?: boolean; // large value over the player I'd still get next turn
  upside?: boolean; // ceiling well above median
  value?: boolean; // falling past ADP → market value
}

const CHIP: Record<WhyKey, { label: string; title: string }> = {
  vona: { label: "VONA", title: "Big value over the next available at this position" },
  scarce: { label: "scarce", title: "Starter-caliber supply here is running thin" },
  run: { label: "run-risk", title: "A run is underway — get ahead of it" },
  need: { label: "fills need", title: "Fills one of your open starting slots" },
  upside: { label: "upside", title: "Ceiling well above the median outcome" },
  value: { label: "ADP value", title: "Falling past ADP — a market value" },
};

// Order reflects decision priority: need first, then the market forces.
const ORDER: WhyKey[] = ["need", "vona", "scarce", "run", "value", "upside"];

export function reasonChips(input: ReasonInput): WhyChip[] {
  const chips = ORDER.filter((k) => input[k]).map((k) => ({ key: k, ...CHIP[k] }));
  return chips.length ? chips : [{ key: "value", label: "best value", title: "Best available value on the board" }];
}
