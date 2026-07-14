// Shapes the Model Lab renders from an engine snapshot's model-ops payload
// (E7-calibration.done.md: R-hat / ESS / divergences convergence diagnostics +
// reliability curve; E0 snapshot). All fields optional so a partial/empty run
// degrades to "no data" rather than throwing.

// One parameter's MCMC convergence diagnostics (per E1 convergence gate / E7).
export interface ParamDiagnostic {
  name: string;
  rhat?: number | null; // Gelman–Rubin R̂ → want ≈ 1.0 (< 1.01 good)
  ess?: number | null; // effective sample size → want high (> 400 good)
}

export interface McmcDiagnostics {
  params: ParamDiagnostic[];
  divergences?: number | null; // # of divergent transitions → want 0
  draws?: number | null; // total post-warmup draws (for ESS context)
}

// One bin of a reliability diagram (E7 reliability_curve): mean predicted vs
// observed frequency. On a calibrated model the points hug the y = x diagonal.
export interface ReliabilityPoint {
  predicted: number; // mean predicted probability in the bin ∈ [0,1]
  observed: number; // empirical frequency in the bin ∈ [0,1]
  count?: number | null; // sample count in the bin (for weighting / tooltip)
}
