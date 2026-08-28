# C05 prep — manifest inventory and preregistration determination (2026-08-26)

Session: C05 advance preparation, worktree `.worktrees/v6-c05-prep`, branch `v6/c05-prep`,
base = accepted C01A production commit `b81541c226dd5aeeacbe9ed79df927853a4b8954`.
This file lives under `.orchestrator-v6/prep/` per the coordination rule: no edits to
`state.md`, to existing immutable manifests/checkpoints, or to files owned by other sessions.

## Manifest inventory (at the accepted base)

| File | sha256 | Status |
|---|---|---|
| `experiments/promotion-v1.json` | `020047cd9c88b08a72efc95eac30d7f018022c10084d1135e4287dcb8e036d7f` | immutable, superseded by v2 |
| `experiments/promotion-v2.json` | `89ec1ce2e45591b06285ed384262a14a82937fd7b3076d5f2d6f290fbb126d01` | immutable, operative until v3 |
| reviewer `experiments/player-calibration-v1.json` | `c4a695080cb0544fbdc205b5b4f57f87000f464639356b2c9f105984a0ac1301` | immutable, reviewer-frozen |
| reviewer `amendments/player-calibration-v1.md` | `2718a30b42a916d30183e4a720f92cedcdab504c93fe7727cd83a9053055c8e5` | immutable, reviewer-frozen |

No executed results exist for any promotion manifest. Nothing was overwritten; the next valid
version in the chain is **v3**.

## Determination: v2 is NOT sufficient; promotion-v3.json created

`promotion-v2.json` freezes arms, pairing, seasons/held-out, seeds, board corpus hashes, the 216
mandatory league ids, metrics, thresholds, and failure interpretation — but it predates the
player-calibration amendment and lacks, entirely:

1. the player-calibration gates (ECR/ADP source identity + snapshots, Spearman, weighted rank
   error, top-N recall, positional bias, cohorts, outlier/decomposition reporting, missing-data
   interpretation, held-out confirmation);
2. a frozen CI construction (v2 names CI95 thresholds but no method);
3. a per-slice evaluation-seed derivation formula;
4. runtime and memory limits;
5. an explicit mandatory high-risk slice list and a hidden-regression rule;
6. a frozen `n_seasons` for the evaluator;
7. exact policy-identity rules for the candidate arm (combined candidate SHA freeze rule).

`promotion-v3.json` (sha256 `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`)
therefore supersedes v2 and freezes all of the above. It carries v1/v2 hashes, keeps every v2
threshold unchanged, incorporates the reviewer calibration files by byte-identical copy + hash,
and leaves `arms.candidate.combined_candidate_sha` **null** — the authoritative run is invalid
until C02/C03/C04 pass and the SHA is frozen in a versioned execution addendum
(`promotion-v3-exec-v1.json`, not yet authored).

## Version-collision disclosure (reported per coordination rule)

`outcome-map.md` and `C01-scope-amendment.md` say checkpoint **C02 owns `promotion-v3.json`**
(as the vehicle for the calibration additions). This session authored `promotion-v3.json` on the
isolated branch `v6/c05-prep` because the C05 brief requires the next versioned preregistration to
incorporate exactly that accepted calibration scope; the manifest's own
`amendment_justification.versioning_note` records the rule: **if the C02 session independently
authors a promotion-v3, the later-integrated file is renumbered v4 at integration; versions are
append-only and neither v1 nor v2 was touched.** No file outside this worktree/branch was created
or modified; the C02 production worktree and both Codex prep worktrees were read-only to this
session.

## Byte-identical copies added (not edits)

- `.orchestrator-v6/experiments/player-calibration-v1.json` (hash matches reviewer original)
- `.orchestrator-v6/amendments/player-calibration-v1.md` (hash matches reviewer original)

Same precedent as C00's byte-identical `promotion-v1.json` copy.
