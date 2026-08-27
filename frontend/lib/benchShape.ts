// C03 browser-safe bench-shape lookup. Static data + finite arithmetic only.
import {
  BENCH_SHAPE_CANONICAL_SOURCE_HASH,
  BENCH_SHAPE_ROWS,
  BENCH_SHAPE_SCHEMA_VERSION,
} from "./generated/benchShape.generated";

export const BENCH_SHAPE_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"] as const;
export type BenchShapePosition = typeof BENCH_SHAPE_POSITIONS[number];
export type BenchShapeEvidenceStatus = "measured" | "interpolated" | "unsupported";
export type LeagueConfigKey = `t${10 | 12 | 14}-${"1qb" | "superflex" | "2qb"}-${
  "std" | "half" | "ppr"
}-te${"0.0" | "0.5"}-b${4 | 8}-ir${0 | 1}`;
export type PositionCounts = Readonly<Record<BenchShapePosition, number>>;
export type SoftMarginalCosts = Readonly<Record<BenchShapePosition, readonly number[]>>;
export type BenchShapeDegradedReason =
  | "missing_league_key"
  | "malformed_artifact"
  | "schema_version_mismatch"
  | "source_hash_mismatch"
  | "bench_budget_mismatch"
  | "unsupported_evidence";

export interface BenchShapeResolution {
  leagueConfigKey: LeagueConfigKey;
  evidenceStatus: BenchShapeEvidenceStatus;
  composition: PositionCounts;
  softMarginalCosts: SoftMarginalCosts;
  provenance: Readonly<Record<string, unknown>>;
  degraded: boolean;
  degradedReason: BenchShapeDegradedReason | null;
  hardCaps: null;
}

const balanced = (benchSlots: number): PositionCounts => {
  const out = { QB: 0, RB: 0, WR: 0, TE: 0, K: 0, DST: 0 };
  const order = ["RB", "WR", "QB", "TE", "K", "DST"] as const;
  for (let i = 0; i < Math.max(0, benchSlots); i++) out[order[i % order.length]]++;
  return out;
};

const softFallback = (benchSlots: number): SoftMarginalCosts =>
  Object.fromEntries(BENCH_SHAPE_POSITIONS.map((position) => [
    position,
    Array.from({ length: Math.max(0, benchSlots) + 1 }, (_, depth) => 0.25 * depth),
  ])) as unknown as SoftMarginalCosts;

const fallback = (
  key: LeagueConfigKey,
  benchSlots: number,
  reason: BenchShapeDegradedReason,
): BenchShapeResolution => ({
  leagueConfigKey: key,
  evidenceStatus: "unsupported",
  composition: balanced(benchSlots),
  softMarginalCosts: softFallback(benchSlots),
  provenance: { kind: "unsupported", reason },
  degraded: true,
  degradedReason: reason,
  hardCaps: null,
});

export function resolveBenchShape(key: LeagueConfigKey, benchSlots: number): BenchShapeResolution {
  if (BENCH_SHAPE_SCHEMA_VERSION !== 2) return fallback(key, benchSlots, "schema_version_mismatch");
  if (!/^[0-9a-f]{64}$/.test(BENCH_SHAPE_CANONICAL_SOURCE_HASH)) {
    return fallback(key, benchSlots, "source_hash_mismatch");
  }
  const row = (BENCH_SHAPE_ROWS as Readonly<Record<string, unknown>>)[key] as {
    evidence_status?: BenchShapeEvidenceStatus;
    composition?: PositionCounts;
    soft_marginal_costs?: SoftMarginalCosts;
    provenance?: Readonly<Record<string, unknown>>;
  } | undefined;
  if (!row) return fallback(key, benchSlots, "missing_league_key");
  if (!row.composition || !row.soft_marginal_costs || !row.provenance) {
    return fallback(key, benchSlots, "malformed_artifact");
  }
  const total = BENCH_SHAPE_POSITIONS.reduce((sum, p) => sum + row.composition![p], 0);
  if (total !== benchSlots) return fallback(key, benchSlots, "bench_budget_mismatch");
  const validCosts = BENCH_SHAPE_POSITIONS.every((p) =>
    row.soft_marginal_costs![p].length === benchSlots + 1 &&
    row.soft_marginal_costs![p].every(Number.isFinite));
  if (!validCosts || !row.evidence_status) return fallback(key, benchSlots, "malformed_artifact");
  const degraded = row.evidence_status === "unsupported";
  return {
    leagueConfigKey: key,
    evidenceStatus: row.evidence_status,
    composition: row.composition,
    softMarginalCosts: row.soft_marginal_costs,
    provenance: row.provenance,
    degraded,
    degradedReason: degraded ? "unsupported_evidence" : null,
    hardCaps: null,
  };
}

export function benchMarginalCost(
  shape: BenchShapeResolution,
  position: BenchShapePosition,
  ownedBenchCount: number,
): number {
  const curve = shape.softMarginalCosts[position];
  const depth = Math.min(Math.max(0, Math.trunc(ownedBenchCount)), curve.length - 1);
  return curve[depth] ?? 0;
}
