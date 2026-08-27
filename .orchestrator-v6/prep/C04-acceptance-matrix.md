# C04 independent acceptance matrix

This is a preparation artifact, not a C04 verdict. `now` means executable against accepted C01A.
C02 is accepted at `417af276dd4438d8a35f38d08bfc26206044925e` (review `f2a1537`);
C03's provisional interface is frozen at `a3394b0a6c72174894bd8a44b33c702372903d11`, but C03 has
not passed and canonical measured artifacts remain an honest dependency.

| Requirement | Evidence/test | Status |
|---|---|---|
| immediate lineup component contract | `v6DraftExplanation.ts`; interface-consumer tests | executable now |
| bye/absence component and week/slot/starter | integration, contract, and interface-consumer tests | executable now |
| contingent role component/evidence/probability | structured payload and formatter tests | executable now |
| breakout option component/upside basis | structured payload and formatter tests | executable now |
| waiver replacement/churn component | candidate transaction adapter plus aggregate-only degradation | executable now; producer transaction source still absent |
| redundancy cost component | frozen resolver soft curve consumer | executable synthetic resolution; measured value blocked C03 PASS |
| evidence state measured/interpolated/unsupported/fallback | resolver adapter and formatting tests | executable synthetic unsupported/fallback; measured artifact blocked C03 PASS |
| degraded/missing inputs visible | explanation contract; ambiguous-depth test | executable now |
| 1QB trace, four-slot bench, no IR | `c04-1qb-b4-noir` | fixture spec now; golden blocked C03/C02 |
| 1QB TE premium, eight-slot bench, IR | `c04-1qb-tep-b8-ir` | fixture spec now; golden blocked C03/C02 |
| superflex, four-slot bench | `c04-superflex-b4-noir` | fixture spec now; golden blocked C03 |
| pure 2QB, TE premium, eight-slot bench, IR | `c04-2qb-tep-b8-ir` | fixture spec now; golden blocked C03 |
| custom roster shape | `c04-custom-wrte-no-k-noir` | fixture spec now; fallback golden blocked C03 |
| legal starters | parameterized `fillRoster` adversarial test | executable now |
| no early duplicate K/DST | `isCapped` adversarial test | executable now |
| no unsupported backup-QB mandate in 1QB | legal-fill/bench test | executable now |
| appropriate SF/2QB scarcity | legal-fill plus SF bench-score contrast | executable now; C03 shape effect pending |
| no hard cap from soft bench shape | deep-depth frozen-resolver consumer test | executable now |
| defensible insurance/upside mixture | trace specs, six components, accepted emergency/upside counters | aggregate distinction accepted C02; candidate mixture blocked C03/C04 payload |
| unsupported config never called measured | explanation negative contract | executable now |
| missing evidence visibly degrades | explanation and ambiguous-depth negatives | executable now |
| no WR/TE teammate handcuff false positive | contingent valuation negative | executable now |
| ambiguous QB/RB depth | contingent valuation negative | executable now |
| same-bye false coverage | weekly coverage negative | executable now |
| ineligible-slot false coverage | weekly coverage negative | executable now |
| prose unsupported by structured result | explanation negative contract | executable now |
| canonical/browser parity and drift failure | parity specification and skipped trace test | blocked C03 PASS/measured artifacts |
| no frontend Monte Carlo/simulation | draftAI and C04 adapter static guards; operation counters | executable now |
| deterministic per-pick operation budget | one RNG call per candidate test | executable now |
| producer-blind representative trace fixtures | noncanonical JSON and trace contract | executable specification; goldens blocked C03 and candidate-level C02 evidence |
| paired points outcome identity/accounting | composite-reference and net-accounting test for `per_season` | accepted C02 field; producer-issued id absent |
| paired H2H outcome identity/accounting | composite-reference and gross-accounting test for `per_season_h2h` | accepted C02 field; producer-issued id absent |
| paired playoff-proxy identity/accounting | gross-proxy contract/skipped adapter for `per_season_playoff` | accepted C02 field; producer-issued id absent |
| paired championship-proxy identity/accounting | gross-proxy contract/skipped adapter for `per_season_champ` | accepted C02 field; producer-issued id absent |
| frozen `ResolveBenchShape` signature consumption | `v6DraftExplanation.c03Interface.test.ts` typed resolver mock | executable now |
| deterministic producer-blind trace | `v6DraftTrace.ts` serialization test | executable now |
| UI-independent explanation formatting | structured-claim positive/negative tests | executable now |

## Future schema assumptions (nonbinding)

- C03 supplies a stable normalized league key, schema version, canonical source hash, evidence state,
  soft component costs, and enough fallback provenance to distinguish unsupported from interpolated.
- The browser artifact carries semantically equivalent data and the canonical source hash; C04 does
  not infer parity from filenames or build timestamps.
- Accepted C02 exposes deterministic aggregate emergency/upside/total adds and paired sample
  families with explicit net/gross semantics, but not candidate transactions or an evidence id.
  C04 consumes a future producer-issued
  candidate reference rather than reconstructing one; until then it degrades explicitly.
- C04 returns structured component values before formatting explanation prose.
