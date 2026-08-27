# C05 — reconciliation against accepted C03 (2026-08-26)

Append-only preparation record. C03 accepted and integrated at
`8694d98186e5800e5439725973bb8789ebdb2979` (chronology in its `C03A-claude.md`: C02C base
`417af276`, C03 checkpoint `573e9ab`, official BLOCK review `ff50f69`, disposition amendment
`8e4ff5f`, bounded C03A correction `1f70ed6`). Nothing was edited: not `promotion-v3.json`, not
any existing record; no candidate SHA frozen, no execution addendum, no authoritative run. The
C05 adapter branch remains PARKED at accepted-C02 head `417af276` pending C04 PASS.

## Frozen board-corpus hashes at 8694d98 — ALL VERIFY

| File | sha256 at 8694d98 | vs promotion-v3 frozen |
|---|---|---|
| `fixtures/seasons/2018.json` | `5a819045a106f31ab4335ccfb392949da49a7bc6ee8cd591ba428959246b1e51` | identical |
| `fixtures/seasons/2021.json` | `2dd49957ecabb2942296162ace290953abbd00a271f8dcc636e87159156923af` | identical |
| `fixtures/seasons/2024.json` | `cb1e284af33b4ef0d081eef764eac0418affa895ce3bd014244cba8ba53a5b95` | identical |
| `fixtures/league_matrix.json` | `6b9b0f9a3a96c9a9b8fb37bee2fbb2c8e0ad01e0d26e5f3d294103c018d0c868` | identical |

**Required manifest/hash amendment: NONE.** The board corpus and league matrix the manifest
freezes are byte-identical at the accepted C03 head, so `promotion-v3.json` remains valid as
preregistered and no promotion-v4 amendment is forced by C03.

## Accepted canonical/generated C03 artifacts (recorded for the candidate-identity freeze)

These are NOT in the manifest's frozen file list (correctly — they are candidate policy surface,
captured by the combined candidate SHA when it is frozen after C04):

| Artifact | sha256 at 8694d98 |
|---|---|
| `fixtures/bench_shape.json` (schema v2) | `96cabb5f4db802237a0081e6effd40bdfa8548179ac3c8297464bf05ecbcdde8` |
| its `canonical_source_hash` | `58b611f5b768dc0b95867410ccd815be39e390cd2711a4f67f8e8844c43f9e90` |
| its source receipt | `.orchestrator-v6/experiments/bench-portfolio-c03-source-v2.json` |
| `fixtures/bench_shape_c02c.json` (preserved pre-C03 shape) | `b672610e291aa97f5be7853c16c2e53db201f74638257acc40e7c129c46ad2ee` (matches the C00 baseline `bench_shape.json` hash) |
| `frontend/lib/generated/benchShape.generated.ts` | `208ecb3854bcecf4c1dc9eb5a7f8538542d523df79adb8e058bb29412f2ab0eb` |

## C03 disposition consequences for C05 (no protocol change needed)

1. **The C03 experiment result is `do_not_promote` and is NOT shipping evidence.** Source-v2
   records all nine candidate rows `unsupported`, `interpolation_sources` empty, and all 216
   canonical matrix rows `unsupported` with explicit provenance. C05 treats this exactly as the
   manifest's `failure_interpretation` already dictates; nothing about it feeds a promotion
   verdict.
2. **`t14-2qb-std-te0.5-b4-ir1` remains blocked/uncleared.** The manifest's
   `mandatory_high_risk_slices` (all 24, including the blocked slice at tolerance 0.0) and
   `blocked_slice` entries stay correct as frozen; no list change required.
3. **Promotion machinery unaffected.** `blitz_engine/promotion/` has no dependency on
   `bench_shape`/`roster_shape` surfaces C03 changed; the parked branch's 37 tests (including
   board-corpus hash verification) remain valid against the frozen manifest. The adapter branch
   is deliberately NOT rebased onto 8694d98 — per instruction it stays parked; the next recreate
   happens once C04 passes, following `C05-adapter-rebase-plan.md` (cherry-pick chain now
   `82b7705 a79af01 996125e f4c279f` + this record's commit).

## What would force a promotion-v4 amendment later (none triggered today)

- any byte change to the four frozen board-corpus files before the authoritative run;
- an accepted change to the started-points netting wording (`C05-c02-interface-mismatches.md`
  item 2, still open);
- a corpus/season addition, limit change, or slice-list change.

Parked. Next action: C04 PASS → recreate adapter branch on the C04-accepted head, rerun the 37
tests, then (and only then) freeze the combined candidate SHA in `promotion-v3-exec-v1.json`.
