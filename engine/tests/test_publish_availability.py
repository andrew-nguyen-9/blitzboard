"""e2b — publish path: availability rows built from `p_startable`, upserted degrade-safe.

Asserts PROPERTIES, not magnitudes: e2a's roster-ceiling priors are stated, not fitted, and
will move once e9b's roster feed lands (see e2a's `.done.md` gotchas). This suite must stay
green across that refit.
"""
from __future__ import annotations

import pandas as pd

from blitz_engine.snapshot.publish_availability import (
    TABLE,
    build_availability_rows,
    publish_availability,
)
from blitz_engine.survival.availability import ZERO_AVAILABILITY_EPS, AvailabilityModel


def _players(**cols) -> pd.DataFrame:
    n = len(next(iter(cols.values()))) if cols else 3
    base = {"player_id": [f"p{i}" for i in range(n)]}
    base.update(cols)
    return pd.DataFrame(base)


def test_build_rows_shape_and_bounds() -> None:
    rows = build_availability_rows(_players(), season=2026, week=1)
    assert list(rows.columns) == [
        "player_id", "season", "week", "p_startable", "roster_status", "source",
    ]
    assert len(rows) == 3
    assert (rows["p_startable"] >= 0).all() and (rows["p_startable"] <= 1).all()
    assert (rows["season"] == 2026).all() and (rows["week"] == 1).all()
    assert (rows["source"] == "engine").all()


def test_degrade_safe_with_only_player_id() -> None:
    # No status/roster_status/depth_rank/snap_share columns at all — the CLI store's PLAYERS
    # table today (player_id/position/team only). Must not crash, must not zero everyone.
    rows = build_availability_rows(pd.DataFrame({"player_id": ["a", "b"]}), 2026, 3)
    assert len(rows) == 2
    assert (rows["p_startable"] == AvailabilityModel().neutral_p).all()
    assert rows["roster_status"].isna().all()


def test_roster_status_column_flows_through_when_present() -> None:
    df = _players(roster_status=["IR", "ROSTERED", "RETIRED"])
    rows = build_availability_rows(df, 2026, 1).set_index("player_id")
    assert rows.loc["p0", "roster_status"] == "IR"
    # IR/RETIRED sink toward zero; a plain ROSTERED body does not (property, not magnitude).
    assert rows.loc["p0", "p_startable"] < ZERO_AVAILABILITY_EPS
    assert rows.loc["p2", "p_startable"] < ZERO_AVAILABILITY_EPS
    assert rows.loc["p1", "p_startable"] > rows.loc["p0", "p_startable"]


def test_publish_without_service_role_key_is_a_documented_noop(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    rows = build_availability_rows(_players(), 2026, 1)
    result = publish_availability(rows)
    assert result["uploaded"] is False
    assert result["rows"] == len(rows)
    assert "SUPABASE_SERVICE_ROLE_KEY" in result["reason"]  # names the var, never a value


def test_publish_never_logs_the_key_value(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sekrit-do-not-print")
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    publish_availability(build_availability_rows(_players(), 2026, 1))
    assert "sekrit-do-not-print" not in capsys.readouterr().out


def test_table_name_matches_the_migration() -> None:
    assert TABLE == "player_availability"
