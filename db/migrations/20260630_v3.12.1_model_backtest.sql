-- v3.12.1 — Model backtest results (Epic 12: VORP + season Monte Carlo validation)
-- backtest/models_backtest.py upserts one row per (model, season); season 0 is the
-- across-seasons (2015-2025) summary. Public read so the methodology/About surface
-- (Epic 14) and player page (Epic 11) can show the numbers; writes are service-role
-- only (the local/manual-dispatch backtest run). Idempotent + safe to re-run.

create table if not exists public.model_backtest (
  model       text not null check (model in ('vorp', 'monte_carlo')),
  season      int  not null,                 -- a real season, or 0 = across-seasons summary
  metrics     jsonb not null,                -- {spearman,...} | {coverage,mae,...} | {seasons,...}
  updated_at  timestamptz not null default now(),
  primary key (model, season)
);

alter table public.model_backtest enable row level security;

-- Anon + authenticated may READ (aggregate, non-personal model metrics).
drop policy if exists "Public read model_backtest" on public.model_backtest;
create policy "Public read model_backtest"
  on public.model_backtest for select
  to anon, authenticated
  using (true);

-- No insert/update/delete policy: the service-role key (pipeline only) bypasses RLS to
-- write; anon/auth cannot mutate.
