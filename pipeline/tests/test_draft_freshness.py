import datetime as dt

from draft_freshness import age_hours, check_freshness


NOW = dt.datetime(2026, 8, 29, 12, tzinfo=dt.timezone.utc)


def test_age_hours_accepts_supabase_offset_timestamp():
    assert age_hours("2026-08-29T06:00:00+00:00", NOW) == 6


def test_check_freshness_fails_stale_and_missing_rows():
    rows = {"values": "2026-08-27T12:00:00Z", "news": None}
    failures = check_freshness(rows, {"values": 36, "news": 12}, NOW)
    assert failures == ["values: 48.0h old", "news: missing timestamp"]


def test_check_freshness_passes_rows_within_limits():
    rows = {"values": "2026-08-28T12:00:01Z", "news": "2026-08-29T06:00:00Z"}
    assert check_freshness(rows, {"values": 24, "news": 6}, NOW) == []
