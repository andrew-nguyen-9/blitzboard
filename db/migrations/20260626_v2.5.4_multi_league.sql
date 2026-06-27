-- v2.5.4 — multi-league data model: per-user leagues + (shared or owned) scoring rules.
-- RLS isolates user_leagues per owner; league_rules are readable when public (owner null) or
-- owned. A partial unique index enforces exactly one default league per user, and
-- set_default_league() flips it atomically. Idempotent + safe to re-run.

-- ── league_rules: the v1 LeagueRules JSONB, now multi-tenant ────────────────
create table if not exists public.league_rules (
  id            uuid primary key default gen_random_uuid(),
  owner_user_id uuid references auth.users(id) on delete cascade, -- null = public/global preset
  name          text,
  config        jsonb not null default '{}'::jsonb,  -- scoring, roster slots, superflex, FAAB, …
  created_at    timestamptz not null default now()
);

alter table public.league_rules enable row level security;

drop policy if exists "rules read public or own" on public.league_rules;
create policy "rules read public or own" on public.league_rules
  for select to authenticated using (owner_user_id is null or owner_user_id = auth.uid());

drop policy if exists "rules insert own" on public.league_rules;
create policy "rules insert own" on public.league_rules
  for insert to authenticated with check (owner_user_id = auth.uid());

drop policy if exists "rules update own" on public.league_rules;
create policy "rules update own" on public.league_rules
  for update to authenticated using (owner_user_id = auth.uid()) with check (owner_user_id = auth.uid());

drop policy if exists "rules delete own" on public.league_rules;
create policy "rules delete own" on public.league_rules
  for delete to authenticated using (owner_user_id = auth.uid());

-- ── user_leagues: the leagues a user has connected ─────────────────────────
create table if not exists public.user_leagues (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users(id) on delete cascade,
  platform           text not null check (platform in ('espn', 'sleeper', 'manual')),
  external_league_id text,
  season             text,
  name               text,
  scoring_profile_id uuid references public.league_rules(id) on delete set null,
  is_default         boolean not null default false,
  created_at         timestamptz not null default now()
);

alter table public.user_leagues enable row level security;

drop policy if exists "leagues select own" on public.user_leagues;
create policy "leagues select own" on public.user_leagues
  for select to authenticated using (user_id = auth.uid());

drop policy if exists "leagues insert own" on public.user_leagues;
create policy "leagues insert own" on public.user_leagues
  for insert to authenticated with check (user_id = auth.uid());

drop policy if exists "leagues update own" on public.user_leagues;
create policy "leagues update own" on public.user_leagues
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "leagues delete own" on public.user_leagues;
create policy "leagues delete own" on public.user_leagues
  for delete to authenticated using (user_id = auth.uid());

-- At most one default league per user.
create unique index if not exists user_leagues_one_default
  on public.user_leagues (user_id) where is_default;

-- Atomically make one league the default (and clear the others) for the caller.
create or replace function public.set_default_league(p_league uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.user_leagues
     set is_default = (id = p_league)
   where user_id = auth.uid();
end;
$$;

revoke all on function public.set_default_league(uuid) from public;
grant execute on function public.set_default_league(uuid) to authenticated;
