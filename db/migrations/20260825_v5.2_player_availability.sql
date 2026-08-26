-- v5.2 — Player availability truth layer (Epic 2, two-tier: engine + publish)
-- Publishes the engine's `AvailabilityModel.p_startable` (blitz_engine.survival.availability)
-- per (player_id, season, week) so the static `draftAI` can replace its `faPenalty` +
-- `injuryDiscount` heuristics with a real number (docs/design/v5-architecture.md §4).
--
-- Written by the engine's `publish` CLI verb, run LOCALLY with SUPABASE_SERVICE_ROLE_KEY
-- (never by `pipeline/`, which must stay jax/torch-free). Anon/authenticated get read-only;
-- there is no insert/update/delete policy, so only the service-role key (which bypasses RLS)
-- can write. Idempotent: re-publishing the same (player_id, season, week) upserts in place.
--
-- Numbers are stated priors until e9b's roster/depth-chart feed lands and the model is
-- refit (e2a .done.md) — the schema is the stable contract, not today's fitted values.

create table if not exists public.player_availability (
  player_id     uuid not null references public.players(id) on delete cascade,
  season        integer not null,
  week          integer not null,
  p_startable   real not null default 1.0,  -- AvailabilityModel.p_startable; 1.0 = neutral/no signal
  roster_status text,                        -- resolved RosterState (e2a), when a feed carries one
  source        text not null default 'engine',
  updated_at    timestamptz not null default now(),
  primary key (player_id, season, week)
);

alter table public.player_availability enable row level security;

drop policy if exists "Public read player_availability" on public.player_availability;
create policy "Public read player_availability"
  on public.player_availability for select
  to anon, authenticated
  using (true);
-- (no insert/update/delete policy → service-role writes bypass RLS; anon/auth cannot mutate.)
