-- v3.7.1 — store the signup phone (envelope-encrypted) on the account row.
-- The phone is app-layer AES-256-GCM ciphertext (frontend/lib/crypto/vault.ts); the master key
-- lives only in server env. It rides in signUp user-metadata and the (SECURITY DEFINER) signup
-- trigger persists it here, so no post-confirm session and no service-role key are needed in the
-- request path. accounts already has RLS with owner-scoped policies (v2.5.1) — phone_encrypted is
-- just another column on that table; the owner may read their own ciphertext but cannot decrypt it
-- (key is server-only), consistent with the vault threat model. Idempotent + safe to re-run.

alter table public.accounts add column if not exists phone_encrypted text;

-- Extend the signup trigger to also persist the encrypted phone (and keep full_name → display_name).
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.accounts (user_id, email, display_name, phone_encrypted)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.email),
    new.raw_user_meta_data ->> 'phone_encrypted'
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
