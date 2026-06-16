// Row shapes mirroring db/schema.sql (the subset the frontend reads).

export type Position = "QB" | "RB" | "WR" | "TE" | "K" | "DEF";

export interface Player {
  id: string;
  sleeper_id: string;
  espn_id: string | null;
  full_name: string;
  position: Position | null;
  nfl_team: string | null;
  bye_week: number | null;
  age: number | null;
  years_exp: number | null;
  status: string | null;
  injury_status: string | null;
  metadata?: {
    depth_chart_order?: number | null;
    depth_chart_position?: string | null;
    search_rank?: number | null;
    [k: string]: unknown;
  } | null;
}

export interface PlayerValue {
  player_id: string;
  engine: "vorp" | "monte_carlo";
  value: number | null;
  vor: number | null;
  replacement: number | null;
  boom: number | null;
  bust: number | null;
  adp: number | null;
  rank: number | null;
}

// Player joined with its value for a given engine (Player Explorer row).
export interface PlayerWithValue extends Player {
  value?: PlayerValue | null;
}

export type Engine = PlayerValue["engine"];
