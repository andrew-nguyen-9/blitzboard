"""Offline LeagueRules — snapshot of the seeded Smores league, no Supabase needed.

The backtest must run with zero keys (DoD: offline-safe), so it reads the scoring +
roster config from a committed fixture (derived verbatim from db/seed_league_example.sql)
instead of the live `league_rules` table."""
from __future__ import annotations

import json
import os

from models import LeagueRules

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "smores_rules.json")


def load_rules_fixture() -> LeagueRules:
    with open(_FIXTURE) as f:
        d = json.load(f)
    return LeagueRules(
        league_id="backtest-smores",
        league_size=d["league_size"],
        scoring=d["scoring"],
        roster_slots=d["roster_slots"],
        waiver_type=d.get("waiver_type", "faab"),
    )
