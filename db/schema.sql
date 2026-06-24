-- ============================================================
-- Fantasy Football Draft Tool — FIRST-PASS schema (draft)
-- Mirrors festival-analyzer conventions: pg_trgm search, RLS
-- public-read, service-role writes, JSONB for flexible config.
-- Run in Supabase SQL editor. Refine during P0.
-- ============================================================

create extension if not exists "pg_trgm";
create extension if not exists "unaccent";
create extension if not exists "uuid-ossp";

-- ------------------------------------------------------------
-- PLAYERS — canonical universe (Sleeper)
-- ------------------------------------------------------------
create table if not exists players (
  id              uuid primary key default uuid_generate_v4(),
  sleeper_id      text unique not null,
  espn_id         text,
  gsis_id         text,                          -- nflverse/NFL GSIS id (history join key)
  yahoo_id        text,
  full_name       text not null,
  position        text,                          -- QB/RB/WR/TE/K/DEF
  nfl_team        text,
  bye_week        int,
  age             int,
  years_exp       int,
  status          text,                          -- active/injured/...
  injury_status   text,                          -- questionable/out/IR
  search_name     text,                          -- normalized for pg_trgm
  metadata        jsonb default '{}',
  updated_at      timestamptz default now()
);
create index if not exists players_search_idx on players using gin (search_name gin_trgm_ops);
create index if not exists players_gsis_idx on players (gsis_id);

-- ------------------------------------------------------------
-- HISTORY — nflverse weekly/seasonal stats
-- ------------------------------------------------------------
create table if not exists player_stats_history (
  id          uuid primary key default uuid_generate_v4(),
  player_id   uuid references players(id) on delete cascade,
  season      int not null,
  week        int,                               -- null = season aggregate
  stats       jsonb not null default '{}',       -- {pass_yds, rush_yds, rec, td, ...}
  fantasy_pts numeric,                            -- under a default scoring profile
  unique (player_id, season, week)
);

-- ------------------------------------------------------------
-- LEAGUES + RULES (multi-tenant-ready)
-- ------------------------------------------------------------
create table if not exists leagues (
  id           uuid primary key default uuid_generate_v4(),
  platform     text not null default 'espn',     -- espn/sleeper
  external_id  text not null,                     -- ESPN league_id
  season       int not null,
  name         text,
  accent_color text,                              -- runtime theming
  settings     jsonb default '{}',
  created_at   timestamptz default now(),
  unique (platform, external_id, season)
);

-- Scoring + roster rules — the single source of truth (D1/ARCH §1)
create table if not exists league_rules (
  id             uuid primary key default uuid_generate_v4(),
  league_id      uuid references leagues(id) on delete cascade,
  scoring        jsonb not null,                  -- {ppr:1, pass_td:4, ...}
  roster_slots   jsonb not null,                  -- {QB:1,RB:2,WR:2,TE:1,FLEX:1,...}
  league_size    int,
  waiver_type    text,
  unique (league_id)
);

-- Credentials kept separate; later gets per-user rows + strict RLS
create table if not exists league_credentials (
  id          uuid primary key default uuid_generate_v4(),
  league_id   uuid references leagues(id) on delete cascade,
  -- v1: populated from pipeline .env, NOT exposed to anon role
  espn_s2     text,
  swid        text,
  updated_at  timestamptz default now()
);

create table if not exists rosters (
  id            uuid primary key default uuid_generate_v4(),
  league_id     uuid references leagues(id) on delete cascade,
  espn_team_id  int,                              -- ESPN team id (sync key)
  team_name     text,
  owner         text,
  abbrev        text,
  logo_url      text,
  division      text,
  player_ids    uuid[] default '{}',
  -- standings
  wins          int default 0,
  losses        int default 0,
  ties          int default 0,
  points_for    numeric default 0,
  points_against numeric default 0,
  standing      int,
  updated_at    timestamptz default now(),
  unique (league_id, espn_team_id)
);

