# Fantasy Football Tool

A pipeline-driven web app for NFL fantasy football: player intelligence, draft assistance
(live + offline), trade and waiver optimization, and real-time news-sentiment trending.
Next.js 15 (App Router) + Supabase (Postgres) + a Python cron pipeline.

> **Status: v2 in planning.** v1 (P0–P7) shipped and is frozen as **v1.0.0** under
> `docs/archive/v1/`. We are building **v2.0.0+** — a high-end, accessible, secure, multi-user
> revamp. See `docs/overview/VISION.md` and `docs/phases/v2/PHASES_OVERVIEW.md`.

## Documentation map

| Area | Where |
|------|-------|
| **Vision (v2)** | [docs/overview/VISION.md](docs/overview/VISION.md) |
| **Decisions (v2 ADRs)** | [docs/decisions/DECISIONS_V2.md](docs/decisions/DECISIONS_V2.md) |
| **Architecture** | [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) · [DATA_TRANSFER.md](docs/architecture/DATA_TRANSFER.md) |
| **Design system** | [DESIGN_GUIDELINE.md](docs/design-system/DESIGN_GUIDELINE.md) · [TOKENS](docs/design-system/TOKENS.md) · [ACCESSIBILITY](docs/design-system/ACCESSIBILITY.md) · [MOTION](docs/design-system/MOTION.md) |
| **Modeling** | [SCORING.md](docs/modeling/SCORING.md) · [VALUE_ENGINE.md](docs/modeling/VALUE_ENGINE.md) · [DRAFT_LOGIC.md](docs/modeling/DRAFT_LOGIC.md) |
| **Security** | [SECURITY.md](docs/security/SECURITY.md) · [MULTI_LEAGUE.md](docs/security/MULTI_LEAGUE.md) |
| **Phases (v2)** | [docs/phases/v2/](docs/phases/v2/PHASES_OVERVIEW.md) — v2.0 … v2.7, full detail |
| **Workflow** | [VERSIONING](docs/workflow/VERSIONING.md) · [GIT_WORKFLOW](docs/workflow/GIT_WORKFLOW.md) · [DEFINITION_OF_DONE](docs/workflow/DEFINITION_OF_DONE.md) |
| **Brainstorming** | [docs/brainstorming/v2-ideas.md](docs/brainstorming/v2-ideas.md) |
| **Design research** | [mocks/v2-research/findings.md](mocks/v2-research/findings.md) — teardown of 12 reference sites |
| **v1 archive** | [docs/archive/v1/](docs/archive/v1/README.md) — frozen v1.0.0 record |
| **Contributing / AI dev** | [CONTRIBUTING.md](CONTRIBUTING.md) · [CLAUDE.md](CLAUDE.md) |

## What v2 delivers

Homepage + Players revamp · honest scoring (kickers/defenses no longer overvalued) ·
draft logic redone and backtested on 2021–2025 · Google/email accounts with an encrypted
ESPN/Sleeper credential vault and per-user isolation · multi-league with rules import ·
public waivers/trades for anyone · a real design system that works beautifully on every
screen and is accessible by construction.

## Running it

```bash
# Frontend (builds & runs with no backend — renders empty states)
cd frontend && npm install
cp .env.local.example .env.local   # add Supabase URL + anon key when ready
npm run dev                        # http://localhost:3000

# Pipeline
cd pipeline && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # add keys when ready
```

## Stack

Next.js 15 (App Router), Tailwind, Framer Motion + **Rive** + GSAP/Lenis for motion ·
Supabase (Postgres, RLS) + **Auth.js** for accounts · Python 3.11 pipeline on GitHub Actions
cron · Vercel hosting + CDN-cached data snapshots.

## Workflow at a glance

Versioning is `v[phase].[segment].[task]`. A phase is a branch; a segment is a sub-branch
(build→test→QA→`/code-review`→commit→push to parent); a phase finishes with an 8-step ritual
ending in merge-to-`main`, tag, doc archival, and a brainstorming file. Never commit to `main`
directly. Details in [CONTRIBUTING.md](CONTRIBUTING.md).
