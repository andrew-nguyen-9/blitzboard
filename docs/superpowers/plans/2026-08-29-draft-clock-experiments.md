# Draft-Clock State and Advice-Order Experiment Plan

**Status:** experiment-only expansion. No product or opponent implementation is authorized.

**Authority:** shipped v5 remains production authority; C05 remains closed. The user makes the pick.
Clock state may become an observed experiment input only after strict market-field isolation and a
lawful point-in-time archive exist. It is not a manager trait, a confidence score, or an autodraft
trigger.

## 1. Decision

Create two separate research tracks:

1. **Opponent behavior:** test whether lawful remaining-clock state improves held-out prediction of
   other managers' picks or next-turn survival beyond the smallest accepted market/roster mixture.
2. **User assistance:** test whether the default hierarchy, optional details, compare, and advice
   order remain usable under one frozen draft-clock deadline.

Do not combine the results. A behavioral effect in historical rooms does not prove a UI is helpful;
a usable compact UI does not validate a clock-conditioned opponent model.

This track is not the next implementation unit. E0q false-quantile suppression remains first,
followed by E0 reason fidelity, E0a native semantics/reflow, E1 compaction, and E2 compare. The UI
study begins only after E0q/E0/E0a are common to every variant. The opponent study begins only after
the strict market-only runtime row and forbidden-key gate pass.

## 2. Evidence and adaptation boundary

### 2.1 Strategic information search

