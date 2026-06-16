# Graph Report - .  (2026-06-15)

## Corpus Check
- Corpus is ~22,717 words - fits in a single context window. You may not need a graph.

## Summary
- 410 nodes · 711 edges · 29 communities (18 shown, 11 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 80 edges (avg confidence: 0.81)
- Token cost: 15,400 input · 4,430 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Projection & Value Engine|Projection & Value Engine]]
- [[_COMMUNITY_Draft Room & ESPN Integration|Draft Room & ESPN Integration]]
- [[_COMMUNITY_Frontend Pages & UI Patterns|Frontend Pages & UI Patterns]]
- [[_COMMUNITY_Supabase & Pipeline Core|Supabase & Pipeline Core]]
- [[_COMMUNITY_Data Visualization Components|Data Visualization Components]]
- [[_COMMUNITY_Architecture & Data Sources|Architecture & Data Sources]]
- [[_COMMUNITY_Projector Implementations|Projector Implementations]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Design Decisions & Patterns|Design Decisions & Patterns]]
- [[_COMMUNITY_TypeScript Configuration|TypeScript Configuration]]
- [[_COMMUNITY_App Layout & Navigation|App Layout & Navigation]]
- [[_COMMUNITY_Player Card Analytics UI|Player Card Analytics UI]]
- [[_COMMUNITY_Draft Board Wireframe|Draft Board Wireframe]]
- [[_COMMUNITY_Superflex League Rules|Superflex League Rules]]
- [[_COMMUNITY_UI Mockups & Design|UI Mockups & Design]]
- [[_COMMUNITY_Next.js Config|Next.js Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Tailwind Config|Tailwind Config]]
- [[_COMMUNITY_Error Page|Error Page]]
- [[_COMMUNITY_System Architecture SVG|System Architecture SVG]]
- [[_COMMUNITY_Homepage|Homepage]]
- [[_COMMUNITY_Sentiment Engine Decision|Sentiment Engine Decision]]
- [[_COMMUNITY_NLP Scoring Decision|NLP Scoring Decision]]
- [[_COMMUNITY_League Connection Decision|League Connection Decision]]
- [[_COMMUNITY_Draft Adapter Decision|Draft Adapter Decision]]

