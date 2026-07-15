-- v4.1 — Per-player opportunity trends (Epic E1)
-- Granular, recent-window-vs-season usage trends per active player, plus QB
-- starting probability / job security. Persisted for the frontend to read.
--
-- Two-plane fit (docs/architecture/ARCHITECTURE.md): PUBLIC READ (anon +
-- authenticated) — trends are derived from already-public catalog/stat data.
-- WRITES are service-role only (pipeline/trends_compute.py); no anon/auth
-- mutate policy, so RLS denies them. Idempotent + safe to re-run.
--
-- Every trend field is a 0..1 signal where 0.5 == neutral/flat (rising usage
-- > 0.5, declining < 0.5). Cascade-safe: a player with no history / a rookie
-- gets 0.5 everywhere rather than a crash or a null hole.

create table if not exists public.player_trends (
  player_id          uuid primary key references public.players(id) on delete cascade,
  opportunity_trend  real not null default 0.5,   -- targets+carries recent-vs-season
  target_share_trend real not null default 0.5,   -- target_share recent-vs-season
  routes_run         real not null default 0,     -- recent-window avg routes (0 if absent)
  routes_trend       real not null default 0.5,   -- routes_run recent-vs-season
  starting_prob      real not null default 0.5,   -- QB: P(starts) from depth chart + injury
  job_security       real not null default 0.5,   -- QB: hold-the-job signal
  updated_at         timestamptz not null default now()
);

alter table public.player_trends enable row level security;

drop policy if exists "Public read player_trends" on public.player_trends;
create policy "Public read player_trends"
  on public.player_trends for select
  to anon, authenticated
  using (true);
-- (no insert/update/delete policy → service-role writes bypass RLS; anon/auth cannot mutate.)
