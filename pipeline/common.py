"""
Shared pipeline utilities: env loading, Supabase service-role client,
rich console, and a standard tenacity retry policy for external APIs.

All pipeline scripts import from here so retry/backoff, logging, and DB
access are consistent (mirrors festival-analyzer conventions).
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from rich.console import Console
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

load_dotenv()

console = Console()

# Standard retry policy for every external API call: 3 attempts, exp backoff.
# Use as: @retry_api  (or call api_retry(...) for a custom predicate)
retry_api = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type(Exception),
)


@lru_cache(maxsize=1)
def get_supabase():
    """Service-role Supabase client. None if env not configured (offline-safe)."""
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        console.print(
            "[yellow]⚠ Supabase env not set "
            "(NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY) — "
            "running in dry mode, no writes.[/yellow]"
        )
        return None
    from supabase import create_client

    return create_client(url, key)


def fetch_all(table: str, columns: str = "*", page: int = 1000, apply=None) -> list[dict]:
    """Fetch ALL rows from a table, paginating past PostgREST's 1000-row cap.

    PostgREST silently limits selects to ~1000 rows, so any full-table load must
    page via .range(). `apply` is an optional callback to add filters/ordering:
        fetch_all("player_stats_history", "player_id,season,stats",
                  apply=lambda q: q.is_("week", "null"))
    """
    sb = get_supabase()
    if sb is None:
        return []
    out: list[dict] = []
    start = 0
    while True:
        q = sb.table(table).select(columns)
        if apply:
            q = apply(q)
        rows = q.range(start, start + page - 1).execute().data or []
        out.extend(rows)
        if len(rows) < page:
            break
        start += page
    return out


def upsert(table: str, rows: list[dict], on_conflict: str) -> int:
    """Idempotent batch upsert. No-op (logged) when Supabase is unconfigured.

    Scripts stay safe to re-run; returns number of rows sent.
    """
    if not rows:
        return 0
    sb = get_supabase()
    if sb is None:
        console.print(f"[dim]dry-run: would upsert {len(rows)} → {table}[/dim]")
        return 0
    # Supabase/PostgREST caps payload size; chunk to be safe.
    sent = 0
    for i in range(0, len(rows), 500):
        chunk = rows[i : i + 500]
        sb.table(table).upsert(chunk, on_conflict=on_conflict).execute()
        sent += len(chunk)
    console.print(f"[green]✓ upserted {sent} → {table}[/green]")
    return sent