## God Nodes (most connected - your core abstractions)
1. `Projection` - 20 edges
2. `compilerOptions` - 16 edges
3. `LeagueRules` - 16 edges
4. `HistoryStore` - 16 edges
5. `Projector` - 16 edges
6. `PlayerWithValue` - 15 edges
7. `main()` - 15 edges
8. `main()` - 12 edges
9. `DraftRoom()` - 11 edges
10. `isSupabaseConfigured()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `D6 — 3-Input Ensemble Projector` --rationale_for--> `EnsembleProjector`  [EXTRACTED]
  docs/DECISIONS.md → pipeline/models/projector.py
- `Superflex OP Slot QB Demand` --conceptually_related_to--> `VorpEngine`  [INFERRED]
  docs/LEAGUE_RULES.md → pipeline/models/value_engine.py
- `ETL Daily GitHub Actions Workflow` --calls--> `main()`  [EXTRACTED]
  .github/workflows/etl_daily.yml → pipeline/value_engine_run.py
- `getSupabase()` --semantically_similar_to--> `get_supabase()`  [INFERRED] [semantically similar]
  frontend/lib/supabase.ts → pipeline/common.py
- `System Architecture` --references--> `LeagueRules`  [EXTRACTED]
  docs/ARCHITECTURE.md → pipeline/models/league_rules.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Draft Live-Sync Triad (Manual + Sleeper + ESPN)** — components_draftroom_draftroom, api_espn_draft_route_get, picks_route_sleeper_picks_get, route_sleeper_draft_get [EXTRACTED 1.00]
- **Player Value Pipeline (players → projections → player_value)** — db_schema_players_table, db_schema_projections_table, db_schema_player_value_table, db_schema_player_stats_history_table [INFERRED 0.95]
- **Empty State Pattern — All Coming-Soon Pages** — draft_page, league_page, players_page_playerspage, trades_page_tradespage, waivers_page_waiverspage, id_page_playerdetailpage, components_emptystate_emptystate [EXTRACTED 1.00]
- **Live Draft Sync Pipeline (poll → map → PlayerWithValue)** — lib_useespnsync_useespnsync, lib_usesleepersync_usesleepersync, lib_espndraft_mapespnpicks, lib_sleeperdraft_mappicks, lib_types_playerwithvalue [EXTRACTED 0.95]
- **Supabase Query Layer (client + all query helpers)** — lib_supabase_getsupabase, lib_queries_getplayers, lib_queries_getplayersbyvalue, lib_queries_getplayerdetail, lib_queries_getleagueoverview, lib_queries_getplayercount [EXTRACTED 0.95]
- **Pipeline DB Write Pattern (get_supabase + fetch_all + upsert)** — pipeline_common_get_supabase, pipeline_common_fetch_all, pipeline_common_upsert, pipeline_history_ingest_main, pipeline_league_sync_main [EXTRACTED 0.95]
- **Ensemble Projection Pipeline: HistoryStore + LeagueRules → Projectors → EnsembleProjector → Projection Distributions** — models_projector_historystore, models_league_rules_leaguerules, models_projector_heuristicprojector, models_projector_regressionprojector, models_projector_consensusprojector, models_projector_ensembleprojector [EXTRACTED 0.95]
- **VORP Value Chain: EnsembleProjector + LeagueRules → VorpEngine → PlayerValue (superflex-aware)** — models_projector_ensembleprojector, models_league_rules_leaguerules, models_value_engine_vorpengine, models_value_engine_playervalue, concept_superflex_op_slot [EXTRACTED 0.95]
- **Daily ETL Orchestration: player_ingest + history_ingest + value_engine_run triggered by GitHub Actions** — workflows_etl_daily_etl_job, pipeline_player_ingest_main, pipeline_value_engine_run_main, concept_batch_precompute [EXTRACTED 0.95]
- **All pipeline stages write to Supabase Postgres** — architecture_player_ingest, architecture_history_ingest, architecture_league_sync, architecture_news_sentiment, architecture_projector, architecture_value_engine, architecture_supabase [EXTRACTED 1.00]
- **All frontend views read from Supabase (anon, read-only)** — architecture_homepage, architecture_player_explorer, architecture_draft_board, architecture_league_overview, architecture_waiver_tool, architecture_trade_optimizer, architecture_supabase [EXTRACTED 1.00]
- **7 tools all consume one value + trending layer** — architecture_table_player_value, architecture_table_trending, architecture_homepage, architecture_player_explorer, architecture_draft_board, architecture_league_overview, architecture_waiver_tool, architecture_trade_optimizer [EXTRACTED 1.00]
- **Three-Panel Draft Board Layout** — mocks_draft_board_wireframe_live_pick_ticker, mocks_draft_board_wireframe_best_available, mocks_draft_board_wireframe_my_roster_needs [EXTRACTED 1.00]
- **Ranking Engine UI Components (VORP and Monte Carlo)** — mocks_draft_board_wireframe_engine_toggle, mocks_draft_board_wireframe_best_available, mocks_draft_board_wireframe_positional_scarcity [INFERRED 0.85]
- **Live Data Pipeline UI (ESPN, stall, manual fallback)** — mocks_draft_board_wireframe_espn_live_indicator, mocks_draft_board_wireframe_manual_fallback, mocks_draft_board_wireframe_live_pick_ticker [INFERRED 0.85]
- **Player Card Instrument Readout — All Visual Panels** — mocks_player_card_dataviz_player_identity, mocks_player_card_dataviz_radial_gauge, mocks_player_card_dataviz_monte_carlo, mocks_player_card_dataviz_sparkline, mocks_player_card_dataviz_sentiment_pulse [EXTRACTED 1.00]

## Communities (29 total, 11 thin omitted)

### Community 0 - "Projection & Value Engine"
Cohesion: 0.06
Nodes (52): ABC, Ensemble Projection (3-signal blend), LeagueRules, fetch_ffc_adp(), positional_order(), Shared Fantasy Football Calculator (FFC) ADP fetch — free, no key (D6).  Cached, Return { lower_name: {name, position, team, adp, ...} } or {} on failure., ADP entries for one position, sorted best→worst. (+44 more)

### Community 1 - "Draft Room & ESPN Integration"
Cohesion: 0.09
Nodes (35): ESPN Draft API Route GET, ESPN Cookie-Auth Server Proxy Pattern, DraftRoom(), Mode, POSITIONS, SyncBadge(), POSITIONS, SortKey (+27 more)

### Community 2 - "Frontend Pages & UI Patterns"
Cohesion: 0.11
Nodes (27): Home(), EmptyState(), EngineToggle(), Graceful Degradation / Empty State Pattern, news_articles Table, rosters Table, trending Table, DraftPage() (+19 more)

### Community 3 - "Supabase & Pipeline Core"
Cohesion: 0.09
Nodes (33): Offline-safe / null-client degradation pattern, HistoryStore, getSupabase(), fetch_all(), get_supabase(), Shared pipeline utilities: env loading, Supabase service-role client, rich conso, Service-role Supabase client. None if env not configured (offline-safe)., Fetch ALL rows from a table, paginating past PostgREST's 1000-row cap.      Post (+25 more)

### Community 4 - "Data Visualization Components"
Cohesion: 0.09
Nodes (25): NotFound(), DistributionBar(), PlayerTable(), Sparkline(), ValueDial(), Projection as Distribution (Floor/Mean/Ceiling), VORP vs Monte Carlo Engine Toggle, draft_picks Table (+17 more)

### Community 5 - "Architecture & Data Sources"
Cohesion: 0.08
Nodes (28): Frontend: Draft Board, ESPN Fantasy (Data Source, fragile), history_ingest Pipeline, Frontend: League Overview, LeagueRules (JSONB scoring + roster, source of truth), league_sync (ESPN) Pipeline, news_sentiment Pipeline (VADER→FinBERT), nflverse / nfl_data_py (Data Source) (+20 more)

### Community 6 - "Projector Implementations"
Cohesion: 0.11
Nodes (11): ConsensusProjector, HistoryStore, Piggyback others' rankings (D6). Uses Fantasy Football Calculator ADP     (free,, player_id → [SeasonLine] (sorted ascending by season)., Mean points-per-game across all season lines at a position (for shrinkage)., RegressionProjector, SeasonLine, build_synth() (+3 more)

### Community 7 - "Frontend Dependencies"
Cohesion: 0.08
Nodes (23): dependencies, framer-motion, next, react, react-dom, @supabase/supabase-js, devDependencies, autoprefixer (+15 more)

### Community 8 - "Design Decisions & Patterns"
Cohesion: 0.13
Nodes (19): Batch Precompute Pipeline Pattern, System Architecture, Data Sources Reference, D1 — Player Data Backbone: Layered, D6 — 3-Input Ensemble Projector, D8 — Build Order: Draft-first, Project Gameplan, Project Roadmap (+11 more)

### Community 9 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 10 - "App Layout & Navigation"
Cohesion: 0.17
Nodes (12): metadata, RootLayout(), Nav(), SECTIONS, ThemeScript(), apply(), ICON, LABEL (+4 more)

### Community 11 - "Player Card Analytics UI"
Cohesion: 0.27
Nodes (11): Boom/Bust Probability Profile, Monte Carlo Simulation for Fantasy Scoring, Opportunity Flag (Target Share / Red Zone), VADER Sentiment Analysis with NFL Lexicon, VORP (Value Over Replacement Player), Player Card Data Visualization (SVG Mock), Monte Carlo Season Outcome Distribution (10k sims), Player Identity Section (Sam LaPorta, TE · DET) (+3 more)

### Community 12 - "Draft Board Wireframe"
Cohesion: 0.31
Nodes (10): Best Available Panel, Draft Board Wireframe Screen, Draft Button with Confirm Burst Animation, Ranking Engine Toggle (VORP vs Monte Carlo), ESPN Live Connection Indicator, Live Pick Ticker Panel, Stall to Manual Fallback Indicator, My Roster and Needs Panel (+2 more)

### Community 13 - "Superflex League Rules"
Cohesion: 0.33
Nodes (7): Superflex OP Slot QB Demand, VORP Replacement Level (Superflex-Aware), D9 — Smores 2025 Superflex League Rules, Smores 2025 League Rules, LeagueRules.replacement_ranks, SLOT_ELIGIBILITY, LeagueRules.starters_per_team

## Knowledge Gaps
- **90 isolated node(s):** `metadata`, `metadata`, `metadata`, `metadata`, `metadata` (+85 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_supabase()` connect `Supabase & Pipeline Core` to `Projection & Value Engine`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Why does `getSupabase()` connect `Supabase & Pipeline Core` to `Frontend Pages & UI Patterns`, `Data Visualization Components`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Why does `main()` connect `Supabase & Pipeline Core` to `Projection & Value Engine`, `Design Decisions & Patterns`, `Projector Implementations`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `Projection` (e.g. with `Projection as Distribution (Floor/Mean/Ceiling)` and `LeagueRules`) actually correct?**
  _`Projection` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `LeagueRules` (e.g. with `LeagueRules` and `MonteCarloEngine`) actually correct?**
  _`LeagueRules` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HistoryStore` (e.g. with `ConsensusProjector` and `HeuristicProjector`) actually correct?**
  _`HistoryStore` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Projector` (e.g. with `_ConsensusSlotProjector` and `DefenseProjector`) actually correct?**
  _`Projector` has 3 INFERRED edges - model-reasoned connections that need verification._