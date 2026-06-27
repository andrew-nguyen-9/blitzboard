-- v2.5.1 — accounts table + prefs + signup trigger (Supabase Auth / GoTrue).
-- 1:1 with auth.users. The account row is auto-created by a SECURITY DEFINER trigger on
-- signup, so the client never inserts its own row (never trust a client-supplied user_id).
-- RLS isolates every row to its owner via auth.uid(). Idempotent + safe to re-run.

create table if not exists public.accounts (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  email        text,
  prefs        jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

alter table public.accounts enable row level security;

drop policy if exists "Accounts select own" on public.accounts;
create policy "Accounts select own" on public.accounts
  for select to authenticated using (user_id = auth.uid());

drop policy if exists "Accounts update own" on public.accounts;
create policy "Accounts update own" on public.accounts
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "Accounts delete own" on public.accounts;
create policy "Accounts delete own" on public.accounts
  for delete to authenticated using (user_id = auth.uid());

-- No INSERT policy: inserts are owned by the trigger below (SECURITY DEFINER bypasses RLS).
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.accounts (user_id, email, display_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.email)
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
