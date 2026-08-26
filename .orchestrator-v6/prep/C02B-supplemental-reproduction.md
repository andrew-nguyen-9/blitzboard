# C02B supplemental independent reproduction

Date: 2026-08-26 (America/Chicago)

This is supplemental reviewer evidence, not the official checkpoint verdict. The
primary reviewer retains ownership of PASS, BLOCK, or INCONCLUSIVE.

## Identity and isolation

- Reviewed production commit: `15a501f443d7b62fe875758ab96c7198d96c8240`.
- `v6/bench-portfolio` resolved to that exact commit before setup.
- Reproduction branch/worktree: `v6/c02b-reproduction` at
  `$HOME/Documents/GitHub/blitzboard/.worktrees/v6-c02b-reproduction`.
- `.worktrees/v6-prod` was not used or modified. No push, merge, PR, or C03 work was
  performed.

## New deterministic finding

**Contradicted: OP waiver eligibility.** The season evaluator delegates slot
eligibility to `blitz_engine.value.mcts.slot_positions`. That helper widens `FLEX`
and `SUPERFLEX`, but not the canonical ESPN `OP` label used elsewhere in the
repository. Consequently `slot_positions("OP") == {"OP"}` instead of
`{"QB", "RB", "WR", "TE"}`. `_best_upgrade` therefore rejects ordinary offensive
players as additions to an OP-only lineup.

The reviewer-owned regression
`engine/tests/test_v6_c02b_supplemental_adversarial.py` fails unchanged against
`15a501f`: expected the dead WR nonstarter to be dropped for a legal RB addition,
but `_best_upgrade` returned `None`. Ruff is clean on the test. Production was not
modified.

FLEX and `SUPERFLEX` cross-role probes pass. Separate probes also establish that the
lowest nonstarter is preferred even when a starter has a lower projection and that
an empty-bench swap cannot drop a sole required QB when doing so would reduce
fillable lineup slots.

## Manifest chronology and immutability

The history is linear and the freezes precede their governed behavior:

| Manifest | Introduction | Frozen behavior lands | SHA-256 | Preserved at head |
|---|---:|---:|---|---|
| waiver-realism-v1 | `62a9336` | `de42301` | `281d546b0480cd54c55c149394adeabd0769d87a50e70b5ff25bfe564d52973f` | yes |
| waiver-realism-v2 | `b2e2f29` | `15a501f` (as superseded by v4's exact formula) | `71b2589d059644376999e855c1b3c88d92bea267f9576ae286024cd912a353b3` | yes |
| waiver-realism-v3 | `a82db26` | `15a501f` | `4fcefd4ccde9248e25548021a0b0f54d26524abe89b22d9f6b61b80f60d707a9` | yes |
| waiver-realism-v4 | `b6f081c` | `15a501f` | `f9c4c60ec10cada496f6422b340ae8f82f2afe624d9a9cbe2e1ddaab162af963` | yes |

For every manifest, the current Git blob equals its introduction blob. The
supersession text is append-only: v2 carries v1 forward; v3 carries v1/v2 forward
while replacing the role-space restriction; v4 replaces only the conflicting v2/v3
budget wording. V4 explicitly freezes:

`total team-week claims <= max(waiver_moves_per_week, proactive_moves_per_week)`,

with emergency-first ordering, independent per-type bounds, and a separately binding
season cap.

`C02-claude.md` and `C02A-claude.md` retain their introduction blobs and SHA-256
values `774f2f…96fd` and `489085e…13e4`. Every pre-existing calibration file under
`.orchestrator-v6/experiments/calibration/` retains its introduction blob. The frozen
reviewer `player-calibration-v1.json` also matches its `bc4cec0` bytes
(`c4a6950…c1301`). The C02B range contains only waiver manifests/evaluator/tests,
the new checkpoint/addendum, and shared state; it contains no C03 or value-coefficient
change.

## Requirement matrix

| Requirement | Result | Evidence |
|---|---|---|
| Dead/config-ineligible nonstarter may be dropped cross-role | proven | reviewer remote suite and production equivalent |
| Post-swap lineup feasibility; sole starter protected | proven | code path plus direct empty-bench probe |
| Started body considered only without a nonstarter | proven | deterministic direct probe |
| FLEX and SUPERFLEX behavior | proven | production/reviewer tests and direct probes |
| OP behavior | **contradicted** | new reviewer regression returns no legal swap |
| K/DST streaming and deterministic ties | proven | production plus unchanged reviewer suites |
| Shared weekly formula and emergency-first ordering | proven | unchanged remote suite; production budget boundaries |
| `(0,1)`, `(1,1)`, `(2,1)` boundaries | proven | unchanged remote test plus production tests |
| Season cap and counter reconciliation | proven | production focused suite |
| Cost veto and strict just-below/equal/above boundaries | proven | decision reviewer suite and production focused suite |
| Genuine low-prior breakout using completed weeks | proven | reviewer and production trajectory tests |
| Shared pool, reverse priority, player return, leakage, determinism | proven | focused suites and full engine suite |
| Every frozen calibration threshold disposed | proven | addendum enumerates all six thresholds |
| Position/cohort regression not silently passed | proven | offline reconstruction finds positive regression in all four comparisons; threshold FAILED |
| Season evaluator tolerance explicit | proven | explicitly `INCONCLUSIVE — NOT EXECUTED`; shipped value preserved |
| No coefficient promotion/input overwrite | proven | Git blob comparisons and empty coefficient-path diff |
| New disposition reproducible offline | proven | regenerated normalized report matches; all 36 position/cohort rows reconstruct exactly |
| Prior checkpoints/manifests/results immutable | proven | introduction/current Git blob equality |
| No C03/merge/push/unrelated production change | proven | linear history and scoped path diff; no external action taken |

## Verification

- Primary reviewer suites, unchanged against reproduction production code: **9
  passed**.
- Production-focused `test_waiver_realism.py`: **21 passed**.
- Full production engine suite (collected before adding the reviewer-owned failing
  regression): **4143 passed, 2 skipped** in 488.22 seconds.
- New reviewer OP regression: **1 failed** as expected; expected `(1, 2)`, received
  `None`.
- Ruff over production engine/tests: clean. Ruff over the new regression: clean.
- Pipeline: **157 passed**. The first collection attempt lacked the worktree-local
  frontend dependency link; the complete rerun used a temporary untracked link to
  the repository's installed `frontend/node_modules`, required sandbox IPC
  permission, passed, and the link was removed.
- Offline calibration report: identical after removing only `generated_utc`.
- Offline threshold reconstruction: all 36 position/cohort rows match the addendum;
  largest positive deltas are 2.43 (1QB ECR), 3.53 (1QB ADP), 4.50 (superflex), and
  3.40 (2QB).
- `git diff --check`: recorded in the final command receipt.

## Recommended disposition

Recommend **BLOCK** to the primary reviewer because the required OP behavior is a
deterministic production contradiction. This is a recommendation only, not the
official verdict. All other examined C02B requirements reproduce as claimed, and
the failed result preserves shipped production behavior.