[Spiliopoulos, Ortmann, and Zhang (2018)](https://doi.org/10.1037/xlm0000535) ran a peer-reviewed,
between-subjects laboratory study with 148 participants: 50 unconstrained, 48 under a 20-second
maximum, and 50 under a 45-second minimum. Participants played 29 normal-form games while Mouselab
recorded payoff lookup; the principal analyses used 28 3×3 games and a hierarchical Bayesian
decision-rule mixture. Under the 20-second limit, the authors report reduced opponent-payoff search
and more use of simpler heuristics.

Applicability is adjacent only. The experiment used one-shot two-player payoff matrices, a 2014
UNSW participant pool, abstract payoffs, an artificial lookup interface, and between-subjects time
conditions. A snake draft is multiplayer, sequential, roster-constrained, and supported by a
visible market board. The result justifies a measured clock-state hypothesis; it does not justify
assigning a “low sophistication” label to a fast manager or hand-setting an effect size.

### 2.2 Automated advice order

[Rieger and Manzey (2022)](https://doi.org/10.1177/0018720820965019) ran two peer-reviewed luggage-
screening experiments with fresh 60-person samples. Each used manual, 95%-reliable, and 75%-reliable
aid groups plus 4.5- and 9-second within-person deadlines. Advice appeared before inspection in the
first experiment and after an initial participant decision in the second. Advice order changed the
time-pressure/reliance pattern, but joint human-aid performance remained generally below the aid
alone.

Again, adaptation is required. Binary detection with known system reliability is not a four-player
fantasy comparison, and “follow the aid” is not BlitzBoard's objective. The implication is to test
order separately and score comprehension, weak-candidate rejection, anchoring, time, and
abandonment—not agreement, trust, or recommendation acceptance.

## 3. Questions and preregistered non-claims

### 3.1 Opponent questions

- Conditional on market position, round, format, and own roster, does remaining time change the
  observed pick distribution?
- Near the deadline, is there less measurable response to other teams' needs or recent runs?
- Does a clock-conditioned bounded picker improve held-out observed-pick log loss and next-turn
  survival calibration?
- Are apparent effects actually platform autopicks, queue behavior, connection delay, or stale
  server timestamps?

### 3.2 User-assistance questions

- Under a fixed deadline, can users reach the primary recommendation before a long player-action
  list and identify two or three reasonable alternatives?
- Do details and compare remain useful late in the clock, or do they add time without improving
  tradeoff comprehension?
- Does a non-forcing user-first shortlist/objective step reduce anchoring without creating excessive
  timeout or abandonment?
- Do keyboard-only, screen-reader, mobile, and large-text users retain enough time to act?

### 3.3 Claims prohibited from this track

- “Fast managers are inexperienced” or “slow managers are sophisticated.”
- “A near-deadline pick follows ADP” without separating human choice, queue, and platform autopick.
- “Users trust BlitzBoard more” as a release success.
- “The compact board is faster” when errors, timeouts, or comprehension worsen.
- “Clock pressure proves the recommendation” or authorizes unattended selection.
- “A clock-conditioned synthetic policy is calibrated” without lawful real labels.

## 4. Point-in-time clock data contract

The minimal event contract is:

```text
draft_id
anonymized_seat_id
pick_number
round
format_id
pick_clock_limit_seconds
remaining_seconds_at_submission
pick_timestamp_utc
server_observed_utc
autopick_state
queue_state_if_lawfully_exposed
connection_or_correction_state_if_lawfully_exposed
market_snapshot_id
public_roster_prefix_hash
chosen_player_id
raw_receipt_id
```

Required semantics:

- `remaining_seconds_at_submission` is source-provided clock state, not a subtraction between two
  receipt timestamps unless the platform contract explicitly defines that transformation.
- Missing clock, queue, or autopick state is null plus a reason. It is never zero.
- A timeout/autopick is a different mechanism from a human submission and is excluded from human-
  policy fitting unless a separately labeled platform fallback model is preregistered.
- Clock limits are stored because 10 seconds remaining under a 30-second clock is not the same
  normalized state as 10 seconds under a 120-second clock.
- Pick corrections, pauses, commissioner actions, reconnects, and keeper/import events are preserved
  or quarantined; they are not silently assigned a duration.
- All rows point to the exact market/public-roster snapshot visible at that event.

For cross-format comparison, derive clock fraction only in analysis:

```text
remaining_fraction = remaining_seconds_at_submission / pick_clock_limit_seconds
```

Freeze bands before outcomes. A reasonable first diagnostic is ample (`> 2/3`), middle (`1/3` to
`2/3`), and near deadline (`< 1/3`), with exact seconds and continuous splines retained only as
sensitivity analyses. Do not select cut points to maximize a favorable effect.

## 5. Privacy, licensing, and retention

Exact timestamps and second-level behavior can fingerprint a room even after team names are removed.
The license/consent receipt must specifically cover event timestamps, clock state, research use,
retention, derived models, and deletion. User authorization is not a substitute for platform
permission where the platform terms require their authorization.

Controls:

- retain exact seconds only in the restricted raw layer;
- use scoped random room/seat IDs and store re-identification links separately;
- prefer preregistered clock bands in ordinary derived receipts;
- suppress small provider/format/clock cells;
- do not join location, real identity, team name, chat, prize, or cross-room identity;
- do not infer a favorite team, experience, or psychological trait from response time;
- provide deletion for identifiable raw histories and derivatives covered by the policy;
- archive the controlling terms/permission version with every collection receipt.

If exact clock data are not permitted, this experiment stays disabled. Pick timestamps alone are not
an acceptable silent proxy.

## 6. Offline opponent experiment

### 6.1 Prerequisites

- strict three-field market player/narrow context implemented outside the opponent;
- runtime assertion rejects every forbidden BlitzBoard projection/value/distribution/availability/
  explanation/metadata key;
- frozen replay parity with the current behaviorally isolated picker;
- lawful point-in-time draft events with clock/autopick semantics;
- train/validation/confirmation split by room and time/provider;
- enough support in each declared clock band and format; unsupported cells remain unavailable.

### 6.2 Arms

| arm | behavior | purpose |
|---|---|---|
| C0 | smallest accepted fixed market/roster mixture; no clock field | reference |
| C1 | C0 plus one bounded main effect of remaining clock on market adherence/random-utility temperature | smallest clock test |
| C2 | C1 plus one interaction with own-roster need | test whether near-deadline choices simplify toward the manager's own roster |
| C3 | C1 plus one interaction with recent run or intervening public needs | test reduced room-state processing; run only if support and C1 justify it |
| CA | explicitly documented platform autopick/queue fallback, evaluated separately | prevent platform automation from contaminating human coefficients |

Only one interaction advances at a time. C2/C3 do not run because they sound plausible; they require
support counts and a declared decision that their result can change. The bounded market window,
legality fallback, seed derivation, and trace remain identical across arms.

### 6.3 Fitting

- Fit only on training rooms; freeze transforms, regularization, and clock bands before validation.
- Cluster uncertainty by draft room and, if lawful linkage exists, manager only under the approved
  privacy scope.
- Include format, round, market distance, own open slots, and provider controls before attributing a
  residual to clock state.
- Use a missing-clock indicator only to assess selection; do not interpret its coefficient as
  behavior.
- Never tune on BlitzBoard team H2H, started points, or playoff proxies; a weaker field can improve
  those diagnostics.

### 6.4 Metrics

Primary:

- held-out observed-pick negative log likelihood/log loss;
- next-turn player and tier survival Brier/log loss and calibration by horizon;
- calibration intercept/slope and reliability counts by clock band.

Secondary:

- top-k observed-pick coverage;
- pick-minus-market distribution and extreme-reach tail;
- position/round, QB-format, K/DST, roster-need, and run-response distributions;
- exact replay and alternate-seed bounded variation;
- legal, duplicate-free, complete rosters;
- performance under missing clock and after excluding all autopicks.

Diagnostic only:

- recommendation stability and reasonable-top-four roster-aware regret;
- started points/H2H/playoff proxies;
- model coefficients or profile weights without held-out predictive value.

### 6.5 Advance gate

C1 advances only if both observed-pick log loss and next-turn survival scoring improve on held-out
rooms, no major preregistered format/round/provider slice breaches its harm bound, calibration stays
honest, reach tails remain plausible, and strict source isolation/legality/replay pass. C2 or C3
advances only if it adds further held-out value and the interaction has adequate support.

If aggregate gain comes only from platform autopicks or one provider, reject the human clock factor.
If calibration improves but latency does not, clock remains offline or is distilled using the same
frozen cases. If real labels are unavailable, retain C0 and qualitative room facts.

## 7. User-assistance clock study

### 7.1 Common baseline

Every variant receives E0q false-quantile suppression, E0 reason fidelity, and E0a native semantics/
reflow before timing. This prevents a compact variant from winning merely because it removed false
numbers, raw codes, clipping, or 155-control recommendation delay.

The primary A/B/C hierarchy study uses one frozen supported clock duration in every arm. Choose the
duration from the target product/league configuration before main outcomes, not from whichever value
makes one variant look best. Practice trials are untimed or separately marked.

### 7.2 Timeout behavior

At timeout:

- record the timeout and displayed remaining time;
- never auto-pick or replace the participant's choice;
- allow completion for comprehension scoring;
- retain whether the answer came after timeout;
- report timeouts/abandonment separately from correct-task time;
- preserve the user's final choice as preference, not ground truth.

### 7.3 Interaction telemetry

The local, consented study log records:

- variant/state/task and frozen clock duration;
- displayed remaining time for details, compare, lens, answer, and draft action;
- keyboard/screen-reader/mobile/input mode;
- focus loss, horizontal scrolling, technical interruption, timeout, and abandonment;
- answer rubric, confidence for factual tasks, and free-choice rationale;
- which limitation/source state was acknowledged.

It does not record production credentials, a full player payload when a locator/hash is enough, or
unrelated browsing.

### 7.4 Main endpoints

Use a hierarchical decision rule:

1. tradeoff comprehension and evidence-limitation accuracy must meet the frozen noninferiority
   margin;
2. among acceptable variants, compare correct-task time and timeout/abandonment;
3. then examine workload and view-open behavior;
4. report weak-candidate rejection and probability/vendor misconceptions as safety endpoints.

Do not collapse these into one usability score. A faster interface that hides uncertainty fails.

### 7.5 Separate advice-order pilot

After A/B/C, compare:

- **Immediate primary:** repaired compact hierarchy appears first.
- **User-first:** participant makes a non-binding shortlist or selects the objective that matters,
  then sees the same unchanged v5 primary and alternatives.

Both show the same candidates, scores, evidence, clock, and legal actions. The user-first step cannot
be required in production based on a small pilot. Primary endpoints are tradeoff accuracy, weak-
candidate rejection, false belief that v5 reranked, time, timeout, and abandonment. Agreement,
acceptance, and trust are descriptive only.

### 7.6 Accessibility clock budget

Test keyboard and at least one screen-reader workflow, 320/375 CSS-pixel reflow, 200% zoom, large
text, high contrast, reduced motion, and long/missing values. Countdown announcements must not fire
every second through a live region; expose the current value programmatically and announce only
predeclared meaningful thresholds without interrupting the draft action. No sound-only warning.

Report task time and timeout by input mode. A deadline that makes the board unusable for an
assistive-technology workflow is a product finding, not a participant failure.

### 7.7 Accessibility standards boundary

Keep three timing authorities distinct:

1. a host platform's live multi-person draft clock;
2. any timer BlitzBoard itself creates or controls;
3. the local study countdown.

[WCAG 2.2 Understanding 2.2.1](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable)
describes turn-off, adjust, or extend routes for time limits set by content and separately defines
real-time/essential exceptions. A live draft may resemble the cited online-auction example, but the
plan must not self-declare an exception: document which system controls the limit, whether an
alternative exists, and obtain an accessibility/conformance review for the exact integration. If
BlitzBoard creates its own nonessential timer, it must not borrow the host's exception. The study
countdown remains non-destructive because participants can finish after timeout and no automatic
choice is made.

For a mirrored countdown, evaluate a named timer value using WAI's
[timer naming guidance](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) and use a
polite programmatic status only for meaningful threshold messages; W3C's
[`role="status"` technique](https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA22) notes its implicit
polite live behavior. Test the actual screen-reader announcement queue. Do not assume that adding
`aria-live` to a value changing every second is accessible, and do not use assertive alerts for
ordinary countdown ticks.

## 8. Cross-layer interpretation

| result | opponent decision | UI decision |
|---|---|---|
| no clock effect after confounders | keep fixed mixture | compact hierarchy may still help users |
| clock improves pick likelihood but UI has no benefit | clock may remain an offline survival input | retain simpler UI |
| UI improves comprehension/time but clock model fails | no opponent clock factor | compact presentation may still advance |
| both improve and pass all gates | keep layers separately typed/versioned | show no opponent-psychology label |
| effect exists only in autopicks | model platform fallback separately or reject | do not infer human behavior |
| accessibility timeout disparity | no opponent implication | revise deadline/flow before release |

## 9. Computational and operational cost

The first opponent clock arm adds one scalar/band to the existing bounded picker likelihood; it does
not justify a learned agent or recurrent state model. Measure campaign runtime and receipt size
against C0. The live board receives no clock-conditioned forecast until real calibration and latency
gates pass.

The UI study uses frozen local fixtures and event logs. It needs no production analytics SDK, vendor
connection, database migration, or permanent fixture route. Prefer the existing Playwright/axe stack
and the proposed disposable populated-board smoke harness.

## 10. Build now / experiment first / reject or defer

### Build now in this track

Nothing. E0q remains the independent implementation recommendation outside this track.

### Experiment first

- archive clock/autopick fields only after permission and schema review;
- exclude or separately label platform automation;
- C0 versus C1 held-out behavior/calibration test;
- one interaction at a time only after C1 support;
- common-deadline A/B/C usability study;
- separate advice-order pilot;
- accessible countdown semantics and timeout analysis.

### Reject or defer

- clock-conditioned production ranking now;
- inferred clock from receipt gaps or pick order;
- speed as experience/sophistication;
- learned per-manager timing profiles;
- forcing a user precommitment before seeing candidates;
- automatic selection at study or product timeout;
- using agreement, trust, or click-through as the success metric;
- MCTS/POMDP expansion based on timing evidence alone.

## 11. Likely files after evidence and authority exist

Offline behavior should reuse:

- `frontend/lib/draftAI.ts` and `frontend/scripts/draft-eval.mjs` only through the strict narrow
  market-player/context seam;
- `engine/blitz_engine/backtest/draft_realism.py` for the bounded factor and trace;
- `engine/blitz_engine/backtest/blind_market.py` or one narrowly named experiment module only if the
  current analyzer cannot express clock bands cleanly;
- the existing draft-realism/blind-market/bridge tests for source isolation, replay, legality, and
  autopick separation;
- ignored hashed experiment receipts and a dated modeling result document.

Data acquisition may touch an approved additive snapshot/history schema and source-specific
collector only after the permission receipt names it. Do not guess a migration or connector now.

The local UI study should reuse the E0a populated-board smoke harness and frozen locator receipts.
No production component file changes merely to conduct the offline advice-order pilot. A later
approved product countdown change belongs in the existing draft board component and focused
accessibility/browser tests, not a new state framework or timer dependency.

## 12. Acceptance and rollback

Acceptance requires:

- lawful, source-defined clock/autopick semantics and point-in-time snapshots;
- strict market-only non-receipt, legality, exact replay, and bounded seed variation;
- held-out behavior and survival calibration gains with supported slices;
- no human-policy result driven by autopicks/timeouts;
- common-baseline user variants and a frozen deadline;
- comprehension noninferiority before time claims;
- timeout, abandonment, misconception, weak-candidate, and accessibility safety reports;
- separate interpretation of opponent and UI evidence;
- no score/order/production-authority change from the experiment itself.

Rollback is deletion or disabling of the optional experiment factor/study variant. C0, v5, stored
picks, and the default board remain unchanged. Immutable lawful receipts remain subject to their
retention/deletion policy; failed analyses remain archived as negative evidence rather than silently
retuned into a passing result.

## 13. Recommended disposition

**Experiment first, after higher-priority prerequisites.** Clock state is a credible extension
because it can change both strategic attention and interaction cost, but the smallest defensible
method is one bounded observed-state factor plus a separate fixed-deadline usability study. Until
lawful real labels and human evidence exist, the board should stay truthful, compact, user-controlled,
and free of timing-based personality claims.
