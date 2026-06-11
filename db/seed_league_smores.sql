-- ============================================================
-- Seed: "Smores 2025" — my ESPN league (the v1 league).
-- 12-team, snake, 0.5 PPR, with an OP (superflex) slot.
-- Run after schema.sql. Idempotent via ON CONFLICT.
-- NOTE: ESPN league_id + cookies live in pipeline .env, not here.
-- ============================================================

insert into leagues (platform, external_id, season, name, accent_color, settings)
values (
  'espn',
  '1850367545',
  2025,
  'Smores 2025',
  '#8CFF5A',
  jsonb_build_object(
    'format', 'head_to_head_points',
    'draft', jsonb_build_object(
      'type', 'snake',
      'date', '2025-08-23T20:15:00-05:00',
      'seconds_per_pick', 45,
      'pick_trading', false,
      'order', 'manual'
    ),
    'regular_season_matchups', 14,
    'weeks_per_matchup', 1,
    'bonus_wins_losses', true,            -- extra win for top scorer-type bonus
    'playoffs', jsonb_build_object('teams', 6, 'reseeding', false, 'home_field_bonus_pts', 1),
    'trade', jsonb_build_object('deadline', '2025-11-26T11:00:00-06:00', 'review_days', 1, 'veto', 'lm_only', 'limit', null),
    'waivers', jsonb_build_object('system', 'faab', 'budget', 100, 'min_offer', 0, 'period_days', 1, 'tiebreaker', 'move_to_last'),
    'keepers', false,
    'undroppable_list', true,
    'ir_slots', 1
  )
)
on conflict (platform, external_id, season) do update
  set name = excluded.name, accent_color = excluded.accent_color, settings = excluded.settings;

insert into league_rules (league_id, scoring, roster_slots, league_size, waiver_type)
select l.id,
  -- ---------------- SCORING ----------------
  jsonb_build_object(
    'passing', jsonb_build_object('yds_per_pt', 25, 'pt_per_yd', 0.04, 'td', 4, 'int', -2, 'two_pt', 2),
    'rushing', jsonb_build_object('pt_per_yd', 0.1, 'td', 6, 'two_pt', 2),
    'receiving', jsonb_build_object('pt_per_yd', 0.1, 'ppr', 0.5, 'td', 6, 'two_pt', 2),
    'misc', jsonb_build_object('fumble_lost', -2, 'fumble_rec_td', 6),
    'kicking', jsonb_build_object(
      'pat', 1, 'pat_miss', -2, 'fg_miss', -1,
      'fg_0_39', 3, 'fg_40_49', 4, 'fg_50_59', 5, 'fg_60_plus', 6
    ),
    'dst', jsonb_build_object(
      'sack', 1, 'int', 2, 'fumble_rec', 2, 'safety', 2, 'blocked_kick', 2,
      'td_any', 6, 'two_pt_return', 2, 'one_pt_safety', 1,
      'points_allowed', jsonb_build_object(
        '0', 5, '1_6', 4, '7_13', 3, '14_17', 1, '18_27', 0, '28_34', -1, '35_45', -3, '46_plus', -5
      ),
      'yards_allowed', jsonb_build_object(
        'lt_100', 5, '100_199', 3, '200_299', 2, '300_349', 0,
        '350_399', -1, '400_449', -3, '450_499', -5, '500_549', -6, '550_plus', -7
      )
    )
  ),
  -- ---------------- ROSTER (10 starters, 6 bench, 1 IR; size 16) ----------------
  -- OP = Offensive Player Utility (QB/RB/WR/TE eligible) => SUPERFLEX behavior.
  jsonb_build_object(
    'QB', 1,
    'RB', 2,
    'WR', 2,
    'TE', 1,
    'FLEX', 1,        -- RB/WR/TE
    'OP', 1,          -- QB/RB/WR/TE  (superflex)
    'DST', 1,
    'K', 1,
    'BENCH', 6,
    'IR', 1,
    '_total_starters', 10,
    '_roster_size', 16,
    '_flex_eligible', jsonb_build_array('RB','WR','TE'),
    '_op_eligible', jsonb_build_array('QB','RB','WR','TE'),
    '_superflex', true,
    '_position_maximums', jsonb_build_object('QB',4,'RB',8,'WR',8,'TE',3,'DST',3,'K',3)
  ),
  12,
  'faab'
from leagues l
where l.platform='espn' and l.season=2025 and l.name='Smores 2025'
on conflict (league_id) do update
  set scoring = excluded.scoring, roster_slots = excluded.roster_slots,
      league_size = excluded.league_size, waiver_type = excluded.waiver_type;
