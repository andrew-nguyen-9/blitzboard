// C01 — explicit player-value unit contracts. The wire fields are:
//   value.vor          mean VOR        = projection mean − positional replacement (raw points scale)
//   value.replacement  replacement     = positional replacement baseline (raw points)
//   value.boom         ceiling VOR     = projection ceiling − replacement  (NOT a raw ceiling)
//   value.bust         floor VOR       = projection floor − replacement
//   value.value        shaped draft value (unitless board score — never compare with points)
// A raw projection may never be compared with a replacement-adjusted value; convert first
// with these helpers. Missing inputs degrade to null explicitly — no silent substitution.
import type { PlayerWithValue } from "./types";

/** Raw season projection mean (points). */
export function projectionMean(p: PlayerWithValue): number {
  return (p.value?.vor ?? 0) + (p.value?.replacement ?? 0);
}

/** Ceiling VOR (points over replacement); null when unavailable. */
export function ceilingVor(p: PlayerWithValue): number | null {
  return p.value?.boom ?? null;
}

/** Raw season projection ceiling (points); null when boom or replacement is missing. */
export function projectionCeiling(p: PlayerWithValue): number | null {
  const b = p.value?.boom;
  const r = p.value?.replacement;
  return b != null && r != null ? b + r : null;
}
