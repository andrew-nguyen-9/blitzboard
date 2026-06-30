-- v3.8.1 — self-service account deletion (Epic 8 Settings).
-- A SECURITY DEFINER RPC lets a signed-in user delete their own auth.users row; every
-- dependent table (accounts, user_leagues, league_rules, credential_vault) references
-- auth.users(id) ON DELETE CASCADE, so one delete cleans up all of the caller's data.
-- No new table → no new RLS. Idempotent + safe to re-run. The function is scoped to
-- auth.uid() so a caller can only ever delete themselves.
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  -- auth.uid() is the only identity used; a caller cannot target another user.
  delete from auth.users where id = auth.uid();
end;
$$;

revoke all on function public.delete_my_account() from public;
grant execute on function public.delete_my_account() to authenticated;
