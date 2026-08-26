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