-- ------------------------------------------------------------
-- PROJECTIONS — as DISTRIBUTIONS (D5/D6: Monte Carlo needs this)
-- ------------------------------------------------------------
create table if not exists projections (
  id              uuid primary key default uuid_generate_v4(),
  player_id       uuid references players(id) on delete cascade,
  season          int not null,
  week            int,                            -- null = season-long
  source          text not null,                  -- consensus/homegrown
  scoring_profile text not null default 'default',
  mean            numeric,
  floor           numeric,
  ceiling         numeric,
  stdev           numeric,
  by_stat         jsonb default '{}',
  unique (player_id, season, week, source, scoring_profile)
);

-- ------------------------------------------------------------
-- PLAYER VALUE — precomputed per engine (D5)
-- ------------------------------------------------------------
create table if not exists player_value (
  id              uuid primary key default uuid_generate_v4(),
  player_id       uuid references players(id) on delete cascade,
  league_id       uuid references leagues(id) on delete cascade,
  engine          text not null,                  -- vorp/monte_carlo
  scoring_profile text not null default 'default',
  value           numeric,
  vor             numeric,
  replacement     numeric,
  boom            numeric,
  bust            numeric,
  adp             numeric,
  rank            int,
  computed_at     timestamptz default now(),
  unique (player_id, league_id, engine, scoring_profile)
);

-- ------------------------------------------------------------
-- NEWS + SENTIMENT (D2/D3) — news_articles doubles as training corpus
-- ------------------------------------------------------------
create table if not exists news_articles (
  id            uuid primary key default uuid_generate_v4(),
  source        text,                             -- rss feed / reddit
  url           text unique,
  title         text,
  body          text,
  published_at  timestamptz,
  player_ids    uuid[] default '{}',
  sentiment     numeric,                          -- -1..1 (VADER v1)
  injury_flag   boolean default false,
  opportunity_flag boolean default false,
  scorer        text default 'vader',             -- vader/finbert
  ingested_at   timestamptz default now()
);

create table if not exists trending (
  id              uuid primary key default uuid_generate_v4(),
  player_id       uuid references players(id) on delete cascade,
  window_start    timestamptz,
  sleeper_adds    int,
  sleeper_drops   int,
  sentiment_avg   numeric,
  trend_score     numeric,                         -- blended narrative ⊕ behavior
  computed_at     timestamptz default now()
);

-- ------------------------------------------------------------
-- DRAFTS — live(ESPN/Sleeper sync) + offline(manual). Same board.
-- ------------------------------------------------------------
create table if not exists drafts (
  id           uuid primary key default uuid_generate_v4(),
  league_id    uuid references leagues(id) on delete cascade,
  mode         text not null default 'offline',   -- live_espn/live_sleeper/offline/sim
  external_id  text,                               -- platform draft id (live)
  status       text default 'pending',
  settings     jsonb default '{}',
  created_at   timestamptz default now()
);

create table if not exists draft_picks (
  id           uuid primary key default uuid_generate_v4(),
  draft_id     uuid references drafts(id) on delete cascade,
  pick_no      int not null,
  round        int,
  team_slot    int,
  player_id    uuid references players(id),
  source       text default 'manual',             -- manual/espn/sleeper/bot
  picked_at    timestamptz default now(),
  unique (draft_id, pick_no)
);

-- ============================================================
-- RLS — enable + public read on all (writes via service role only).
-- credentials table is the exception: NO public read.
-- ============================================================
do $$
declare t text;
begin
  foreach t in array array[
    'players','player_stats_history','leagues','league_rules','rosters',
    'projections','player_value','news_articles','trending','drafts','draft_picks'
  ] loop
    execute format('alter table %I enable row level security;', t);
    execute format($p$create policy "public read %1$s" on %1$I for select using (true);$p$, t);
  end loop;
end $$;

alter table league_credentials enable row level security;  -- no public-read policy → locked to service role
