# Tech Stack

## Frontend (`frontend/`)
- Next.js 15 (App Router), React 18, TypeScript 5.5 (strict, `tsc --noEmit`).
- Supabase: `@supabase/supabase-js` + `@supabase/ssr` (SSR cookie clients in `lib/supabase/`). Postgres + Auth (Auth.js, Google + email/password).
- Validation: `zod` v4.
- Animation: `framer-motion`, `gsap`, `lenis` (smooth scroll), Rive (`@rive-app/react-canvas`, wrapped in `components/RiveInstrument.tsx`). All gated by `prefers-reduced-motion`.
- Tables/virtualization: `@tanstack/react-virtual`.
- Styling: Tailwind 3.4 + PostCSS/autoprefixer; design tokens are OKLCH CSS custom properties swapped by `data-theme` (light/dark/system). See `docs/design-system/`.
- Tests: `vitest` 3 (co-located `*.test.ts` in lib/). E2E/a11y: `playwright` + `@axe-core/playwright`.
- Lint: ESLint 9 + eslint-config-next. `tsx` for TS scripts.
- Package manager: **npm** (`frontend/package-lock.json`; no pnpm/yarn lock). No root package.json — all node tooling lives in `frontend/`.

## Pipeline (`pipeline/`)
- Python 3.11 (CI). Deps in `pipeline/requirements.txt`. Sources: Sleeper (players), nflverse (history), ESPN/Sleeper (league). Sentiment: VADER now (FinBERT later).

## Deploy
- Vercel (root `vercel.json`). Pipeline runs via GitHub Actions cron (`.github/workflows/etl_daily.yml`).
