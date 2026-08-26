"""Fail closed when draft-critical Supabase data is stale."""
from __future__ import annotations

import argparse
import datetime as dt

from common import get_supabase


def age_hours(value: str, now: dt.datetime) -> float:
    timestamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (now - timestamp).total_seconds() / 3600


def check_freshness(rows: dict[str, str | None], limits: dict[str, float], now: dt.datetime) -> list[str]:
    failures = []
    for label, limit in limits.items():
        value = rows.get(label)
        if not value:
            failures.append(f"{label}: missing timestamp")
            continue
        age = age_hours(value, now)
        print(f"{label}: {value} ({age:.1f}h old; limit {limit:g}h)")
        if age > limit:
            failures.append(f"{label}: {age:.1f}h old")
    return failures


def latest(sb, table: str, column: str, *, engine: str | None = None) -> str | None:
    query = sb.table(table).select(column)
    if engine:
        query = query.eq("engine", engine)
    data = query.order(column, desc=True).limit(1).execute().data or []
    return data[0].get(column) if data else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--value-max-hours", type=float, default=36)
    parser.add_argument("--news-max-hours", type=float, default=12)
    args = parser.parse_args()

    sb = get_supabase()
    if sb is None:
        print("FAIL: Supabase service-role environment is not configured")
        return 2

    rows = {
        "player_value:vorp": latest(sb, "player_value", "computed_at", engine="vorp"),
        "player_value:monte_carlo": latest(sb, "player_value", "computed_at", engine="monte_carlo"),
        "news_articles": latest(sb, "news_articles", "ingested_at"),
        "trending": latest(sb, "trending", "computed_at"),
    }
    limits = {
        "player_value:vorp": args.value_max_hours,
        "player_value:monte_carlo": args.value_max_hours,
        "news_articles": args.news_max_hours,
        "trending": args.news_max_hours,
    }
    failures = check_freshness(rows, limits, dt.datetime.now(dt.timezone.utc))
    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("PASS: draft values, news, and trending are fresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
