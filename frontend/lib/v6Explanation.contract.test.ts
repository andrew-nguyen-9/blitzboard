import { describe, expect, it } from "vitest";

type EvidenceState = "measured" | "interpolated" | "unsupported" | "fallback";
type ComponentName =
  | "immediate_lineup"
  | "bye_absence_coverage"
  | "contingent_role"
  | "breakout_option"
  | "waiver_replacement_churn"
  | "redundancy_cost";

interface ComponentResult {
  name: ComponentName;
  value: number | null;
  state: EvidenceState;
  degraded_inputs: string[];
  evidence_ids: string[];
}

interface ExplanationPayload {
  candidate_id: string;
  league_evidence: { state: EvidenceState; league_key: string | null; source_hash: string | null };
  components: ComponentResult[];
  covered_assignments: { week: number; slot: string; starter_id: string }[];
  contingent: { starter_id: string; evidence_ids: string[]; inheritance_probability: number | null; degraded_state: string | null } | null;
  upside_basis: { kind: string; evidence_ids: string[] } | null;
  replacement_churn: { value: number | null; evidence_ids: string[]; degraded_state: string | null };
  redundancy: { value: number | null; evidence_ids: string[] };
  claims: { component: ComponentName; text: string; evidence_ids: string[] }[];
}

const COMPONENTS: ComponentName[] = [
  "immediate_lineup",
  "bye_absence_coverage",
  "contingent_role",
  "breakout_option",
  "waiver_replacement_churn",
  "redundancy_cost",
];

function contractErrors(payload: ExplanationPayload): string[] {
  const errors: string[] = [];
  const byName = new Map(payload.components.map((component) => [component.name, component]));
  for (const required of COMPONENTS) if (!byName.has(required)) errors.push(`missing component:${required}`);
  if (payload.league_evidence.state === "measured" && (!payload.league_evidence.league_key || !payload.league_evidence.source_hash)) {
    errors.push("measured league evidence lacks key/hash");
  }
  for (const claim of payload.claims) {
    const component = byName.get(claim.component);
    if (!component || component.value == null) errors.push(`claim lacks structured result:${claim.component}`);
    if (claim.evidence_ids.length === 0 || claim.evidence_ids.some((id) => !component?.evidence_ids.includes(id))) {
      errors.push(`claim lacks component evidence:${claim.component}`);
    }
  }
  if (payload.contingent && payload.contingent.inheritance_probability == null && !payload.contingent.degraded_state) {
    errors.push("contingent probability lacks degraded state");
  }
  return errors;
}

function completePayload(): ExplanationPayload {
  return {
    candidate_id: "candidate",
    league_evidence: { state: "measured", league_key: "t12-superflex-half-te0.0-b4-ir0", source_hash: "sha256:fixture" },
    components: COMPONENTS.map((name, index) => ({ name, value: index - 1, state: "measured", degraded_inputs: [], evidence_ids: [`e-${name}`] })),
    covered_assignments: [{ week: 8, slot: "OP", starter_id: "starter-qb" }],
    contingent: { starter_id: "starter-rb", evidence_ids: ["depth-feed"], inheritance_probability: 0.25, degraded_state: null },
    upside_basis: { kind: "ceiling_vor", evidence_ids: ["projection"] },
    replacement_churn: { value: 2.5, evidence_ids: ["c02-waiver"], degraded_state: null },
    redundancy: { value: -1.5, evidence_ids: ["roster-shape"] },
    claims: COMPONENTS.map((component) => ({ component, text: component, evidence_ids: [`e-${component}`] })),
  };
}

describe("C04 explanation payload contract (producer-independent)", () => {
  it("requires all six component results and accepts evidence-backed claims", () => {
    expect(contractErrors(completePayload())).toEqual([]);
  });

  it("rejects prose that is unsupported by the structured scoring result", () => {
    const payload = completePayload();
    payload.components = payload.components.filter((component) => component.name !== "contingent_role");
    expect(contractErrors(payload)).toContain("claim lacks structured result:contingent_role");
  });

  it("never permits unsupported/interpolated configuration evidence to be described as measured", () => {
    const payload = completePayload();
    payload.league_evidence = { state: "measured", league_key: null, source_hash: null };
    expect(contractErrors(payload)).toContain("measured league evidence lacks key/hash");
    for (const state of ["interpolated", "unsupported", "fallback"] as const) {
      payload.league_evidence = { state, league_key: null, source_hash: null };
      expect(contractErrors(payload)).not.toContain("measured league evidence lacks key/hash");
    }
  });

  it("makes missing inheritance evidence visibly degraded", () => {
    const payload = completePayload();
    payload.contingent = { starter_id: "starter-rb", evidence_ids: [], inheritance_probability: null, degraded_state: null };
    expect(contractErrors(payload)).toContain("contingent probability lacks degraded state");
    payload.contingent.degraded_state = "missing_authoritative_depth";
    expect(contractErrors(payload)).not.toContain("contingent probability lacks degraded state");
  });

  it("retains covered week, eligible slot, and starter identity as structured data", () => {
    const assignment = completePayload().covered_assignments[0];
    expect(assignment).toEqual({ week: 8, slot: "OP", starter_id: "starter-qb" });
  });
});

describe.skip("C04 production explanation adapter — blocked on C03/C02 interfaces", () => {
  it("maps the future live scorer payload into the producer-independent contract", () => {});
  it("carries C02 replacement/churn value without reconstructing it in the browser", () => {});
});

