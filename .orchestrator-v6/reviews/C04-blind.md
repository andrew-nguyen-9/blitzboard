# C04 producer-blind findings

Frozen before reading `.orchestrator-v6/checkpoints/C04-claude.md`.

- accepted combined base: `8694d98186e5800e5439725973bb8789ebdb2979`
- reviewed production head: `31030f812c349c46f9ef1d1345a65a6505560b2e`

## Blind deterministic finding

The new C04 modules implement structured component payloads, accepted-C03 resolver adaptation,
explicit unsupported/fallback presentation, deterministic traces, candidate-evidence degradation,
and simulation-free decoration of `draftAI.scoreBoard` results. However, the explained scorer is
not connected to production. Outside tests, only `v6DraftLiveScoring.ts` references
`scoreBoardWithExplanations`. `DraftWarRoom.tsx` still imports and calls `scoreBoard` directly,
maps results into the legacy `Recommendation` shape, and `LiveRecommendations.tsx` renders only
legacy reason chips/equity/uncertainty. No live component receives, formats, or displays the C04
payload or trace.

Thus the checkpoint proves a detached library but not the required live scoring/explanation
integration. The reviewer-owned static integration test requires the production war-room path to
call the explained scorer and pass/render structured explanations. It is expected to fail against
this checkpoint.

The four producer-ID skips are separately honest: accepted C02/C03 exposes paired samples but no
stable candidate-level transaction IDs. Explicit unsupported degradation is preferable to invented
evidence and is not this finding's blocker.

No producer checkpoint rationale was consulted before freezing this finding.
