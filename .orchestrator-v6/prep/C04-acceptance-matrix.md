# C04 independent acceptance matrix

This is a preparation artifact, not a C04 verdict. `now` means executable against accepted C01A.
C02 is accepted at `417af276dd4438d8a35f38d08bfc26206044925e` (review `f2a1537`);
C03 is accepted and integrated at `8694d98186e5800e5439725973bb8789ebdb2979`. Its canonical
artifact is intentionally all-unsupported after `do_not_promote`; this is executable evidence, not
a measured-row dependency.

| Requirement | Evidence/test | Status |
|---|---|---|
| immediate lineup component contract | `v6DraftExplanation.ts`; interface-consumer tests | executable now |
| bye/absence component and week/slot/starter | integration, contract, and interface-consumer tests | executable now |
| contingent role component/evidence/probability | structured payload and formatter tests | executable now |
| breakout option component/upside basis | structured payload and formatter tests | executable now |
| waiver replacement/churn component | candidate transaction adapter plus aggregate-only degradation | executable now; producer transaction source still absent |
| redundancy cost component | accepted resolver soft curve consumer | executable; unsupported state preserved and score behavior reconciled |
| evidence state measured/interpolated/unsupported/fallback | accepted resolver adapter and formatting tests | executable unsupported/fallback; artifact proves no measured/interpolated rows exist |
| degraded/missing inputs visible | explanation contract; ambiguous-depth test | executable now |
| 1QB trace, four-slot bench, no IR | `c04-1qb-b4-noir` | executable accepted unsupported resolution |
| 1QB TE premium, eight-slot bench, IR | `c04-1qb-tep-b8-ir` | executable accepted unsupported resolution |
| superflex, four-slot bench | `c04-superflex-b4-noir` | executable accepted unsupported resolution |
| pure 2QB, TE premium, eight-slot bench, IR | `c04-2qb-tep-b8-ir` | executable accepted unsupported resolution |
| custom roster shape | `c04-custom-wrte-no-k-noir` | executable missing-key fallback |
| legal starters | parameterized `fillRoster` adversarial test | executable now |
| no early duplicate K/DST | `isCapped` adversarial test | executable now |
| no unsupported backup-QB mandate in 1QB | legal-fill/bench test | executable now |
| appropriate SF/2QB scarcity | legal-fill plus SF bench-score contrast | executable now; C03 shape effect pending |
| no hard cap from soft bench shape | deep-depth frozen-resolver consumer test | executable now |
| defensible insurance/upside mixture | live structured six-component payload | executable; missing candidate transaction evidence degrades |
| unsupported config never called measured | explanation negative contract | executable now |
| missing evidence visibly degrades | explanation and ambiguous-depth negatives | executable now |
| no WR/TE teammate handcuff false positive | contingent valuation negative | executable now |
| ambiguous QB/RB depth | contingent valuation negative | executable now |
| same-bye false coverage | weekly coverage negative | executable now |
| ineligible-slot false coverage | weekly coverage negative | executable now |
| prose unsupported by structured result | explanation negative contract | executable now |
| canonical/browser parity and drift failure | actual canonical/generated hash and row-key tests | executable now |
| no frontend Monte Carlo/simulation | draftAI and C04 adapter static guards; operation counters | executable now |
| deterministic per-pick operation budget | one RNG call per candidate test | executable now |
| producer-blind representative trace fixtures | noncanonical JSON and actual resolver trace contract | executable now with unsupported/fallback provenance |
| paired points outcome identity/accounting | composite-reference and net-accounting test for `per_season` | accepted C02 field; producer-issued id absent |
| paired H2H outcome identity/accounting | composite-reference and gross-accounting test for `per_season_h2h` | accepted C02 field; producer-issued id absent |
| paired playoff-proxy identity/accounting | gross-proxy contract/skipped adapter for `per_season_playoff` | accepted C02 field; producer-issued id absent |
| paired championship-proxy identity/accounting | gross-proxy contract/skipped adapter for `per_season_champ` | accepted C02 field; producer-issued id absent |
| frozen `ResolveBenchShape` signature consumption | synthetic plus accepted implementation adapter tests | executable now |
| deterministic producer-blind trace | `v6DraftTrace.ts` serialization test | executable now |
| UI-independent explanation formatting | structured-claim positive/negative tests | executable now |
| live score/payload reconciliation | `v6DraftLiveScoring.test.ts` | executable: component total + named residual = shipped score |

## Future schema assumptions (nonbinding)

- Accepted C03 supplies the normalized league key, schema version, canonical source hash,
  unsupported evidence state, finite soft costs, and fallback provenance.
- The browser artifact carries the canonical source hash and row keys; C04 verifies both directly.
- Accepted C02 exposes deterministic aggregate emergency/upside/total adds and paired sample
  families with explicit net/gross semantics, but not candidate transactions or an evidence id.
  C04 consumes a future producer-issued
  candidate reference rather than reconstructing one; until then it degrades explicitly.
- C04 returns structured component values before formatting explanation prose.
