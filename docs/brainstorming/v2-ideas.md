# v2 Brainstorming — ideas, fixes, and futures

Seeded during v2 planning. The 8-step phase ritual appends a per-phase file
(`v2.<phase>-ideas.md`) as each phase surfaces new ideas. This is the backlog, not a commitment.

## Surfaced while planning v2

### Model / data
- **FinBERT swap-in** for sentiment once the `news_articles` corpus is large enough (v1 D3 path).
- **Paid consensus** (FantasyPros superflex ECR) behind the already-stubbed key for a stronger
  ensemble input — especially to anchor superflex QB ranks.
- **In-season weekly projections + start/sit** tool (the backtest harness already scores weekly).
- **Strength-of-schedule / matchup adjustments** layered onto weekly projections.
- **Injury-status live feed** to flip a player's predictability/availability in near-real-time.
- **Trade-finder across *future* weeks** (rest-of-season value, not just today).

### Product / UX
- **Mock-draft mode vs. AI bots** as a standalone practice tool (extends the simulator).
- **Shareable read-only draft board / trade proposal links** (public, no auth).
- **Per-NFL-team accent theming** on player views (open question in D16) — A/B it.
- **"Why this value" explainer** popovers everywhere (predictability already does this for K/DEF).
- **Onboarding wizard** for connecting a league + importing rules (reduce time-to-value).
- **Push/email alerts** for waiver targets during the FAAB window (respect quiet hours).

### Platform / infra
- **Vercel AI Gateway** for any future LLM-assisted features (weak-labeling corpus, summaries).
- **Snapshot diffing** — ship only the day-over-day delta to returning clients (smaller payloads).
- **Edge personalization** for the active-league profile without leaking other users' data.
- **Multi-sport generalization** of the engine (the interfaces are sport-agnostic-ish).

### Tech debt / risks to watch
- ESPN feed fragility remains the weakest dependency (manual-first mitigates; monitor).
- Overfitting risk in the backtest — keep a held-out season; prefer explainable terms.
- Keep the snapshot wire format simple until 60KB budget forces columnar.
- Don't let motion creep past the perf budget — CI gate is the guardrail.
