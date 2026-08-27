# C03A-codex — independent failed-candidate disposition review

## Verdict: PASS

- reviewed correction base: `573e9ab2e127b6be79937c2c6cd32b5fc7227f3d`
- disposition amendment: `8e4ff5fdc7083016c343bf2016aabbe0e310aa22`
- production correction: `1f70ed6b9f7ca599192f6637f0d90f3d5c473c97`
- reviewed checkpoint head: `0e1af27c3585da5f3d1ec79f0bcd7596c7d41a5d`
- reviewer-gate amendment: `03be8aa313ca778956cffb8bc4379a97efea75b3`
- review order: correction diff, immutable evidence, independent gates, and blind findings first;
  `C03A-claude.md` reconciled afterward

## Correction evidence

The append-only v5 amendment precedes correction behavior and binds the authoritative
`do_not_promote` result to consumer eligibility. Results-v1 and source-v1 remain immutable negative
evidence. Source-v2 preserves their exact hashes, exposes all nine candidate rows as unsupported,
and declares no interpolation sources. The canonical and generated artifacts hash source-v2
exactly and expose all 216 rows as unsupported, degraded, finite soft fallback with no hard caps.

Accepted C02C behavior is preserved through `fixtures/bench_shape_c02c.json`, whose SHA-256
`b672610e291aa97f5be7853c16c2e53db201f74638257acc40e7c129c46ad2ee` exactly matches
`417af276:fixtures/bench_shape.json`. Full-matrix tests prove `bench_bounds`, K/DST timing, and
solver requirements retain the accepted values. Schema v2 no longer activates failed portfolio
guidance or removes accepted bounds.

The authoritative experiment was not rerun or reinterpreted. All nine mandatory slices remain
uncleared and `t14-2qb-std-te0.5-b4-ir1` remains unsupported. Frozen interface records, manifests
v1-v4, results-v1, source-v1, and `C03-claude.md` retain their original Git blobs.

## Independent verification

- amended reviewer disposition gate: **1 passed**
- focused C03/C02C suite: **556 passed**
- Ruff: clean
- generator parity: exact
- source-v2 reproduction: exact/no rewrite
- canonical rows: 216 unsupported; source-v2 rows: 9 unsupported
- accepted C02C fixture hash and full-matrix bounds: exact
- `git diff --check`: clean
- producer and reviewer worktrees: clean at verdict

Producer hashes, frontend resolver tests, TypeScript, build, artifact sizes, and the pre-existing
hook warning reconcile with the checkpoint record.

## Ownership and integration disposition

Producer commit `0da40d9954336665300c7577e7abb4222c462b8a` duplicates the reviewer-owned gate and amendment
from review commit `03be8aa`. It is not accepted as production-owned content and must be omitted
when transferring commits. This is non-blocking because the production correction commits contain
no dependency on those paths.

Integrate C03 commits individually in chronological order, omitting `0da40d9`. The correction tail
accepted for production is `8e4ff5f`, `1f70ed6`, then checkpoint record `0e1af27`; retain the earlier
reviewed C03 chain required by those commits. Inspect every cherry-pick and stop on any unexpected
reviewer-path dependency or conflict. Do not merge the disposable branch wholesale.

## Gate disposition

C03 is accepted as negative evidence plus safe shared-artifact infrastructure. No failed portfolio
selection is promoted: consumer guidance remains unsupported and accepted C02C behavior remains
authoritative. C04 may be recreated only after these accepted production-owned commits are
integrated onto `v6/bench-portfolio` and the combined tree is verified.

This verdict does not authorize push, protected-branch merge, PR, release, or branch/worktree
deletion.
