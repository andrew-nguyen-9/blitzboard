# Fantasy Football Draft Tool

An autonomous, pipeline-driven web app for NFL fantasy football: player intelligence,
draft assistance (live + offline), trade and waiver optimization, and real-time
news-sentiment trending. Built for one league first, architected to open up to anyone.

Spun off the `music-festival-analyzer` infrastructure (Next.js 15 App Router + Supabase +
Python pipeline on GitHub Actions cron), with independent API keys.

## What this folder is

This is the **planning workspace** — gameplan, locked decisions, architecture, design
direction, mock visuals, and roadmap — written before code so the build has a spine.

| File | Purpose |
|------|---------|
| [docs/GAMEPLAN.md](docs/GAMEPLAN.md) | The plan in one page: what we're building and why |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Locked decisions from the design interview (the "why") |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, the core abstractions, data flow |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | Sleeper / nflverse / ESPN / RSS+Reddit — what each provides |
| [docs/DESIGN.md](docs/DESIGN.md) | UI/UX art direction (creative-dev), inspiration, motion |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phased build order with shippable milestones |
| [db/schema.sql](db/schema.sql) | First-pass database schema |
| [mocks/](mocks/) | Architecture, data-flow, ER, and UI wireframe mockups (SVG) |

## The seven sections

a) Homepage · b) League Overview (ESPN connect) · c) Draft Simulator (offline/bots) ·
d) Player Explorer · e) Live + Offline Draft Tool · f) Trade Optimizer · g) Waiver Wire Tool

## Status

**P0 (Foundation) — scaffolded & building.** Next.js frontend (7 routes, dark/light/system
theme, offline empty states), Python pipeline (Sleeper + nflverse ingest), the core model
interfaces (`LeagueRules` / `Projector` / `ValueEngine`, superflex-aware), DB schema + league
seed, and the daily ETL workflow. Builds with **no keys** (renders empty states). Next: P1 Player Explorer with real data — see [docs/ROADMAP.md](docs/ROADMAP.md).

## Running it

```bash
# Frontend (builds & runs with no backend — offline empty states)
cd frontend
npm install
cp .env.local.example .env.local   # add Supabase URL + anon key when ready
npm run dev                        # http://localhost:3000

# Backend / pipeline
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # add Supabase service-role + ESPN cookies
python player_ingest.py --trending           # Sleeper → players
python history_ingest.py --seasons 2022 2023 2024   # nflverse → history

# Database (run once in Supabase SQL editor)
#   db/schema.sql           — tables + RLS
#   db/seed_league_smores.sql — my league rules (superflex half-PPR)
```

## Stack

- **Frontend**: Next.js 15 (App Router), Tailwind, Framer Motion (+ GSAP/canvas where creative-dev calls for it)
- **Backend/DB**: Supabase (Postgres + auto-REST), RLS, anon-read / service-role-write
- **Pipeline**: Python 3.11, GitHub Actions cron (tenacity + rich + dotenv, idempotent upserts)
- **Hosting**: Vercel (frontend) + Supabase (data)
