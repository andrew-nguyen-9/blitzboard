-- v2.5.3 — encrypted credential vault for ESPN/Sleeper secrets.
-- Ciphertext is app-layer AES-256-GCM (see frontend/lib/crypto/vault.ts); the master key lives
-- only in server env, never here. RLS isolates rows per owner, and there is intentionally NO
-- SELECT policy: the authed client can NEVER read the ciphertext column. The UI reads only the
-- non-secret status via credential_status() (SECURITY DEFINER); the pipeline reads ciphertext
-- with the service-role key to decrypt transiently. Idempotent + safe to re-run.

create table if not exists public.credential_vault (
  user_id     uuid not null references auth.users(id) on delete cascade,
  platform    text not null check (platform in ('espn', 'sleeper')),
  ciphertext  text not null,                 -- "iv.tag.ct" (base64), AES-256-GCM
  masked_hint text,                          -- e.g. ••••ABCD for the UI; never the secret
  status      text not null default 'connected' check (status in ('connected', 'expired')),
  expires_at  timestamptz,                   -- ESPN cookies rotate; null = no known expiry
  created_at  timestamptz not null default now(),
  primary key (user_id, platform)            -- one credential per platform per user (upsert to replace)
);

alter table public.credential_vault enable row level security;

-- Owner may write/replace/remove their own credential. No SELECT policy by design — the
-- authed client cannot read any column of this table (so the ciphertext never reaches the
-- browser). Updates/deletes are still scoped to the owner via USING.
drop policy if exists "vault insert own" on public.credential_vault;
create policy "vault insert own" on public.credential_vault
  for insert to authenticated with check (user_id = auth.uid());

drop policy if exists "vault update own" on public.credential_vault;
create policy "vault update own" on public.credential_vault
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "vault delete own" on public.credential_vault;
create policy "vault delete own" on public.credential_vault
  for delete to authenticated using (user_id = auth.uid());

-- Non-secret connection status for the signed-in user. SECURITY DEFINER so it can read the
-- table (which has no SELECT policy), but it only ever returns the non-secret columns and only
-- for the caller's own rows (filtered by auth.uid()).
create or replace function public.credential_status()
returns table (platform text, masked_hint text, status text, expires_at timestamptz)
language sql
security definer
set search_path = public
stable
as $$
  select platform, masked_hint, status, expires_at
  from public.credential_vault
  where user_id = auth.uid();
$$;

revoke all on function public.credential_status() from public;
grant execute on function public.credential_status() to authenticated;
