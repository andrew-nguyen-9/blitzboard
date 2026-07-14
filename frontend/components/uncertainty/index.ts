// Public surface of the uncertainty kit. E8-draft-room / lineup compose these.
export { default as UncertaintyStrip } from "./UncertaintyStrip";
export { default as RangeBar } from "./RangeBar";
export { default as MiniDistribution } from "./MiniDistribution";
export { default as ProbabilityBadges } from "./ProbabilityBadges";
export { playerUncertainty } from "./fromValue";
export type { ValueLike, ProjectionLike } from "./fromValue";
export type { PlayerUncertainty, QuantilePoint, McProbs } from "./types";
export {
  quantileAt,
  rangeFromQuantiles,
  gaussianQuantiles,
  bustProbability,
  normCdf,
  asProbability,
  sortQuantiles,
} from "./quantiles";
export type { Range } from "./quantiles";
