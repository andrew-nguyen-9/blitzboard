# C04 independent acceptance contract

Status: preparation only. This document does not define production implementation and is not a
checkpoint verdict. C02 and C03 interfaces are unfinished; names below are semantic requirements,
not proposed TypeScript field names.

## Scoring components

Every candidate trace must expose six separately attributable numeric results. A result may be
`null` only with an explicit degraded/unsupported state and named missing inputs.

| Component | Required meaning | Minimum evidence | Forbidden substitution |
|---|---|---|---|
| immediate lineup contribution | Candidate's marginal legal-starting-lineup gain for the actual roster slots | before/after lineup assignment, eligible slot, score units | raw player rank or projection without a legal assignment |
| bye/absence coverage | Marginal expected starts created by the candidate | week, slot, starter id; candidate availability; maximum-matching result | same-position count, same-bye credit, or ineligible-slot credit |
| contingent role | Expected inherited role from explicit succession evidence | starter id, evidence kind/source, inheritance probability, expected value or degraded state | teammate/position proximity or ambiguous depth |
| breakout option value | Value of a plausible ceiling outcome over the current lineup/replacement bar | upside basis and units, projection/evidence id | mixed raw/VOR units or unsupported narrative labels |
| waiver replacement/churn | Cost/value relative to C02's bounded point-in-time replacement and churn output | C02 output id, value, transaction/churn basis | a browser simulation or a constant silently presented as measured |
| redundancy cost | Soft marginal cost of already-covered roles/positions | roster assignment and shared-shape evidence/fallback status | a hard positional cap derived from the C03 soft shape |

The scoring total must be reproducible from structured components plus any separately named legacy
term. Explanations may summarize components, but may not invent a claim absent from the structured
result.

## Explanation payload semantics

The production payload must carry:

- covered `week`, eligible `slot`, and `starter_id`;
- contingent `starter_id`, supporting evidence identifiers, and inheritance probability, or an
  explicit degraded state when probability cannot be supported;
- an upside basis with units/evidence;
- replacement/churn value with C02 evidence or a visible dependency/fallback state;
- redundancy value and basis;
- league-configuration evidence state and the resolved league key;
- exactly one of `measured`, `interpolated`, `unsupported`, or `fallback` for each C03-derived value;
- a list of degraded or missing inputs at component and overall levels.

`measured` requires a canonical league key and canonical source hash. Interpolation must identify
its source rows/method. Unsupported custom configurations may fall back, but the UI and trace must
retain `unsupported`/`fallback`; neither may be relabeled measured.

## Canonical/browser parity (pending C03)

The future parity test will load, without modifying, the canonical C03 bench-shape artifact and its
browser-safe generated artifact. It must prove:

1. equal schema version and canonical source hash;
2. equal normalized league keys, evidence states, soft costs, and fallback metadata;
3. deterministic generation and drift failure after a one-field mutation;
4. no frontend import of the canonical engine artifact and no runtime generation/simulation;
5. no interpretation of a soft cost as candidate ineligibility or a positional maximum.

Exact filenames, serialization order, and field names remain deliberately unspecified until C03
publishes its accepted interface.

## Runtime budget

The live browser scorer may perform one deterministic board evaluation per pick. It may walk the
bounded candidate pool and use deterministic matching/lookup work. It may not invoke Monte Carlo,
season simulation, repeated stochastic trials, engine Python, or runtime artifact generation.

The executable guard currently proves one score result and, when jitter is enabled, one RNG sample
per candidate. C04 production should preserve the stronger budget:

`rng_calls <= candidate_count`, `simulation_trials = 0`, `season_rollouts = 0`.

