# C04-codex — independent live scoring/explanation review

## Verdict: BLOCK

- accepted combined base: `8694d98186e5800e5439725973bb8789ebdb2979`
- reviewed implementation: `bf8591a288ca4d45bfb84a8e6b75363d4feb00d7`
- reviewed checkpoint head: `31030f812c349c46f9ef1d1345a65a6505560b2e`
- review order: acceptance contract, implementation/call sites, traces, skips, and independent
  gates first; `C04-claude.md` reconciled only after blind findings were frozen

## Proven requirements

The new modules provide six structured components, deterministic traces, accepted-C03 resolver
adaptation, explicit unsupported/fallback states, candidate-evidence adapters, UI-independent
formatting, and zero simulation/rollout counters. They decorate the shipped `scoreBoard` result
without changing its rank or score and keep failed C03 guidance degraded. Custom keys fall back;
soft costs never become hard caps; absent candidate transaction evidence remains null rather than
being invented.

Producer focused tests pass **49 with 4 visible skips**; independent C03 parity, 15 focused shape
tests, Ruff, and `git diff --check` pass. The four skips honestly represent producer-issued paired
outcome identifiers absent from accepted C02/C03 and are not the blocker.

## Blocking contradiction: no live consumer

`scoreBoardWithExplanations` is referenced only by its own tests outside its defining module. The
production war room still imports and calls `draftAI.scoreBoard` directly, maps results into the
legacy `Recommendation` shape, and renders legacy reason chips/equity/uncertainty only.
`LiveRecommendations.tsx` receives no C04 payload, calls no C04 formatter, and displays no coverage,
contingent-role, breakout, replacement degradation, redundancy, league evidence, or trace-derived
claim.

The producer checkpoint calls the detached module a “live seam,” but an unused seam does not meet
the required live scoring/explanation integration. The reviewer-owned static integration probe
fails deterministically at the missing war-room import. This is executable production reachability,
not a UI-style preference.

## Required C04A correction

1. Preserve `C04-claude.md` and the accepted C04 preparation/implementation commits. Change only
   the production recommendation integration, its focused tests, and immutable C04A record.
2. Make the real `DraftWarRoom` recommendation path call `scoreBoardWithExplanations` exactly once
   instead of independently calling `scoreBoard`. Preserve player order and numeric shipped scores
   byte/number-for-number for identical inputs.
3. Pass the structured explanation through the `Recommendation` model and render deterministic
   text derived through `formatDraftExplanation` (or a semantically equivalent structured renderer)
   in `LiveRecommendations`. Unsupported C03 and missing C02 candidate evidence must be visible;
   no unsupported numeric claim may be presented as measured.
4. Derive the league key from the actual live configuration. Custom/unrepresentable configurations
   must use the existing explicit fallback rather than a guessed canonical key.
5. Add direct production-path tests proving the live war room calls the explained scorer, the UI
   renders coverage/provenance/degradation claims, ranking is unchanged, and no second score/simulation
   pass is introduced. Run the reviewer integration test unchanged.
6. Re-run focused and full frontend tests, TypeScript, lint, production build, C03 parity/shape gates,
   static browser-cost guards, and `git diff --check`. The four producer-ID skips may remain only
   with their current honest dependency explanation.
7. Write immutable `C04A-claude.md` and stop for re-review. Do not integrate, start C05 execution,
   push, merge, or open a PR.

No scoring coefficient, C03 artifact, C02 evaluator, experiment result, promotion manifest, or
unrelated UI behavior is in scope for C04A.
