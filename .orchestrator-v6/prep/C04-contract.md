# C04 independent acceptance contract

Status: preparation only. This document does not define production implementation and is not a
checkpoint verdict. C02 is accepted at production head
`417af276dd4438d8a35f38d08bfc26206044925e` (review `f2a1537`); C03 is accepted and integrated at
`8694d98186e5800e5439725973bb8789ebdb2979` with an intentionally all-unsupported artifact.
Names below are semantic requirements, not proposed TypeScript field names.

## Scoring components

Every candidate trace must expose six separately attributable numeric results. A result may be
`null` only with an explicit degraded/unsupported state and named missing inputs.

| Component | Required meaning | Minimum evidence | Forbidden substitution |
|---|---|---|---|
| immediate lineup contribution | Candidate's marginal legal-starting-lineup gain for the actual roster slots | before/after lineup assignment, eligible slot, score units | raw player rank or projection without a legal assignment |
| bye/absence coverage | Marginal expected starts created by the candidate | week, slot, starter id; candidate availability; maximum-matching result | same-position count, same-bye credit, or ineligible-slot credit |
| contingent role | Expected inherited role from explicit succession evidence | starter id, evidence kind/source, inheritance probability, expected value or degraded state | teammate/position proximity or ambiguous depth |
| breakout option value | Value of a plausible ceiling outcome over the current lineup/replacement bar | upside basis and units, projection/evidence id | mixed raw/VOR units or unsupported narrative labels |
| waiver replacement/churn | Cost/value relative to C02's bounded point-in-time replacement and churn output | C02 evidence id, candidate/transaction value, transaction/churn basis | aggregate adds presented as candidate value, a browser simulation, or a constant silently presented as measured |
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

Accepted production artifact bytes are authoritative. There are no measured or interpolated rows;
C04 must preserve that absence rather than synthesizing either status.

### Provisional frozen-interface implementation

C04 consumes the accepted browser resolver through a narrow adapter satisfying the frozen v1
`ResolveBenchShape` signature. `v6DraftExplanation.ts` uses exactly one resolver call, maps
non-evidence failures to visible `fallback`, preserves honest `unsupported`, reads only finite soft
marginal costs, and never turns depth into candidate ineligibility. `v6DraftLiveScoring.ts` decorates
the shipped deterministic score with six structured components and a named legacy-policy residual;
unsupported C03 costs do not silently alter the shipped total. Canonical/generated hash and row-key
parity are executable. Candidate-level waiver evidence remains absent and degrades explicitly.

## Accepted C02 interface reconciliation

Read-only inspection of accepted C02 production head
`417af276dd4438d8a35f38d08bfc26206044925e` and PASS review `f2a1537` confirms:

- aggregate per-seat means: `emergency_adds`, `upside_adds`, and backward-compatible
  `waiver_adds = emergency_adds + upside_adds`;
- configuration inputs relevant to churn: `proactive_moves_per_week`, `upgrade_margin`,
  `waiver_cost`, and `season_moves_cap`;
- paired sample families: `per_season`, `per_season_h2h`, `per_season_playoff`, and
  `per_season_champ`;
- `paired_ci(a, b, seats, field)` returning `{mean, lo, hi, n}`.

Accepted transaction semantics additionally require:

- `waiver_cost` is a strict remaining-horizon decision gate and a single accounting charge; an
  equal-or-below-cost claim does not transact;
- `per_season`/`started_points` are net of that charge, while H2H and playoff/championship proxies
  remain gross on-field outcomes;
- emergency and upside claims draw from one weekly allowance, with emergencies first, and retain a
  shared season cap;
- upside drops are roster-wide feasible: the lowest forward-looking nonstarter is preferred, the
  add must be legal in the actual slot shape, and a started body is dropped only if lineup coverage
  does not decrease;
- `SUPERFLEX`, `OP`, and `SFLX` are equivalent QB/RB/WR/TE aliases; K/DST are ineligible.

The accepted interfaces still do **not** publish transaction-level add/drop records,
candidate-level replacement or churn value, a browser-safe result, or a stable producer-issued
evidence/outcome identifier. Therefore C04 must not convert aggregate waiver-add counts into
candidate explanation value.

Until a producer publishes an identifier, acceptance fixtures may use a reviewer-local composite reference
of `(producer_commit, seed, seats, field, n_seasons)` to prevent outcome-family collisions. This is
test bookkeeping only, not a production identifier contract. A production explanation must consume
a stable producer-issued reference or visibly degrade with
`aggregate_only_no_candidate_transactions`.

The paired field identifiers above distinguish net points, gross H2H, gross playoff proxy, and
gross championship proxy. The latter two remain explicitly proxies; C04 explanations must not
describe them as observed playoff qualification or championships, and no comparison may silently
mix the net and gross accounting families.

## Runtime budget

The live browser scorer may perform one deterministic board evaluation per pick. It may walk the
bounded candidate pool and use deterministic matching/lookup work. It may not invoke Monte Carlo,
season simulation, repeated stochastic trials, engine Python, or runtime artifact generation.

The executable guard currently proves one score result and, when jitter is enabled, one RNG sample
per candidate. C04 production should preserve the stronger budget:

`rng_calls <= candidate_count`, `simulation_trials = 0`, `season_rollouts = 0`.
