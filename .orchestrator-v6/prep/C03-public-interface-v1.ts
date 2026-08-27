/** Frozen C03→C04 declarations. Contract only; this file is not production implementation. */

export const C03_BENCH_SHAPE_SCHEMA_VERSION = 2 as const;
export const C03_BENCH_SHAPE_POSITION_ORDER = ["QB", "RB", "WR", "TE", "K", "DST"] as const;

export type BenchShapePosition = typeof C03_BENCH_SHAPE_POSITION_ORDER[number];
export type BenchShapeEvidenceStatus = "measured" | "interpolated" | "unsupported";
export type LeagueConfigKey = `t${10 | 12 | 14}-${"1qb" | "superflex" | "2qb"}-${
  "std" | "half" | "ppr"
}-te${"0.0" | "0.5"}-b${4 | 8}-ir${0 | 1}`;

export type PositionCounts = Readonly<Record<BenchShapePosition, number>>;
export type SoftMarginalCosts = Readonly<Record<BenchShapePosition, readonly number[]>>;

export interface MeasuredBenchShapeProvenance {
  readonly kind: "measured";
  readonly source_receipt: string;
  readonly producer_sha: string;
  readonly evaluator_sha: string;
  readonly n_pairs: number;
  readonly seeds: readonly number[];
}

export interface InterpolatedBenchShapeProvenance {
  readonly kind: "interpolated";
  readonly source_receipt: string;
  readonly source_keys: readonly LeagueConfigKey[];
  readonly method: string;
}

export interface UnsupportedBenchShapeProvenance {
  readonly kind: "unsupported";
  readonly reason: string;
  readonly nearest_measured_keys?: readonly LeagueConfigKey[];
}

export type BenchShapeProvenance =
  | MeasuredBenchShapeProvenance
  | InterpolatedBenchShapeProvenance
  | UnsupportedBenchShapeProvenance;

export interface BenchShapeRow {
  readonly league_config_key: LeagueConfigKey;
  readonly evidence_status: BenchShapeEvidenceStatus;
  readonly bench_slots: 4 | 8;
  readonly composition: PositionCounts;
  readonly soft_marginal_costs: SoftMarginalCosts;
  readonly provenance: BenchShapeProvenance;
}

export interface BenchShapeArtifact {
  readonly schema_version: typeof C03_BENCH_SHAPE_SCHEMA_VERSION;
  readonly canonical_source_hash: string;
  readonly canonical_source_receipt: string;
  readonly rows: Readonly<Partial<Record<LeagueConfigKey, BenchShapeRow>>>;
}

export type BenchShapeDegradedReason =
  | "missing_league_key"
  | "malformed_artifact"
  | "schema_version_mismatch"
  | "source_hash_mismatch"
  | "bench_budget_mismatch"
  | "unsupported_evidence";

export interface BenchShapeResolution {
  readonly leagueConfigKey: LeagueConfigKey;
  readonly evidenceStatus: BenchShapeEvidenceStatus;
  readonly composition: PositionCounts;
  readonly softMarginalCosts: SoftMarginalCosts;
  readonly provenance: BenchShapeProvenance;
  readonly degraded: boolean;
  readonly degradedReason: BenchShapeDegradedReason | null;
  /** Always null: v1 shapes are soft costs and never positional caps. */
  readonly hardCaps: null;
}

/** C04 consumer seam; C03 supplies the implementation after the interface freeze. */
export type ResolveBenchShape = (
  key: LeagueConfigKey,
  benchSlots: number,
) => BenchShapeResolution;

/** Required static exports of frontend/lib/generated/benchShape.generated.ts. */
export interface GeneratedBenchShapeModule {
  readonly BENCH_SHAPE_SCHEMA_VERSION: typeof C03_BENCH_SHAPE_SCHEMA_VERSION;
  readonly BENCH_SHAPE_CANONICAL_SOURCE_HASH: string;
  readonly BENCH_SHAPE_CANONICAL_SOURCE_RECEIPT: string;
  readonly BENCH_SHAPE_ROWS: BenchShapeArtifact["rows"];
}
