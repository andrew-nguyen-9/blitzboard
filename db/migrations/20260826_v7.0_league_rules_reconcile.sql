-- v7.0 — reconcile the live v1 league_rules shape with v2.5.4 multi-league auth.
-- The live table predates v2.5.4 and retains the v1 columns consumed by the pipeline.
-- Add the v2 columns alongside them: the pipeline keeps reading the v1 shape while the
-- authenticated frontend reads config and ownership metadata. No existing data is moved.

alter table public.league_rules
  add column if not exists owner_user_id uuid references auth.users(id) on delete cascade,
  add column if not exists name text,
  add column if not exists config jsonb not null default '{}'::jsonb,
  add column if not exists created_at timestamptz not null default now();

alter table public.league_rules enable row level security;

-- v1 left a world-readable SELECT policy; with owned rows arriving via v2.5.4 it must go.
-- Safe: only queries.auth.ts (authenticated) and the service-role pipeline read this table.
drop policy if exists "public read league_rules" on public.league_rules;

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

create unique index if not exists user_leagues_one_default
  on public.user_leagues (user_id) where is_default;

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
