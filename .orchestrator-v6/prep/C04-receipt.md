# C04 preparation receipt

Date: 2026-08-26. Branch: `v6/c04-prep`. Base: C01A
`b81541c226dd5aeeacbe9ed79df927853a4b8954`.

## Commands and results

Run from the dedicated worktree unless noted.

```text
cd frontend
./node_modules/.bin/vitest run \
  lib/v6DraftIntegration.adversarial.test.ts \
  lib/v6DraftTrace.contract.test.ts \
  lib/v6Explanation.contract.test.ts

3 test files passed
21 tests passed, 9 skipped (dependency-blocked)
```

```text
cd frontend
npm run typecheck

exit 0
```

```text
cd frontend
npm test

57 test files passed
513 tests passed, 9 skipped
exit 0
```

```text
git diff --check

exit 0
```

The worktree reused the main checkout's already-installed `frontend/node_modules` through an
ignored local symlink. The symlink is runtime-only and is not committed.

## Intentional skips/dependencies

- 7 parameterized golden live-trace/parity/soft-shape assertions: blocked until C03 publishes the
  accepted canonical and browser-safe schema/artifacts.
- 2 production explanation-adapter assertions: blocked until C03 publishes shape evidence and C02
  publishes replacement/churn outputs.

Skipped tests are retained as collection-visible requirements. No production behavior or canonical
artifact was changed to make them pass.

## Provisional C02 follow-up

After the original preparation commit, provisional C02 commit
`edbcc4d743b447ebcbbfe84a0e1210380c6250d1` was inspected read-only. C04-owned contracts now record
its aggregate waiver counters, churn-related configuration, four paired sample field identifiers,
and `paired_ci` result shape. Candidate transaction/replacement evidence and stable producer-issued
outcome identifiers remain absent and intentionally dependency-blocked. All assumptions remain
provisional pending independent C02 acceptance and any later interface revision.

Follow-up verification:

```text
cd frontend
./node_modules/.bin/vitest run \
  lib/v6DraftIntegration.adversarial.test.ts \
  lib/v6DraftTrace.contract.test.ts \
  lib/v6Explanation.contract.test.ts

3 test files passed
23 tests passed, 13 skipped (C03/candidate-adapter dependencies)
```

```text
cd frontend
./node_modules/.bin/tsc --noEmit

exit 0
```

## Accepted C02 reconciliation

C02 was subsequently accepted at production head
`417af276dd4438d8a35f38d08bfc26206044925e`, review commit `f2a1537`. The C04-owned contract was
reconciled without importing or editing production. The aggregate counters and paired field names
survived, while the accepted transaction semantics now explicitly bind the future adapter: strict
remaining-horizon cost gate, single net-points charge, gross on-field H2H/proxies, one shared weekly
allowance, roster-wide feasible drops, and OP/SFLX/SUPERFLEX equivalence. Candidate transactions
and producer-issued evidence identifiers remain absent, so their adapters stay skipped pending C03.

Accepted-interface reconciliation verification:

```text
focused C04 vitest: 3 files passed; 24 passed, 13 skipped
TypeScript (`tsc --noEmit`): exit 0
```

## Frozen C03 interface branch

Base: `a3394b0a6c72174894bd8a44b33c702372903d11`. The three C04 preparation commits were
cherry-picked in order without conflict. `frontend/npm ci` installed 426 packages locally. Before
implementation, the frozen declaration compiled directly with strict TypeScript settings. C04 then
added only new explanation/trace modules and interface-consumer tests; all frozen C03 files remain
byte-identical to the base.

Verification before the interface-implementation commit:

```text
frozen C03 declaration, strict standalone TypeScript compile: exit 0
frozen C03 interface pytest: 4 passed
focused C04 vitest: 4 files passed; 33 passed, 16 skipped
frontend typecheck: exit 0
full frontend vitest: 58 files passed; 525 passed, 16 skipped
frozen C03 file diff against a3394b0: empty
git diff --check: exit 0
```

The 16 visible skips are 13 inherited C04 preparation cases plus 3 frozen-resolver cases requiring
canonical measured/interpolated artifacts and parity. No checkpoint verdict is implied.
