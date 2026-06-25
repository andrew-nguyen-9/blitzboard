-- v2.2.1 — Predictability scoring (SCORING.md §1 / VALUE_ENGINE.md)
-- Adds the per-player predictability score ρ∈[0,1] to the distribution and value
-- layers. The ValueEngine discounts raw VORP by f(ρ) (v2.2.2); the player card
-- surfaces it as the "predictability meter" (v2.2.4). Idempotent + RLS-safe: these
-- tables already have public-read policies from schema.sql; no new table.

alter table projections  add column if not exists predictability numeric;  -- ρ∈[0,1]
alter table player_value add column if not exists predictability numeric;  -- ρ∈[0,1]

comment on column projections.predictability  is 'Reproducibility of the projection ρ∈[0,1] (SCORING.md §1): YoY rank stability + own variance + TD/turnover share, shrunk to a positional prior.';
comment on column player_value.predictability is 'Predictability ρ∈[0,1] carried from the projection; drives the f(ρ) VORP discount and the player-card meter.';
