// Pure diagnostic scoring for the Lab. Thresholds mirror the E1 convergence gate /
// standard HMC practice (R̂ < 1.01, ESS > 400, 0 divergences). Status is encoded
// as an enum (never colour alone) so the table can pair an icon + label with the
// colour — colourblind-safe per ACCESSIBILITY.md.
import type { McmcDiagnostics, ParamDiagnostic, ReliabilityPoint } from "./types";

export type Status = "ok" | "warn" | "bad" | "unknown";

// R̂: 1.0 ideal. < 1.01 converged; < 1.05 borderline; otherwise not converged.
export function rhatStatus(rhat: number | null | undefined): Status {
  if (rhat == null || !Number.isFinite(rhat)) return "unknown";
  if (rhat < 1.01) return "ok";
  if (rhat < 1.05) return "warn";
  return "bad";
}

// ESS: bigger is better. > 400 healthy; > 100 usable-but-thin; otherwise too few.
export function essStatus(ess: number | null | undefined): Status {
  if (ess == null || !Number.isFinite(ess)) return "unknown";
  if (ess >= 400) return "ok";
  if (ess >= 100) return "warn";
  return "bad";
}

// Divergences: any is a warning, many a hard problem (biased posterior geometry).
export function divergenceStatus(n: number | null | undefined): Status {
  if (n == null || !Number.isFinite(n)) return "unknown";
  if (n === 0) return "ok";
  if (n <= 5) return "warn";
  return "bad";
}

// Worst status across all params + divergences → the run's headline health.
export function overallStatus(d: McmcDiagnostics): Status {
  const order: Status[] = ["ok", "warn", "bad"];
  let worst = 0;
  const bump = (s: Status) => {
    const i = order.indexOf(s);
    if (i > worst) worst = i;
  };
  for (const p of d.params) {
    bump(rhatStatus(p.rhat));
    bump(essStatus(p.ess));
  }
  bump(divergenceStatus(d.divergences));
  const anyKnown =
    d.params.some((p) => p.rhat != null || p.ess != null) || d.divergences != null;
  return anyKnown ? order[worst] : "unknown";
}

// Expected Calibration Error: count-weighted mean |observed − predicted| across the
// reliability bins (0 = perfectly on the diagonal). Null when there's nothing to
// score. Complements E7's KS/PIT gate with a single legible headline number.
export function expectedCalibrationError(points: ReliabilityPoint[]): number | null {
  const valid = points.filter(
    (p) => Number.isFinite(p.predicted) && Number.isFinite(p.observed),
  );
  if (valid.length === 0) return null;
  const totalW = valid.reduce((s, p) => s + (p.count ?? 1), 0) || valid.length;
  const weighted = valid.reduce(
    (s, p) => s + (p.count ?? 1) * Math.abs(p.observed - p.predicted),
    0,
  );
  return weighted / totalW;
}

// Sort params worst-first so problems surface at the top of the table.
export function byWorstFirst(params: ParamDiagnostic[]): ParamDiagnostic[] {
  const rank = (p: ParamDiagnostic) => {
    const order: Status[] = ["ok", "warn", "bad", "unknown"];
    const worst = Math.max(order.indexOf(rhatStatus(p.rhat)), order.indexOf(essStatus(p.ess)));
    // bad(2) first, then warn(1), ok(0), unknown(3) last → remap.
    return worst === 3 ? -1 : worst;
  };
  return [...params].sort((a, b) => rank(b) - rank(a));
}
